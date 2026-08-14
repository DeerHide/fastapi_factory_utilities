"""Tests for the plugin application-state registry."""

from pathlib import Path

import pytest
from fastapi import FastAPI

from fastapi_factory_utilities.core.plugins import state as state_mod
from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.plugins.odm_plugin.depends import depends_odm_client, depends_odm_database
from fastapi_factory_utilities.core.plugins.state import (
    ALL_KEYS,
    ODM_CLIENT,
    PluginNotBoundError,
    PluginNotRegisteredError,
    StateKey,
)


class _UnboundPlugin(PluginAbstract):
    """Minimal plugin for unbound-state tests."""

    def on_load(self) -> None:
        """Unused."""

    async def on_startup(self) -> None:
        """Unused."""

    async def on_shutdown(self) -> None:
        """Unused."""


class _BareRequest:
    """Request stand-in with an empty FastAPI app."""

    def __init__(self) -> None:
        """Bind an app with no plugin state."""
        self.app: FastAPI = FastAPI()


class TestPluginNotBound:
    """``_add_to_state`` before ``set_application``."""

    def test_add_to_state_before_set_application_raises(self) -> None:
        """A plugin used before set_application raises PluginNotBoundError."""
        plugin: _UnboundPlugin = _UnboundPlugin()
        with pytest.raises(PluginNotBoundError, match="set_application"):
            plugin._add_to_state(key=ODM_CLIENT, value=object())  # pylint: disable=protected-access


class TestPluginNotRegistered:
    """depends_* accessors when the plugin was never registered."""

    def test_depends_odm_client_names_missing_plugin(self) -> None:
        """Missing ODM client is PluginNotRegisteredError, not AttributeError."""
        with pytest.raises(PluginNotRegisteredError, match="ODMPlugin"):
            depends_odm_client(_BareRequest())  # type: ignore[arg-type]

    def test_depends_odm_database_names_missing_plugin(self) -> None:
        """Missing ODM database names ODMPlugin."""
        with pytest.raises(PluginNotRegisteredError, match="ODMPlugin"):
            depends_odm_database(_BareRequest())  # type: ignore[arg-type]


class TestRegistryDrift:
    """Every registry key is written by a plugin and read by an accessor."""

    def test_every_registry_key_is_written_and_read(self) -> None:
        """Each StateKey constant appears in a plugin module and a depends module."""
        plugins_root: Path = Path(state_mod.__file__).resolve().parent
        writers: str = "\n".join(
            path.read_text(encoding="utf-8")
            for path in plugins_root.rglob("*.py")
            if path.name in {"plugins.py", "plugin.py"}
        )
        readers: str = "\n".join(path.read_text(encoding="utf-8") for path in plugins_root.rglob("depends.py"))
        named: dict[str, StateKey] = {
            name: value for name, value in vars(state_mod).items() if isinstance(value, StateKey)
        }
        assert set(named.values()) == set(ALL_KEYS)
        for name in named:
            assert name in writers, f"{name} is never written by a plugin"
            assert name in readers, f"{name} is never read by a depends accessor"
