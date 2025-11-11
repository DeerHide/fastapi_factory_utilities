"""Taskiq Plugin Module."""

from importlib.util import find_spec

from .depends import depends_scheduler_component
from .exceptions import TaskiqPluginBaseError, TaskiqPluginConfigError
from .plugin import TaskiqPlugin
from .schedulers import SchedulerComponent

__all__: list[str] = [  # pylint: disable=invalid-name
    "SchedulerComponent",
    "TaskiqPlugin",
    "TaskiqPluginBaseError",
    "TaskiqPluginConfigError",
    "depends_scheduler_component",
]

if find_spec("beanie") is not None:
    from .depends import depends_odm_database

    __all__ += [  # pylint: disable=invalid-name
        "depends_odm_database",
    ]

if find_spec("aio_pika") is not None:
    from .depends import depends_aiopika_robust_connection

    __all__ += [  # pylint: disable=invalid-name
        "depends_aiopika_robust_connection",
    ]
