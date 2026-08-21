"""Provides the OpenTelemetry plugin."""

import asyncio
from typing import Self, cast

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from structlog.stdlib import BoundLogger, get_logger

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.plugins.state import METER_PROVIDER, OTEL_CONFIG, TRACER_PROVIDER

from .builder import OpenTelemetryPluginBuilder
from .configs import OpenTelemetryConfig
from .exceptions import OpenTelemetryPluginBaseException, OpenTelemetryPluginConfigError
from .instruments import apply_instruments

__all__: list[str] = [
    "OpenTelemetryConfig",
    "OpenTelemetryPluginBaseException",
    "OpenTelemetryPluginBuilder",
    "OpenTelemetryPluginConfigError",
]

_logger: BoundLogger = get_logger()


class OpenTelemetryPlugin(PluginAbstract):
    """OpenTelemetry plugin.

    Does not register a StatusService component: it is not a data path.
    A missing collector must not mark the pod not-ready.
    """

    SECONDS_TO_MS_MULTIPLIER: int = 1000

    def __init__(self) -> None:
        """Initialize the OpenTelemetry plugin."""
        super().__init__()
        self._otel_config: OpenTelemetryConfig | None = None
        self._tracer_provider: TracerProvider | None = None
        self._meter_provider: MeterProvider | None = None

    def _build(self) -> Self:
        """Build the OpenTelemetry plugin."""
        assert self._application is not None
        # Build the OpenTelemetry Resources, TracerProvider and MeterProvider
        try:
            otel_builder: OpenTelemetryPluginBuilder = OpenTelemetryPluginBuilder(
                application=self._application
            ).build_all()
        except OpenTelemetryPluginBaseException as exception:
            _logger.error(f"OpenTelemetry plugin failed to start. {exception}")
            raise
        # Configuration is never None at this point (checked in the builder and raises an exception)
        self._otel_config = cast(OpenTelemetryConfig, otel_builder.config)
        self._tracer_provider = otel_builder.tracer_provider
        self._meter_provider = otel_builder.meter_provider
        return self

    def _instrument(self) -> None:
        """Instrument the FastAPI application."""
        assert self._application is not None
        assert self._tracer_provider is not None
        assert self._meter_provider is not None
        assert self._otel_config is not None

        apply_instruments(self._application, self._otel_config, self._meter_provider, self._tracer_provider)

    def on_load(self) -> None:
        """On load."""
        assert self._application is not None
        # Build the OpenTelemetry Resources, TracerProvider and MeterProvider
        self._build()
        assert self._tracer_provider is not None
        assert self._meter_provider is not None
        assert self._otel_config is not None
        self._add_to_state(key=TRACER_PROVIDER, value=self._tracer_provider)
        self._add_to_state(key=METER_PROVIDER, value=self._meter_provider)
        self._add_to_state(key=OTEL_CONFIG, value=self._otel_config)
        # Instrument the FastAPI application and AioHttpClient, ...
        self._instrument()
        _logger.debug(f"OpenTelemetry plugin loaded. {self._otel_config.activate=}")

    async def on_startup(self) -> None:
        """On startup."""
        pass

    async def close_tracer_provider(self) -> None:
        """Close the tracer provider."""
        assert self._tracer_provider is not None
        assert self._otel_config is not None
        self._tracer_provider.force_flush(
            timeout_millis=self._otel_config.closing_timeout * self.SECONDS_TO_MS_MULTIPLIER
        )
        # No Delay for the shutdown of the tracer provider
        try:
            self._tracer_provider.shutdown()
        except Exception as exception:
            _logger.error("OpenTelemetry plugin failed to close the tracer provider.", error=exception)

    async def close_meter_provider(self) -> None:
        """Close the meter provider."""
        assert self._meter_provider is not None
        assert self._otel_config is not None
        self._meter_provider.force_flush(
            timeout_millis=self._otel_config.closing_timeout * self.SECONDS_TO_MS_MULTIPLIER
        )
        try:
            self._meter_provider.shutdown(
                timeout_millis=self._otel_config.closing_timeout * self.SECONDS_TO_MS_MULTIPLIER
            )
        except Exception as exception:
            _logger.error("OpenTelemetry plugin failed to close the meter provider.", error=exception)

    async def on_shutdown(self) -> None:
        """On shutdown."""
        _logger.debug("OpenTelemetry plugin stop requested. Flushing and closing...")

        await asyncio.gather(
            self.close_tracer_provider(),
            self.close_meter_provider(),
        )

        _logger.debug("OpenTelemetry plugin closed.")
