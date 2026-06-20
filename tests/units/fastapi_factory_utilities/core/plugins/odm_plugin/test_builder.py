"""Unit tests for ODM builder."""

from typing import Any
from unittest.mock import MagicMock, patch

from pymongo.server_api import ServerApiVersion

from fastapi_factory_utilities.core.plugins.odm_plugin.builder import ODMBuilder
from fastapi_factory_utilities.core.plugins.odm_plugin.configs import ODMConfig

DEFAULT_CONNECTION_TIMEOUT_MS = 4000
DEFAULT_MAX_POOL_SIZE = 100
CUSTOM_MIN_POOL_SIZE = 5
CUSTOM_MAX_POOL_SIZE = 50
CUSTOM_MAX_IDLE_TIME_MS = 60000
CUSTOM_HEARTBEAT_FREQUENCY_MS = 5000


class TestODMBuilderBuildClient:
    """Tests for ``ODMBuilder.build_client``."""

    @patch("fastapi_factory_utilities.core.plugins.odm_plugin.builder.AsyncMongoClient")
    def test_build_client_passes_pool_settings(self, mock_async_mongo_client: MagicMock) -> None:
        """Pool tuning from config is forwarded to ``AsyncMongoClient``."""
        odm_config: ODMConfig = ODMConfig(
            uri="mongodb://localhost:27017",
            min_pool_size=CUSTOM_MIN_POOL_SIZE,
            max_pool_size=CUSTOM_MAX_POOL_SIZE,
            max_idle_time_ms=CUSTOM_MAX_IDLE_TIME_MS,
            heartbeat_frequency_ms=CUSTOM_HEARTBEAT_FREQUENCY_MS,
        )
        builder: ODMBuilder = ODMBuilder(application=MagicMock(), odm_config=odm_config)

        builder.build_client()

        mock_async_mongo_client.assert_called_once()
        client_kwargs: dict[str, Any] = mock_async_mongo_client.call_args.kwargs
        assert client_kwargs["host"] == "mongodb://localhost:27017"
        assert client_kwargs["connect"] is True
        assert client_kwargs["connectTimeoutMS"] == DEFAULT_CONNECTION_TIMEOUT_MS
        assert client_kwargs["serverSelectionTimeoutMS"] == DEFAULT_CONNECTION_TIMEOUT_MS
        assert client_kwargs["minPoolSize"] == CUSTOM_MIN_POOL_SIZE
        assert client_kwargs["maxPoolSize"] == CUSTOM_MAX_POOL_SIZE
        assert client_kwargs["maxIdleTimeMS"] == CUSTOM_MAX_IDLE_TIME_MS
        assert client_kwargs["heartbeatFrequencyMS"] == CUSTOM_HEARTBEAT_FREQUENCY_MS
        assert client_kwargs["server_api"].version == ServerApiVersion.V1
        assert client_kwargs["tz_aware"] is True

    @patch("fastapi_factory_utilities.core.plugins.odm_plugin.builder.AsyncMongoClient")
    def test_build_client_omits_optional_pool_settings_when_unset(
        self,
        mock_async_mongo_client: MagicMock,
    ) -> None:
        """Optional pool settings are omitted when not configured."""
        odm_config: ODMConfig = ODMConfig(uri="mongodb://localhost:27017")
        builder: ODMBuilder = ODMBuilder(application=MagicMock(), odm_config=odm_config)

        builder.build_client()

        client_kwargs: dict[str, Any] = mock_async_mongo_client.call_args.kwargs
        assert "maxIdleTimeMS" not in client_kwargs
        assert "heartbeatFrequencyMS" not in client_kwargs
        assert client_kwargs["minPoolSize"] == 0
        assert client_kwargs["maxPoolSize"] == DEFAULT_MAX_POOL_SIZE

    @patch("fastapi_factory_utilities.core.plugins.odm_plugin.builder.AsyncMongoClient")
    def test_build_client_omits_max_idle_time_ms_when_zero(
        self,
        mock_async_mongo_client: MagicMock,
    ) -> None:
        """Zero max idle time means no limit and must not be forwarded to PyMongo."""
        odm_config: ODMConfig = ODMConfig(
            uri="mongodb://localhost:27017",
            max_idle_time_ms=0,
            heartbeat_frequency_ms=0,
        )
        builder: ODMBuilder = ODMBuilder(application=MagicMock(), odm_config=odm_config)

        builder.build_client()

        client_kwargs: dict[str, Any] = mock_async_mongo_client.call_args.kwargs
        assert "maxIdleTimeMS" not in client_kwargs
        assert "heartbeatFrequencyMS" not in client_kwargs
