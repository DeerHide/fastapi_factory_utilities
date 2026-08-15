"""Aiohttp client plugin.

Readiness is opt-in per HTTP dependency via ``affects_readiness`` on
``HttpServiceDependencyConfig`` (default false). A degraded third-party API
must not fail the pod unless the service explicitly says that dependency is
on the critical path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.plugins.state import (
    AIOHTTP_RESOURCE_PREFIX,
    METER_PROVIDER,
    TRACER_PROVIDER,
)
from fastapi_factory_utilities.core.plugins.status import register_status_component, report_status
from fastapi_factory_utilities.core.services.status.enums import ComponentTypeEnum

from .builder import AioHttpClientBuilder

if TYPE_CHECKING:
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.trace import TracerProvider
    from reactivex import Subject

    from fastapi_factory_utilities.core.services.status.types import Status


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
            subject: Subject[Status] | None = None
            config = self._builder.configs.get(key)
            if self._application is not None and config is not None and config.affects_readiness is True:
                subject = register_status_component(
                    self._application,
                    component_type=ComponentTypeEnum.SERVICE,
                    identifier=key,
                )
            try:
                await resource.on_startup(tracer_provider=tracer_provider, meter_provider=meter_provider)
            except Exception:
                if subject is not None:
                    report_status(subject, healthy=False)
                raise
            if subject is not None:
                report_status(subject, healthy=True)
            self._add_to_state(key=AIOHTTP_RESOURCE_PREFIX.resource_attr(key), value=resource)

    async def on_shutdown(self) -> None:
        """On shutdown."""
        for _, resource in self._builder.resources.items():
            await resource.on_shutdown()
