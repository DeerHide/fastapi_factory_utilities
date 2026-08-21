"""Unit tests for Redis plugin depends."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI

from fastapi_factory_utilities.core.plugins.redis_plugin.configs import RedisCredentialsConfig
from fastapi_factory_utilities.core.plugins.redis_plugin.constants import (
    STATE_REDIS_CLIENT_KEY,
    STATE_REDIS_PLUGIN_KEY,
)
from fastapi_factory_utilities.core.plugins.redis_plugin.depends import depends_redis, depends_redis_plugin
from fastapi_factory_utilities.core.plugins.redis_plugin.plugins import RedisPlugin
from fastapi_factory_utilities.core.plugins.state import PluginNotRegisteredError


class TestDependsRedis:
    """Tests for ``depends_redis`` and ``depends_redis_plugin``."""

    def test_depends_redis_returns_client(self) -> None:
        """Client is read from application state."""
        mock_client: MagicMock = MagicMock()
        mock_request: MagicMock = MagicMock()
        setattr(mock_request.app.state, STATE_REDIS_CLIENT_KEY, mock_client)
        assert depends_redis(mock_request) is mock_client

    def test_depends_redis_plugin_returns_plugin(self) -> None:
        """Plugin is read from application state."""
        plugin: RedisPlugin = RedisPlugin(
            name_suffix="svc",
            redis_credentials_config=RedisCredentialsConfig(url="redis://localhost:6379"),
        )
        mock_request: MagicMock = MagicMock()
        setattr(mock_request.app.state, STATE_REDIS_PLUGIN_KEY, plugin)
        assert depends_redis_plugin(mock_request) is plugin

    def test_depends_redis_names_missing_plugin(self) -> None:
        """Missing Redis client is PluginNotRegisteredError, not AttributeError."""

        class _Req:
            app = FastAPI()

        with pytest.raises(PluginNotRegisteredError, match="RedisPlugin"):
            depends_redis(_Req())  # type: ignore[arg-type]

    def test_depends_redis_plugin_names_missing_plugin(self) -> None:
        """Missing Redis plugin is PluginNotRegisteredError, not AttributeError."""

        class _Req:
            app = FastAPI()

        with pytest.raises(PluginNotRegisteredError, match="RedisPlugin"):
            depends_redis_plugin(_Req())  # type: ignore[arg-type]
