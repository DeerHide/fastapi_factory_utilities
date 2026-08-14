"""Unit tests for RedisPlugin."""

# pylint: disable=protected-access

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.plugins.redis_plugin.configs import RedisCredentialsConfig
from fastapi_factory_utilities.core.plugins.redis_plugin.constants import (
    STATE_REDIS_CLIENT_KEY,
    STATE_REDIS_PLUGIN_KEY,
)
from fastapi_factory_utilities.core.plugins.redis_plugin.exceptions import RedisPluginNotStartedError
from fastapi_factory_utilities.core.plugins.redis_plugin.plugins import RedisPlugin
from fastapi_factory_utilities.core.services.status.enums import (
    ComponentTypeEnum,
    HealthStatusEnum,
    ReadinessStatusEnum,
)
from fastapi_factory_utilities.core.services.status.services import StatusService


class TestRedisPluginBuildKey:
    """Tests for ``RedisPlugin.build_key``."""

    def test_prefix_and_parts(self) -> None:
        """Built key carries the service prefix and joined parts."""
        plugin: RedisPlugin = RedisPlugin(
            name_suffix="customers-backend",
            redis_credentials_config=RedisCredentialsConfig(url="redis://localhost:6379"),
        )
        assert plugin.build_key("count", "customers", "abc123") == "customers-backend:count:customers:abc123"

    def test_empty_parts_rejected(self) -> None:
        """No parts or empty string parts raise ValueError."""
        plugin: RedisPlugin = RedisPlugin(
            name_suffix="svc",
            redis_credentials_config=RedisCredentialsConfig(url="redis://localhost:6379"),
        )
        with pytest.raises(ValueError):
            plugin.build_key()
        with pytest.raises(ValueError):
            plugin.build_key("count", "", "digest")

    def test_empty_name_suffix_rejected(self) -> None:
        """Empty name_suffix is rejected at construction."""
        with pytest.raises(ValueError):
            RedisPlugin(name_suffix="")


class TestRedisPluginLifecycle:
    """Tests for RedisPlugin load / startup / shutdown with mocks."""

    def test_inheritance(self) -> None:
        """RedisPlugin inherits from PluginAbstract."""
        plugin: RedisPlugin = RedisPlugin(
            name_suffix="svc",
            redis_credentials_config=RedisCredentialsConfig(url="redis://localhost:6379"),
        )
        assert isinstance(plugin, PluginAbstract)

    def test_on_load_uses_injected_credentials(self) -> None:
        """Injected credentials skip YAML resolution."""
        config: RedisCredentialsConfig = RedisCredentialsConfig(url="redis://injected:6379")
        plugin: RedisPlugin = RedisPlugin(name_suffix="svc", redis_credentials_config=config)
        mock_app: MagicMock = MagicMock()
        mock_app.PACKAGE_NAME = "test"
        plugin._application = mock_app
        with patch(
            "fastapi_factory_utilities.core.plugins.redis_plugin.plugins.build_redis_credentials_config"
        ) as mock_build:
            plugin.on_load()
            mock_build.assert_not_called()
        assert plugin._redis_credentials_config is config

    async def test_on_startup_pings_and_registers_state(self) -> None:
        """Startup creates client, pings, registers CACHE status, and stores state."""
        plugin: RedisPlugin = RedisPlugin(
            name_suffix="svc",
            redis_credentials_config=RedisCredentialsConfig(url="redis://localhost:6379"),
        )
        mock_app: MagicMock = MagicMock()
        fastapi_app: FastAPI = FastAPI()
        mock_app.get_asgi_app.return_value = fastapi_app
        mock_app.get_status_service.return_value = StatusService()
        plugin._application = mock_app
        plugin.on_load()

        mock_client: AsyncMock = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)
        mock_client.aclose = AsyncMock()

        with patch(
            "fastapi_factory_utilities.core.plugins.redis_plugin.plugins.Redis.from_url",
            return_value=mock_client,
        ) as from_url:
            await plugin.on_startup()
            from_url.assert_called_once_with("redis://localhost:6379", decode_responses=True)

        mock_client.ping.assert_awaited_once()
        assert getattr(fastapi_app.state, STATE_REDIS_CLIENT_KEY) is mock_client
        assert getattr(fastapi_app.state, STATE_REDIS_PLUGIN_KEY) is plugin

        status_service: StatusService = mock_app.get_status_service.return_value
        by_type = status_service.get_components_status_by_type()
        assert ComponentTypeEnum.CACHE in by_type
        cache_statuses = list(by_type[ComponentTypeEnum.CACHE].values())
        assert len(cache_statuses) == 1
        assert cache_statuses[0]["health"] == HealthStatusEnum.HEALTHY
        assert cache_statuses[0]["readiness"] == ReadinessStatusEnum.READY

        await plugin.on_shutdown()
        mock_client.aclose.assert_awaited_once()

    async def test_on_startup_ping_failure_marks_unhealthy(self) -> None:
        """Failed ping marks CACHE unhealthy and re-raises."""
        plugin: RedisPlugin = RedisPlugin(
            name_suffix="svc",
            redis_credentials_config=RedisCredentialsConfig(url="redis://localhost:6379"),
        )
        mock_app: MagicMock = MagicMock()
        fastapi_app: FastAPI = FastAPI()
        mock_app.get_asgi_app.return_value = fastapi_app
        mock_app.get_status_service.return_value = StatusService()
        plugin._application = mock_app
        plugin.on_load()

        mock_client: AsyncMock = AsyncMock()
        mock_client.ping = AsyncMock(side_effect=ConnectionError("down"))
        mock_client.aclose = AsyncMock()

        with patch(
            "fastapi_factory_utilities.core.plugins.redis_plugin.plugins.Redis.from_url",
            return_value=mock_client,
        ):
            with pytest.raises(ConnectionError):
                await plugin.on_startup()

        status_service: StatusService = mock_app.get_status_service.return_value
        by_type = status_service.get_components_status_by_type()
        cache_statuses = list(by_type[ComponentTypeEnum.CACHE].values())
        assert cache_statuses[0]["health"] == HealthStatusEnum.UNHEALTHY
        mock_client.aclose.assert_awaited_once()

    def test_client_before_startup_raises_named_error(self) -> None:
        """Accessing the client before on_startup raises RedisPluginNotStartedError."""
        plugin: RedisPlugin = RedisPlugin(
            name_suffix="svc",
            redis_credentials_config=RedisCredentialsConfig(url="redis://localhost:6379"),
        )
        with pytest.raises(RedisPluginNotStartedError, match="call on_startup first"):
            _ = plugin.client
