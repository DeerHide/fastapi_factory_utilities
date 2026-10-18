"""Tests for OpenTelemetry plugin configuration models."""

import pytest
from pydantic import ValidationError

from fastapi_factory_utilities.core.plugins.opentelemetry_plugin.configs import (
    InstrumentationName,
    OpenTelemetryConfig,
    OpenTelemetryMeterConfig,
)

DEFAULT_INTERVAL_MS = 60_000
DEFAULT_TIMEOUT_MS = 10_000
CUSTOM_INTERVAL_MS = 30_000
INVALID_INTERVAL_MS = 5_000
INVALID_TIMEOUT_MS = 10_000


class TestOpenTelemetryMeterConfigDefaults:
    """Defaults and validation for ``OpenTelemetryMeterConfig``."""

    def test_default_interval_is_one_minute(self) -> None:
        """Default export interval is 60s to avoid flooding backends."""
        config = OpenTelemetryMeterConfig()
        assert config.reader_interval_millis == DEFAULT_INTERVAL_MS

    def test_default_timeout_is_ten_seconds(self) -> None:
        """Default export timeout is 10s and stays below the interval."""
        config = OpenTelemetryMeterConfig()
        assert config.reader_timeout_millis == DEFAULT_TIMEOUT_MS
        assert config.reader_timeout_millis <= config.reader_interval_millis

    def test_timeout_equal_to_interval_is_allowed(self) -> None:
        """Timeout may equal the interval (``<=``)."""
        config = OpenTelemetryMeterConfig(
            reader_interval_millis=CUSTOM_INTERVAL_MS,
            reader_timeout_millis=CUSTOM_INTERVAL_MS,
        )
        assert config.reader_timeout_millis == CUSTOM_INTERVAL_MS

    def test_timeout_greater_than_interval_raises(self) -> None:
        """Timeout must not exceed the interval."""
        with pytest.raises(ValidationError, match="reader_timeout_millis"):
            OpenTelemetryMeterConfig(
                reader_interval_millis=INVALID_INTERVAL_MS,
                reader_timeout_millis=INVALID_TIMEOUT_MS,
            )


class TestRuntimeInstrumentationOptIn:
    """Runtime / system metrics instrumentors are opt-in."""

    def test_default_instrumentations_exclude_runtime(self) -> None:
        """Default list omits asyncio and system_metrics."""
        config = OpenTelemetryConfig()
        assert InstrumentationName.ASYNCIO not in config.instrumentations
        assert InstrumentationName.SYSTEM_METRICS not in config.instrumentations
        assert InstrumentationName.FASTAPI in config.instrumentations
        assert InstrumentationName.HTTPX in config.instrumentations
        assert config.enable_runtime_instrumentation is False

    def test_enable_runtime_instrumentation_flag_defaults_false(self) -> None:
        """The opt-in flag is disabled by default."""
        assert OpenTelemetryConfig().enable_runtime_instrumentation is False
