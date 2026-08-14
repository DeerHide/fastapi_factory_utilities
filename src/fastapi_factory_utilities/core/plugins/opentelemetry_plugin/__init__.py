"""OpenTelemetry Plugin Module."""

# ruff: noqa: E402
# pylint: disable=wrong-import-position
from fastapi_factory_utilities.core.plugins.extras import require_extra

require_extra("otel", "opentelemetry.sdk")

from .configs import OpenTelemetryConfig, OpenTelemetryMeterConfig, OpenTelemetryTracerConfig
from .exceptions import OpenTelemetryPluginBaseException, OpenTelemetryPluginConfigError
from .plugins import OpenTelemetryPlugin, depends_meter_provider, depends_otel_config, depends_tracer_provider

__all__: list[str] = [
    "OpenTelemetryConfig",
    "OpenTelemetryMeterConfig",
    "OpenTelemetryPlugin",
    "OpenTelemetryPluginBaseException",
    "OpenTelemetryPluginConfigError",
    "OpenTelemetryTracerConfig",
    "depends_meter_provider",
    "depends_otel_config",
    "depends_tracer_provider",
]
