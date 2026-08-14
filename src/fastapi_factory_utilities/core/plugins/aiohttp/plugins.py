"""Aiohttp client plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.plugins.state import (
    AIOHTTP_RESOURCE_PREFIX,
    METER_PROVIDER,
    TRACER_PROVIDER,
)

from .builder import AioHttpClientBuilder

if TYPE_CHECKING:
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.trace import TracerProvider


class AioHttpClientPlugin(PluginAbstract):
    """Aiohttp client plugin."""

    def __init__(self, keys: list[str]) -> None:
        """Initialize the Aiohttp client plugin.

        Args:
            keys (list[str]): The keys of the dependencies configurations.
        """
        super().__init__()
        self._keys: list[str] = keys

    def on_load(self) -> None:
        """On load."""
        if self._application is None:
            raise ValueError("The application package name is not set")

        self._builder: AioHttpClientBuilder = AioHttpClientBuilder(keys=self._keys, application=self._application)
        self._builder.build_configs()

    async def on_startup(self) -> None:
        """On startup."""
        self._builder.build_resources()

        # Get OpenTelemetry providers from application state if available
        tracer_provider: TracerProvider | None = None
        meter_provider: MeterProvider | None = None
        if self._application is not None:
            app_state = self._application.get_asgi_app().state
            tracer_provider = getattr(app_state, TRACER_PROVIDER.attr, None)
            meter_provider = getattr(app_state, METER_PROVIDER.attr, None)

        for key, resource in self._builder.resources.items():
            await resource.on_startup(tracer_provider=tracer_provider, meter_provider=meter_provider)
            self._add_to_state(key=AIOHTTP_RESOURCE_PREFIX.resource_attr(key), value=resource)

    async def on_shutdown(self) -> None:
        """On shutdown."""
        for _, resource in self._builder.resources.items():
            await resource.on_shutdown()
