"""Deprecated plugin package aliases keep the 5.x import paths working."""

import importlib
import sys

import pytest


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("fastapi_factory_utilities.core.plugins.aiohttp", "aiohttp_plugin"),
        ("fastapi_factory_utilities.core.plugins.aiopika", "aiopika_plugin"),
        ("fastapi_factory_utilities.core.plugins.taskiq_plugins", "taskiq_plugin"),
    ],
)
def test_old_plugin_package_path_warns(old: str, new: str) -> None:
    """Importing the pre-rename package emits a DeprecationWarning naming the replacement."""
    sys.modules.pop(old, None)
    with pytest.warns(DeprecationWarning, match=new):
        getattr(importlib.import_module(old), "__all__")


def test_aiohttp_alias_exposes_depends_submodule() -> None:
    """``from ...aiohttp import depends`` still resolves after the rename."""
    sys.modules.pop("fastapi_factory_utilities.core.plugins.aiohttp", None)
    canonical = importlib.import_module("fastapi_factory_utilities.core.plugins.aiohttp_plugin.depends")
    with pytest.warns(DeprecationWarning, match="aiohttp_plugin"):
        aiohttp_pkg = importlib.import_module("fastapi_factory_utilities.core.plugins.aiohttp")
        assert aiohttp_pkg.depends.AioHttpResourceDepends is canonical.AioHttpResourceDepends
