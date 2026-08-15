"""Provides the dependencies for the Taskiq plugin."""

from importlib.util import find_spec
from typing import TYPE_CHECKING

from fastapi import Request
from taskiq import TaskiqDepends

from fastapi_factory_utilities.core.plugins.state import SCHEDULER_COMPONENT, get_from_state

if TYPE_CHECKING:
    from .schedulers import SchedulerComponent

__all__: list[str] = [
    "DEPENDS_SCHEDULER_COMPONENT_KEY",
    "depends_scheduler_component",
]

DEPENDS_SCHEDULER_COMPONENT_KEY: str = SCHEDULER_COMPONENT.attr


def depends_scheduler_component(
    request: Request = TaskiqDepends(),
) -> "SchedulerComponent":
    """Dependency injection for the scheduler component.

    Raises:
        PluginNotRegisteredError: If no ``TaskiqPlugin`` was registered.
    """
    return get_from_state(request.app.state, SCHEDULER_COMPONENT)


if find_spec("beanie") is not None:
    from fastapi_factory_utilities.core.plugins.odm_plugin.depends import (  # noqa: F401  # pylint: disable=unused-import
        depends_odm_database,
    )

    __all__.append("depends_odm_database")

if find_spec("aio_pika") is not None:
    from fastapi_factory_utilities.core.plugins.aiopika_plugin.depends import (  # noqa: F401  # pylint: disable=unused-import
        depends_aiopika_robust_connection,
    )

    __all__.append("depends_aiopika_robust_connection")
