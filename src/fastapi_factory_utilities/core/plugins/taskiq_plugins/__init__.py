"""Taskiq Plugin Module."""

from importlib.util import find_spec

from .depends import depends_scheduler_component
from .exceptions import TaskiqPluginBaseError
from .plugin import TaskiqPlugin
from .schedulers import SchedulerComponent

__all__: list[str] = [
    "SchedulerComponent",
    "TaskiqPlugin",
    "TaskiqPluginBaseError",
    "depends_scheduler_component",
]

if find_spec("beanie") is not None:
    from .depends import depends_odm_database

    __all__ += [
        "depends_odm_database",
    ]

if find_spec("aio-pika") is not None:
    from .depends import depends_aiopike_robust_connection

    __all__ += [
        "depends_aiopike_robust_connection",
    ]
