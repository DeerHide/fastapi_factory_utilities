"""Integration tests for the S3 plugin against MinIO."""

import urllib.request
from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from opentelemetry.instrumentation.botocore import AiobotocoreInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from testcontainers.community.minio import MinioContainer

from fastapi_factory_utilities.core.plugins.s3_plugin import (
    STATE_BUCKET_PREFIX_KEY,
    STATE_S3_CLIENT_KEY,
    S3BucketResource,
    S3Config,
    S3Plugin,
)
from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol
from fastapi_factory_utilities.core.services.status.services import StatusService
from tests.fixtures.minio import build_s3_config_from_container


class TestS3PluginIntegration:
    """Integration tests for ``S3Plugin`` with a real MinIO container."""

    @pytest.fixture
    def mock_application(self) -> MagicMock:
        """Create a mock application with FastAPI state and status service."""
        app: MagicMock = MagicMock(spec=ApplicationAbstractProtocol)
        app.PACKAGE_NAME = "test"
        fastapi_app: FastAPI = FastAPI()
        app.get_asgi_app.return_value = fastapi_app
        app.get_status_service.return_value = StatusService()
        return app

    async def test_plugin_lifecycle(
        self,
        s3_plugin_factory: Callable[[list[str] | None], S3Plugin],
        mock_application: MagicMock,
        s3_buckets: dict[str, str],
    ) -> None:
        """Load, start, and shut down the plugin against live MinIO buckets."""
        plugin: S3Plugin = s3_plugin_factory(None)
        plugin.set_application(mock_application)
        plugin.on_load()
        await plugin.on_startup()

        state = mock_application.get_asgi_app().state
        client = getattr(state, STATE_S3_CLIENT_KEY)
        assert client is not None
        listed = await client.list_buckets()
        listed_names: set[str] = {bucket["Name"] for bucket in listed.get("Buckets", [])}
        assert s3_buckets["media"] in listed_names
        assert s3_buckets["thumbs"] in listed_names

        media: S3BucketResource = getattr(state, f"{STATE_BUCKET_PREFIX_KEY}media")
        thumbs: S3BucketResource = getattr(state, f"{STATE_BUCKET_PREFIX_KEY}thumbs")
        assert media.client is thumbs.client is client
        assert media.bucket_name == s3_buckets["media"]
        assert thumbs.bucket_name == s3_buckets["thumbs"]

        await plugin.on_shutdown()

    async def test_put_get_round_trip_per_bucket(
        self,
        s3_plugin_factory: Callable[[list[str] | None], S3Plugin],
        mock_application: MagicMock,
    ) -> None:
        """Put and get objects through each named bucket resource."""
        plugin: S3Plugin = s3_plugin_factory(None)
        plugin.set_application(mock_application)
        plugin.on_load()
        await plugin.on_startup()

        state = mock_application.get_asgi_app().state
        for key in ("media", "thumbs"):
            resource: S3BucketResource = getattr(state, f"{STATE_BUCKET_PREFIX_KEY}{key}")
            body: bytes = f"hello-{key}".encode()
            await resource.client.put_object(
                Bucket=resource.bucket_name,
                Key=f"{key}.txt",
                Body=body,
            )
            response = await resource.client.get_object(Bucket=resource.bucket_name, Key=f"{key}.txt")
            async with response["Body"] as stream:
                retrieved: bytes = await stream.read()
            assert retrieved == body

        await plugin.on_shutdown()

    async def test_keys_subset(
        self,
        s3_plugin_factory: Callable[[list[str] | None], S3Plugin],
        mock_application: MagicMock,
    ) -> None:
        """Plugin with keys subset only registers selected bucket resources."""
        plugin: S3Plugin = s3_plugin_factory(["media"])
        plugin.set_application(mock_application)
        plugin.on_load()
        await plugin.on_startup()

        state = mock_application.get_asgi_app().state
        assert hasattr(state, f"{STATE_BUCKET_PREFIX_KEY}media")
        assert not hasattr(state, f"{STATE_BUCKET_PREFIX_KEY}thumbs")

        await plugin.on_shutdown()

    async def test_resource_helpers_round_trip(
        self,
        s3_plugin_factory: Callable[[list[str] | None], S3Plugin],
        mock_application: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Exercise put/get/list/head/delete/download helpers against MinIO."""
        plugin: S3Plugin = s3_plugin_factory(None)
        plugin.set_application(mock_application)
        plugin.on_load()
        await plugin.on_startup()

        state = mock_application.get_asgi_app().state
        media: S3BucketResource = getattr(state, f"{STATE_BUCKET_PREFIX_KEY}media")

        url: str = await media.put_bytes("helpers/a.txt", b"hello", content_type="text/plain")
        assert media.key_from_url(url) == "helpers/a.txt"
        assert await media.get_bytes("helpers/a.txt") == b"hello"
        assert await media.head_or_none("helpers/a.txt") is not None
        assert "helpers/a.txt" in await media.list_keys("helpers/")

        dest: Path = tmp_path / "out.txt"
        await media.download_to_file("helpers/a.txt", dest)
        assert dest.read_bytes() == b"hello"

        local: Path = tmp_path / "in.bin"
        local.write_bytes(b"file-bytes")
        file_url: str = await media.put_file("helpers/b.bin", local)
        assert await media.get_bytes(media.key_from_url(file_url) or "") == b"file-bytes"

        await media.delete("helpers/a.txt")
        assert await media.head_or_none("helpers/a.txt") is None

        await plugin.on_shutdown()

    async def test_presigned_get_url(
        self,
        minio_container: object,
        s3_buckets: dict[str, str],
        mock_application: MagicMock,
    ) -> None:
        """Presign against the MinIO endpoint itself (no path prefix) and fetch."""
        assert isinstance(minio_container, MinioContainer)
        config: S3Config = build_s3_config_from_container(minio_container=minio_container, buckets=s3_buckets)
        # Sign against the same endpoint (host-only); no public path prefix.
        config = S3Config.model_validate(
            {
                **config.model_dump(),
                "presign_endpoint_url": config.endpoint_url,
                "presign_expiry_seconds": 60,
            }
        )
        plugin: S3Plugin = S3Plugin(s3_config=config)
        plugin.set_application(mock_application)
        plugin.on_load()
        await plugin.on_startup()

        state = mock_application.get_asgi_app().state
        media: S3BucketResource = getattr(state, f"{STATE_BUCKET_PREFIX_KEY}media")
        await media.put_bytes("presign.txt", b"signed")
        url: str = await media.presigned_get_url("presign.txt")
        assert "X-Amz-Signature=" in url or "X-Amz-Credential=" in url

        # Fetch via the shared data-plane client (presigned URL targets MinIO).
        with urllib.request.urlopen(url) as response:
            assert response.read() == b"signed"

        await plugin.on_shutdown()

    async def test_aiobotocore_instrumentation_emits_span(
        self,
        s3_plugin_factory: Callable[[list[str] | None], S3Plugin],
        mock_application: MagicMock,
    ) -> None:
        """AiobotocoreInstrumentor records a client span for put_object."""
        exporter: InMemorySpanExporter = InMemorySpanExporter()
        provider: TracerProvider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        instrumentor: AiobotocoreInstrumentor = AiobotocoreInstrumentor()
        instrumentor.instrument(tracer_provider=provider)
        try:
            plugin: S3Plugin = s3_plugin_factory(["media"])
            plugin.set_application(mock_application)
            plugin.on_load()
            await plugin.on_startup()

            state = mock_application.get_asgi_app().state
            media: S3BucketResource = getattr(state, f"{STATE_BUCKET_PREFIX_KEY}media")
            await media.put_bytes("otel.txt", b"traced")

            spans = exporter.get_finished_spans()
            assert any("S3" in (span.name or "") or "PutObject" in (span.name or "") for span in spans), (
                f"expected S3 span, got {[span.name for span in spans]}"
            )
            await plugin.on_shutdown()
        finally:
            instrumentor.uninstrument()
