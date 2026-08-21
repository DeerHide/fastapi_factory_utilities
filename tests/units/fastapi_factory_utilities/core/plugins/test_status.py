"""Tests for plugin StatusService registration helpers."""

import asyncio

import pytest
from fastapi import FastAPI

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.plugins.state import PluginNotBoundError
from fastapi_factory_utilities.core.plugins.status import PluginStatusMixin
from fastapi_factory_utilities.core.services.status.enums import (
    ComponentTypeEnum,
    HealthStatusEnum,
    ReadinessStatusEnum,
)
from fastapi_factory_utilities.core.services.status.services import StatusService


class _StatusPlugin(PluginStatusMixin, PluginAbstract):
    """Minimal plugin for mixin tests."""

    def on_load(self) -> None:
        """Unused."""

    async def on_startup(self) -> None:
        """Unused."""

    async def on_shutdown(self) -> None:
        """Unused."""


def _bound_plugin() -> tuple[_StatusPlugin, StatusService]:
    plugin: _StatusPlugin = _StatusPlugin()
    status_service: StatusService = StatusService()
    app = FastAPI()
    application = type("App", (), {})()
    application.get_asgi_app = lambda: app  # type: ignore[method-assign]
    application.get_status_service = lambda: status_service  # type: ignore[method-assign]
    plugin.set_application(application)  # type: ignore[arg-type]
    return plugin, status_service


class TestPluginStatusMixin:
    """``PluginStatusMixin`` registration and signalling."""

    def test_setup_status_before_set_application_raises(self) -> None:
        """Unbound plugin cannot register a status component."""
        plugin: _StatusPlugin = _StatusPlugin()
        with pytest.raises(PluginNotBoundError, match="set_application"):
            plugin._setup_status(component_type=ComponentTypeEnum.CACHE, identifier="Redis")

    def test_report_healthy_and_unhealthy(self) -> None:
        """Healthy then unhealthy updates StatusService."""
        plugin, status_service = _bound_plugin()
        plugin._setup_status(component_type=ComponentTypeEnum.CACHE, identifier="Redis")
        plugin._report_healthy()
        statuses = list(status_service.get_components_status_by_type()[ComponentTypeEnum.CACHE].values())
        assert statuses[0]["health"] == HealthStatusEnum.HEALTHY
        assert statuses[0]["readiness"] == ReadinessStatusEnum.READY
        plugin._report_unhealthy()
        statuses = list(status_service.get_components_status_by_type()[ComponentTypeEnum.CACHE].values())
        assert statuses[0]["health"] == HealthStatusEnum.UNHEALTHY
        assert statuses[0]["readiness"] == ReadinessStatusEnum.NOT_READY

    async def test_arm_unhealthy_is_cancelled_on_recover(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A reconnect before the grace period does not flap readiness."""
        monkeypatch.setattr(_StatusPlugin, "DISCONNECT_GRACE_S", 0.05)
        plugin, status_service = _bound_plugin()
        plugin._setup_status(component_type=ComponentTypeEnum.MESSAGE_BROKER, identifier="RabbitMQ")
        plugin._report_healthy()
        plugin._arm_unhealthy()
        plugin._report_healthy()
        await asyncio.sleep(0.08)
        statuses = list(status_service.get_components_status_by_type()[ComponentTypeEnum.MESSAGE_BROKER].values())
        assert statuses[0]["readiness"] == ReadinessStatusEnum.READY

    async def test_arm_unhealthy_fires_after_grace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Sustained disconnect marks not-ready after the grace period."""
        monkeypatch.setattr(_StatusPlugin, "DISCONNECT_GRACE_S", 0.05)
        plugin, status_service = _bound_plugin()
        plugin._setup_status(component_type=ComponentTypeEnum.MESSAGE_BROKER, identifier="RabbitMQ")
        plugin._report_healthy()
        plugin._arm_unhealthy()
        await asyncio.sleep(0.08)
        statuses = list(status_service.get_components_status_by_type()[ComponentTypeEnum.MESSAGE_BROKER].values())
        assert statuses[0]["readiness"] == ReadinessStatusEnum.NOT_READY
