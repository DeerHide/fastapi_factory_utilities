"""PyMongo OpenTelemetry hooks for sanitized command diagnostics."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import Span
from pymongo import monitoring

MAX_DB_STATEMENT_LENGTH: int = 2048
MAX_IN_ARRAY_LENGTH: int = 20

# Command keys whose value is the collection name when that value is str or int.
_COLLECTION_COMMAND_KEYS: frozenset[str] = frozenset(
    {
        "find",
        "aggregate",
        "count",
        "distinct",
        "update",
        "delete",
        "insert",
        "findAndModify",
    }
)

# Payload keys to summarize on the span (filters, updates, documents, …).
_STATEMENT_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "filter",
        "query",
        "sort",
        "limit",
        "skip",
        "pipeline",
        "updates",
        "documents",
        "update",
    }
)

RequestHookT = Callable[[Span, monitoring.CommandStartedEvent], None]


def _json_safe_placeholder(value: Any) -> str:
    """Return a type placeholder; never call ``str()`` on BSON values."""
    return f"<{type(value).__name__}>"


def _truncate_in_arrays(value: Any) -> Any:
    """Truncate large arrays and refuse to stringify BSON documents.

    PyMongo often hands the command filter over as ``RawBSONDocument``.
    ``str()`` on that object includes the raw bytes and the full
    ``CodecOptions`` repr, so every find becomes a 2KB span attribute.
    """
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    if isinstance(value, list):
        if len(value) > MAX_IN_ARRAY_LENGTH:
            head: list[Any] = [_truncate_in_arrays(item) for item in value[:MAX_IN_ARRAY_LENGTH]]
            return [*head, f"...(+{len(value) - MAX_IN_ARRAY_LENGTH} more)"]
        return [_truncate_in_arrays(item) for item in value]
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            safe_key: str = key if isinstance(key, str) else _json_safe_placeholder(key)
            sanitized[safe_key] = _truncate_in_arrays(item)
        return sanitized
    return _json_safe_placeholder(value)


def _sanitize_mongo_command(command: Mapping[str, Any]) -> dict[str, Any]:
    """Return a compact, redaction-safe MongoDB command summary for tracing."""
    sanitized: dict[str, Any] = {"command": next(iter(command.keys()), "unknown")}
    for key, value in command.items():
        if key in _COLLECTION_COMMAND_KEYS and isinstance(value, str | int):
            sanitized["collection"] = value
            continue
        if key in _STATEMENT_PAYLOAD_KEYS:
            sanitized[key] = _truncate_in_arrays(value)
    return sanitized


def build_pymongo_request_hook() -> RequestHookT:
    """Build a request hook that records a sanitized MongoDB command on the span."""

    def request_hook(span: Span, event: monitoring.CommandStartedEvent) -> None:
        """Attach a truncated MongoDB command summary to the active span."""
        statement: str = json.dumps(
            _sanitize_mongo_command(event.command),
            default=_json_safe_placeholder,
        )
        if len(statement) > MAX_DB_STATEMENT_LENGTH:
            statement = f"{statement[: MAX_DB_STATEMENT_LENGTH - 3]}..."
        span.set_attribute(SpanAttributes.DB_STATEMENT, statement)

    return request_hook
