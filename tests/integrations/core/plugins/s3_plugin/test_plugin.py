"""Integration tests for the S3 plugin against MinIO."""

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI

from fastapi_factory_utilities.core.plugins.s3_plugin import (
    STATE_BUCKET_PREFIX_KEY,
    STATE_S3_CLIENT_KEY,
    S3BucketResource,
    S3Plugin,
)
from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol
from fastapi_factory_utilities.core.services.status.services import StatusService


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
