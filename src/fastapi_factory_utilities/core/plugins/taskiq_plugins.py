"""Deprecated alias of ``taskiq_plugin``. Removed in 7.0.0."""

from __future__ import annotations

import importlib
import warnings
from typing import Any

_NEW = "fastapi_factory_utilities.core.plugins.taskiq_plugin"


def __getattr__(name: str) -> Any:  # pylint: disable=invalid-name
    """Re-export public names and submodules from ``taskiq_plugin``."""
    warnings.warn(
        f"fastapi_factory_utilities.core.plugins.taskiq_plugins is renamed to {_NEW} and will be removed in 7.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    module = importlib.import_module(_NEW)
    if name == "__all__":
        return list(module.__all__)
    return getattr(module, name)
