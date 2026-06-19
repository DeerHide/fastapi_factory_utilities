"""Unit tests for ODM plugin configuration."""

import pytest
from pydantic import ValidationError

from fastapi_factory_utilities.core.plugins.odm_plugin.configs import ODMConfig

DEFAULT_CONNECTION_TIMEOUT_MS = 4000
DEFAULT_MAX_POOL_SIZE = 100
CUSTOM_MIN_POOL_SIZE = 5
CUSTOM_MAX_POOL_SIZE = 50
CUSTOM_MAX_IDLE_TIME_MS = 60000
CUSTOM_HEARTBEAT_FREQUENCY_MS = 5000


class TestODMConfig:
    """Tests for ``ODMConfig``."""

    def test_defaults(self) -> None:
        """Pool tuning fields default to pymongo-compatible values."""
        config: ODMConfig = ODMConfig(uri="mongodb://localhost:27017")

        assert config.database == "test"
        assert config.connection_timeout_ms == DEFAULT_CONNECTION_TIMEOUT_MS
        assert config.min_pool_size == 0
        assert config.max_pool_size == DEFAULT_MAX_POOL_SIZE
        assert config.max_idle_time_ms is None
        assert config.heartbeat_frequency_ms is None

    def test_custom_pool_settings(self) -> None:
        """Custom pool settings are accepted."""
        config: ODMConfig = ODMConfig(
            uri="mongodb://localhost:27017",
            database="youtube-integration",
            connection_timeout_ms=10000,
            min_pool_size=CUSTOM_MIN_POOL_SIZE,
            max_pool_size=CUSTOM_MAX_POOL_SIZE,
            max_idle_time_ms=CUSTOM_MAX_IDLE_TIME_MS,
            heartbeat_frequency_ms=CUSTOM_HEARTBEAT_FREQUENCY_MS,
        )

        assert config.min_pool_size == CUSTOM_MIN_POOL_SIZE
        assert config.max_pool_size == CUSTOM_MAX_POOL_SIZE
        assert config.max_idle_time_ms == CUSTOM_MAX_IDLE_TIME_MS
        assert config.heartbeat_frequency_ms == CUSTOM_HEARTBEAT_FREQUENCY_MS

    def test_rejects_unknown_fields(self) -> None:
        """Extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ODMConfig(uri="mongodb://localhost:27017", unknown_field=True)
