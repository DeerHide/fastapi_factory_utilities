"""Tests for sanitized PyMongo OpenTelemetry request hooks."""

from typing import Any
from unittest.mock import MagicMock

from opentelemetry.semconv.trace import SpanAttributes
from pymongo import monitoring

from fastapi_factory_utilities.core.plugins.opentelemetry_plugin.pymongo_hooks import (
    MAX_DB_STATEMENT_LENGTH,
    build_pymongo_request_hook,
)


class TestBuildPymongoRequestHook:
    """Tests for ``build_pymongo_request_hook``."""

    def test_sets_sanitized_db_statement_on_span(self) -> None:
        """The hook must expose filter/sort/limit without raw oversized payloads."""
        span: MagicMock = MagicMock()
        event: monitoring.CommandStartedEvent = monitoring.CommandStartedEvent(
            command={
                "find": "YoutubeMediaModel",
                "filter": {"realm_id": "realm-1"},
                "sort": {"youtube_published_at": -1},
                "limit": 50,
            },
            database_name="youtube-integration",
            request_id=1,
            connection_id=MagicMock(),
            operation_id=1,
        )
        request_hook = build_pymongo_request_hook()

        request_hook(span, event)

        span.set_attribute.assert_called_once()
        attribute_name: str
        attribute_value: Any
        attribute_name, attribute_value = span.set_attribute.call_args.args
        assert attribute_name == SpanAttributes.DB_STATEMENT
        assert '"filter": {"realm_id": "realm-1"}' in attribute_value
        assert '"sort": {"youtube_published_at": -1}' in attribute_value
        assert len(attribute_value) <= MAX_DB_STATEMENT_LENGTH

    def test_truncates_large_in_arrays(self) -> None:
        """Large ``$in`` arrays must be truncated to keep span attributes bounded."""
        span: MagicMock = MagicMock()
        video_ids: list[str] = [f"vid-{index}" for index in range(30)]
        event: monitoring.CommandStartedEvent = monitoring.CommandStartedEvent(
            command={
                "find": "YoutubeMediaModel",
                "filter": {"youtube_video_id": {"$in": video_ids}},
            },
            database_name="youtube-integration",
            request_id=2,
            connection_id=MagicMock(),
            operation_id=2,
        )
        request_hook = build_pymongo_request_hook()

        request_hook(span, event)

        attribute_value: str = span.set_attribute.call_args.args[1]
        assert "(+10 more)" in attribute_value
        assert "vid-29" not in attribute_value
