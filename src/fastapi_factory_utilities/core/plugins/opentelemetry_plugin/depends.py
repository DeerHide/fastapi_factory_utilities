"""Provides FastAPI dependencies for the OpenTelemetry plugin."""

from fastapi import Request
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from taskiq import TaskiqDepends

from fastapi_factory_utilities.core.plugins.state import (
    METER_PROVIDER,
    OTEL_CONFIG,
    TRACER_PROVIDER,
    get_from_state,
)

from .configs import OpenTelemetryConfig


def depends_tracer_provider(request: Request = TaskiqDepends()) -> TracerProvider:
    """Get the tracer provider.

    Raises:
        PluginNotRegisteredError: If no ``OpenTelemetryPlugin`` was registered.
    """
    return get_from_state(request.app.state, TRACER_PROVIDER)


def depends_meter_provider(request: Request = TaskiqDepends()) -> MeterProvider:
    """Get the meter provider.

    Raises:
        PluginNotRegisteredError: If no ``OpenTelemetryPlugin`` was registered.
    """
    return get_from_state(request.app.state, METER_PROVIDER)


def depends_otel_config(request: Request = TaskiqDepends()) -> OpenTelemetryConfig:
    """Get the OpenTelemetry config.

    Raises:
        PluginNotRegisteredError: If no ``OpenTelemetryPlugin`` was registered.
    """
    return get_from_state(request.app.state, OTEL_CONFIG)
