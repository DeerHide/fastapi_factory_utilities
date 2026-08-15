"""Smoke tests for Tier-1 driver-seam fixtures (no containers)."""

from fastapi import FastAPI
from taskiq import InMemoryBroker

from fastapi_factory_utilities.core.plugins.redis_plugin.constants import STATE_REDIS_CLIENT_KEY
from fastapi_factory_utilities.core.plugins.taskiq_plugin.depends import DEPENDS_SCHEDULER_COMPONENT_KEY
from fastapi_factory_utilities.core.testing.odm import build_mongomock_database
from fastapi_factory_utilities.core.testing.otel import build_in_memory_otel
from fastapi_factory_utilities.core.testing.redis import build_fakeredis
from fastapi_factory_utilities.core.testing.s3 import build_s3_bucket_resource, moto_s3_client
from fastapi_factory_utilities.core.testing.taskiq import build_in_memory_scheduler_component


class TestMongomockAdapter:
    """Tests for the pymongo-async-mock adapter."""

    async def test_aconnect_aclose_and_falsy_session(self) -> None:
        """Patched client exposes aconnect/aclose; start_session is falsy."""
        database = build_mongomock_database(database_name="smoke")
        client = database.client
        await client.aconnect()
        session = client.start_session()
        assert bool(session) is False
        await session.end_session()
        await client.aclose()


class TestFakeredis:
    """Tests for fakeredis wiring."""

    async def test_set_get_and_app_state(self) -> None:
        """FakeRedis round-trips a key and can be placed on app.state."""
        client = build_fakeredis()
        await client.set("k", "v")
        assert await client.get("k") == "v"
        app = FastAPI()
        setattr(app.state, STATE_REDIS_CLIENT_KEY, client)
        assert app.state.redis_client is client
        await client.aclose()


class TestInMemoryTaskiq:
    """Tests for InMemoryBroker scheduler component."""

    def test_broker_is_in_memory_and_on_state(self) -> None:
        """SchedulerComponent uses InMemoryBroker and lands on app.state."""
        app = FastAPI()
        component = build_in_memory_scheduler_component(app=app)
        assert isinstance(component.broker, InMemoryBroker)
        assert getattr(app.state, DEPENDS_SCHEDULER_COMPONENT_KEY) is component


class TestInMemoryOtel:
    """Tests for in-memory OTel providers."""

    def test_span_is_exported(self) -> None:
        """Spans created via the tracer provider are captured in-memory."""
        otel = build_in_memory_otel()
        tracer = otel.tracer_provider.get_tracer("test")
        with tracer.start_as_current_span("unit"):
            pass
        spans = otel.span_exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "unit"
        otel.tracer_provider.shutdown()
        otel.meter_provider.shutdown()


class TestMotoS3:
    """Tests for moto-backed S3BucketResource."""

    async def test_put_and_get_bytes(self) -> None:
        """Round-trip put_bytes / get_bytes through moto."""
        async with moto_s3_client() as (client, endpoint_url, names):
            bucket = build_s3_bucket_resource(
                client,
                bucket_name=names[0],
                endpoint_url=endpoint_url,
            )
            await bucket.put_bytes("obj", b"payload")
            assert await bucket.get_bytes("obj") == b"payload"
            assert await bucket.head_or_none("missing") is None
