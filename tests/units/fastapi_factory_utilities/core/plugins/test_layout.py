"""Assert every plugin package matches the canonical layout."""

import importlib
from pathlib import Path

import fastapi_factory_utilities.core.plugins as plugins_pkg

_PLUGINS_ROOT: Path = Path(plugins_pkg.__file__).resolve().parent
_CANONICAL: tuple[str, ...] = (
    "__init__.py",
    "plugins.py",
    "configs.py",
    "builder.py",
    "depends.py",
    "exceptions.py",
)


def _plugin_packages() -> list[Path]:
    """Return ``*_plugin`` directories under ``core/plugins``."""
    return sorted(path for path in _PLUGINS_ROOT.iterdir() if path.is_dir() and path.name.endswith("_plugin"))


def test_every_plugin_package_has_canonical_files() -> None:
    """Each plugin package contains the six canonical modules."""
    packages: list[Path] = _plugin_packages()
    assert packages, "no *_plugin packages found"
    missing: dict[str, list[str]] = {}
    for package in packages:
        absent: list[str] = [name for name in _CANONICAL if not (package / name).is_file()]
        if absent:
            missing[package.name] = absent
    assert not missing, missing


def test_every_plugin_all_exports_contract() -> None:
    """``__all__`` re-exports the plugin class, config, depends, and exception base."""
    for package in _plugin_packages():
        module = importlib.import_module(f"fastapi_factory_utilities.core.plugins.{package.name}")
        names: set[str] = set(module.__all__)
        assert any(name.endswith("Plugin") for name in names), package.name
        assert any("Config" in name for name in names), package.name
        assert any(name.startswith("depends_") or name.endswith("Depends") for name in names), package.name
        assert any(name.endswith("Error") or name.endswith("Exception") for name in names), package.name
