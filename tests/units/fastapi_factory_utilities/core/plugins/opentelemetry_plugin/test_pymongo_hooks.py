"""Tests for sanitized PyMongo OpenTelemetry request hooks."""

import datetime
import json
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

from bson import ObjectId
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

    def test_does_not_stringify_raw_bson_documents(self) -> None:
        """BSON document filters must not be dumped via ``str()`` onto the span."""

        class _RawBSONDocument:
            def __str__(self) -> str:
                return "CodecOptions(" + ("x" * 3000)

        span: MagicMock = MagicMock()
        event: monitoring.CommandStartedEvent = monitoring.CommandStartedEvent(
            command={
                "find": "YoutubeMediaModel",
                "filter": _RawBSONDocument(),
                "limit": 1,
            },
            database_name="youtube-integration",
            request_id=3,
            connection_id=MagicMock(),
            operation_id=3,
        )
        request_hook = build_pymongo_request_hook()

        request_hook(span, event)

        attribute_value: str = span.set_attribute.call_args.args[1]
        assert "CodecOptions" not in attribute_value
        assert "_RawBSONDocument" in attribute_value
        assert len(attribute_value) <= MAX_DB_STATEMENT_LENGTH

    def test_find_and_modify_with_datetime_does_not_raise(self) -> None:
        """Realm-shaped findAndModify must serialize datetimes without raising."""
        span: MagicMock = MagicMock()
        now: datetime.datetime = datetime.datetime.now(tz=datetime.UTC)
        realm_id = uuid4()
        event: monitoring.CommandStartedEvent = monitoring.CommandStartedEvent(
            command={
                "findAndModify": "realms",
                "query": {"_id": realm_id, "revision_id": uuid4()},
                "update": {
                    "$set": {
                        "name": "acme",
                        "active_status": "deleted",
                        "deleted_at": now,
                        "created_at": now,
                        "updated_at": now,
                        "revision_id": uuid4(),
                        "realm_id": realm_id,
                        "object_id": ObjectId(),
                    }
                },
                "new": True,
                "upsert": True,
            },
            database_name="customers",
            request_id=4,
            connection_id=MagicMock(),
            operation_id=4,
        )
        request_hook = build_pymongo_request_hook()

        request_hook(span, event)

        attribute_value: str = span.set_attribute.call_args.args[1]
        parsed: dict[str, Any] = json.loads(attribute_value)
        assert parsed["collection"] == "realms"
        assert '"collection": "realms"' in attribute_value
        assert "<datetime>" in attribute_value
        assert "<UUID>" in attribute_value
        assert "<ObjectId>" in attribute_value
        assert len(attribute_value) <= MAX_DB_STATEMENT_LENGTH

    def test_find_and_modify_update_pipeline_with_datetime(self) -> None:
        """FindAndModify update pipelines with datetime must stay JSON-safe."""
        span: MagicMock = MagicMock()
        now: datetime.datetime = datetime.datetime.now(tz=datetime.UTC)
        event: monitoring.CommandStartedEvent = monitoring.CommandStartedEvent(
            command={
                "findAndModify": "realms",
                "query": {"_id": uuid4()},
                "update": [{"$set": {"updated_at": now}}],
                "new": True,
            },
            database_name="customers",
            request_id=5,
            connection_id=MagicMock(),
            operation_id=5,
        )
        request_hook = build_pymongo_request_hook()

        request_hook(span, event)

        attribute_value: str = span.set_attribute.call_args.args[1]
        parsed: dict[str, Any] = json.loads(attribute_value)
        assert parsed["collection"] == "realms"
        assert "<datetime>" in attribute_value
        assert isinstance(parsed["update"], list)

    def test_plain_update_records_collection_string(self) -> None:
        """A plain update command must record the collection name, not the updates array."""
        span: MagicMock = MagicMock()
        event: monitoring.CommandStartedEvent = monitoring.CommandStartedEvent(
            command={
                "update": "realms",
                "updates": [
                    {
                        "q": {"_id": uuid4()},
                        "u": {"$set": {"name": "acme"}},
                    }
                ],
            },
            database_name="customers",
            request_id=6,
            connection_id=MagicMock(),
            operation_id=6,
        )
        request_hook = build_pymongo_request_hook()

        request_hook(span, event)

        attribute_value: str = span.set_attribute.call_args.args[1]
        parsed: dict[str, Any] = json.loads(attribute_value)
        assert parsed["collection"] == "realms"
        assert "updates" in parsed
        assert parsed.get("update") is None

    def test_aggregate_one_records_collection_one(self) -> None:
        """aggregate: 1 must still record collection as the integer 1."""
        span: MagicMock = MagicMock()
        event: monitoring.CommandStartedEvent = monitoring.CommandStartedEvent(
            command={
                "aggregate": 1,
                "pipeline": [{"$match": {"active_status": "active"}}],
            },
            database_name="customers",
            request_id=7,
            connection_id=MagicMock(),
            operation_id=7,
        )
        request_hook = build_pymongo_request_hook()

        request_hook(span, event)

        attribute_value: str = span.set_attribute.call_args.args[1]
        parsed: dict[str, Any] = json.loads(attribute_value)
        assert parsed["collection"] == 1
