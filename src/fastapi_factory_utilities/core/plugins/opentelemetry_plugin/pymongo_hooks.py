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

RequestHookT = Callable[[Span, monitoring.CommandStartedEvent], None]


def _truncate_in_arrays(value: Any) -> Any:
    """Truncate large ``$in`` arrays to keep span attributes bounded."""
    if isinstance(value, list):
        if len(value) > MAX_IN_ARRAY_LENGTH:
            return [*value[:MAX_IN_ARRAY_LENGTH], f"...(+{len(value) - MAX_IN_ARRAY_LENGTH} more)"]
        return [_truncate_in_arrays(item) for item in value]
    if isinstance(value, dict):
        return {key: _truncate_in_arrays(item) for key, item in value.items()}
    return value


def _sanitize_mongo_command(command: Mapping[str, Any]) -> dict[str, Any]:
    """Return a compact, redaction-safe MongoDB command summary for tracing."""
    sanitized: dict[str, Any] = {"command": next(iter(command.keys()), "unknown")}
    for key, value in command.items():
        if key in {"find", "aggregate", "count", "distinct", "update", "delete", "insert"}:
            sanitized["collection"] = value
            continue
        if key in {"filter", "query", "sort", "limit", "skip", "pipeline", "updates", "documents"}:
            sanitized[key] = _truncate_in_arrays(value)
    return sanitized


def build_pymongo_request_hook() -> RequestHookT:
    """Build a request hook that records a sanitized MongoDB command on the span."""

    def request_hook(span: Span, event: monitoring.CommandStartedEvent) -> None:
        """Attach a truncated MongoDB command summary to the active span."""
        statement: str = json.dumps(_sanitize_mongo_command(event.command), default=str)
        if len(statement) > MAX_DB_STATEMENT_LENGTH:
            statement = f"{statement[: MAX_DB_STATEMENT_LENGTH - 3]}..."
        span.set_attribute(SpanAttributes.DB_STATEMENT, statement)

    return request_hook
