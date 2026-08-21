"""Tests for PluginAbstract shared helpers."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.plugins.state import ODM_CLIENT


class _WarmPlugin(PluginAbstract):
    """Minimal plugin for exercising ``_warm_soft``."""

    def on_load(self) -> None:
        """No-op."""

    async def on_startup(self) -> None:
        """No-op."""

    async def on_shutdown(self) -> None:
        """No-op."""


class TestPluginWarmSoft:
    """Tests for ``PluginAbstract._warm_soft``."""

    @pytest.mark.asyncio
    async def test_warm_soft_awaits_probe(self) -> None:
        """Startup probe is awaited."""
        plugin: _WarmPlugin = _WarmPlugin()
        probe: AsyncMock = AsyncMock(return_value={"ok": 1})

        await plugin._warm_soft(probe, what="MongoDB connection")

        probe.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_warm_soft_swallows_failures(self) -> None:
        """Probe failures are logged but do not abort startup."""
        plugin: _WarmPlugin = _WarmPlugin()
        probe: AsyncMock = AsyncMock(side_effect=ConnectionError("unavailable"))

        await plugin._warm_soft(probe, what="S3 connection")

        probe.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_warm_soft_swallows_timeout(self) -> None:
        """Probe timeout is logged but does not abort startup."""

        async def slow() -> dict[str, int]:
            await asyncio.sleep(10)
            return {"ok": 1}

        plugin: _WarmPlugin = _WarmPlugin()
        await plugin._warm_soft(lambda: asyncio.wait_for(slow(), timeout=0.01), what="MongoDB connection")


class TestPluginAddToState:
    """Tests for ``PluginAbstract._add_to_state``."""

    def test_add_to_state_writes_registry_key(self) -> None:
        """A StateKey is published on the ASGI app state."""
        plugin: _WarmPlugin = _WarmPlugin()
        app = FastAPI()
        application = MagicMock()
        application.get_asgi_app.return_value = app
        plugin.set_application(application)
        plugin._add_to_state(key=ODM_CLIENT, value="client")

        assert getattr(app.state, ODM_CLIENT.attr) == "client"

    def test_add_to_state_writes_string_key(self) -> None:
        """A raw string key is published on the ASGI app state."""
        plugin: _WarmPlugin = _WarmPlugin()
        app = FastAPI()
        application = MagicMock()
        application.get_asgi_app.return_value = app
        plugin.set_application(application)
        plugin._add_to_state(key="custom_key", value=1)

        assert app.state.custom_key == 1
