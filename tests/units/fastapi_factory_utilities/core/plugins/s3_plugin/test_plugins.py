"""Unit tests for S3 plugin lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from fastapi import FastAPI

from fastapi_factory_utilities.core.plugins.s3_plugin.configs import S3Config
from fastapi_factory_utilities.core.plugins.s3_plugin.constants import (
    STATE_BUCKET_PREFIX_KEY,
    STATE_S3_CLIENT_KEY,
)
from fastapi_factory_utilities.core.plugins.s3_plugin.exceptions import S3BucketNotFoundError
from fastapi_factory_utilities.core.plugins.s3_plugin.plugins import S3Plugin
from fastapi_factory_utilities.core.plugins.s3_plugin.resources import S3BucketResource
from fastapi_factory_utilities.core.services.status.enums import HealthStatusEnum, ReadinessStatusEnum
from fastapi_factory_utilities.core.services.status.services import StatusService


def _config() -> S3Config:
    """Build a test S3Config with two buckets."""
    return S3Config.model_validate(
        {
            "endpoint_url": "http://localhost:9000",
            "access_key_id": "akid",
            "secret_access_key": "secret",
            "buckets": {"media": "media-bucket", "thumbs": "thumbs-bucket"},
        }
    )


def _mock_application() -> MagicMock:
    """Create a mock application with FastAPI state and status service."""
    app: MagicMock = MagicMock()
    app.PACKAGE_NAME = "test"
    fastapi_app: FastAPI = FastAPI()
    app.get_asgi_app.return_value = fastapi_app
    app.get_status_service.return_value = StatusService()
    return app


@asynccontextmanager
async def _fake_client_cm(client: MagicMock) -> AsyncIterator[MagicMock]:
    """Async context manager yielding a fake S3 client."""
    yield client


class TestS3PluginWarmClient:
    """Tests for ``S3Plugin._warm_client``."""

    # pylint: disable=protected-access

    @pytest.mark.asyncio
    async def test_warm_client_swallows_failures(self) -> None:
        """Warm failures are logged but do not abort startup."""
        plugin: S3Plugin = S3Plugin(s3_config=_config())
        mock_client: MagicMock = MagicMock()
        mock_client.list_buckets = AsyncMock(side_effect=ConnectionError("unavailable"))

        await plugin._warm_client(client=mock_client)

        mock_client.list_buckets.assert_awaited_once()


class TestS3PluginStartup:
    """Tests for ``S3Plugin`` startup / shutdown."""

    # pylint: disable=protected-access

    @pytest.mark.asyncio
    async def test_startup_registers_shared_client_and_bucket_resources(self) -> None:
        """Startup enters the client once and registers per-bucket resources."""
        mock_client: MagicMock = MagicMock()
        mock_client.list_buckets = AsyncMock(return_value={"Buckets": []})
        mock_client.head_bucket = AsyncMock(return_value={})

        mock_session: MagicMock = MagicMock()
        mock_session.client.return_value = _fake_client_cm(mock_client)

        mock_app: MagicMock = _mock_application()
        plugin: S3Plugin = S3Plugin(s3_config=_config())
        plugin.set_application(mock_app)
        plugin.on_load()

        with patch("fastapi_factory_utilities.core.plugins.s3_plugin.plugins.Session", return_value=mock_session):
            await plugin.on_startup()

        state = mock_app.get_asgi_app().state
        assert getattr(state, STATE_S3_CLIENT_KEY) is mock_client
        media: S3BucketResource = getattr(state, f"{STATE_BUCKET_PREFIX_KEY}media")
        thumbs: S3BucketResource = getattr(state, f"{STATE_BUCKET_PREFIX_KEY}thumbs")
        assert media.bucket_name == "media-bucket"
        assert thumbs.bucket_name == "thumbs-bucket"
        assert media.client is thumbs.client is mock_client
        mock_client.head_bucket.assert_any_await(Bucket="media-bucket")
        mock_client.head_bucket.assert_any_await(Bucket="thumbs-bucket")

        await plugin.on_shutdown()
        assert plugin._s3_client is None

    @pytest.mark.asyncio
    async def test_missing_bucket_marks_unhealthy_and_reraises(self) -> None:
        """Missing configured buckets mark STORAGE unhealthy and re-raise."""
        mock_client: MagicMock = MagicMock()
        mock_client.list_buckets = AsyncMock(return_value={"Buckets": []})
        mock_client.head_bucket = AsyncMock(
            side_effect=ClientError(
                error_response={"Error": {"Code": "404", "Message": "Not Found"}},
                operation_name="HeadBucket",
            )
        )

        mock_session: MagicMock = MagicMock()
        mock_session.client.return_value = _fake_client_cm(mock_client)

        mock_subject: MagicMock = MagicMock()
        mock_status_service: MagicMock = MagicMock()
        mock_status_service.register_component_instance.return_value = mock_subject

        mock_app: MagicMock = _mock_application()
        mock_app.get_status_service.return_value = mock_status_service

        plugin: S3Plugin = S3Plugin(s3_config=_config())
        plugin.set_application(mock_app)
        plugin.on_load()

        with patch("fastapi_factory_utilities.core.plugins.s3_plugin.plugins.Session", return_value=mock_session):
            with pytest.raises(S3BucketNotFoundError):
                await plugin.on_startup()

        status: Any = mock_subject.on_next.call_args.kwargs["value"]
        assert status["health"] == HealthStatusEnum.UNHEALTHY
        assert status["readiness"] == ReadinessStatusEnum.NOT_READY
        assert plugin._exit_stack is None

    @pytest.mark.asyncio
    async def test_connect_failure_marks_unhealthy_and_reraises(self) -> None:
        """Client enter failures mark STORAGE unhealthy and propagate."""
        failing_cm: MagicMock = MagicMock()
        failing_cm.__aenter__ = AsyncMock(side_effect=ConnectionError("S3 unavailable"))
        failing_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session: MagicMock = MagicMock()
        mock_session.client.return_value = failing_cm

        mock_subject: MagicMock = MagicMock()
        mock_status_service: MagicMock = MagicMock()
        mock_status_service.register_component_instance.return_value = mock_subject

        mock_app: MagicMock = _mock_application()
        mock_app.get_status_service.return_value = mock_status_service

        plugin: S3Plugin = S3Plugin(s3_config=_config())
        plugin.set_application(mock_app)
        plugin.on_load()

        with patch("fastapi_factory_utilities.core.plugins.s3_plugin.plugins.Session", return_value=mock_session):
            with pytest.raises(ConnectionError, match="S3 unavailable"):
                await plugin.on_startup()

        status: Any = mock_subject.on_next.call_args.kwargs["value"]
        assert status["health"] == HealthStatusEnum.UNHEALTHY
        assert status["readiness"] == ReadinessStatusEnum.NOT_READY
