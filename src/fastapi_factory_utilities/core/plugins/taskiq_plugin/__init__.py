"""Taskiq Plugin Module."""

# ruff: noqa: E402
# pylint: disable=wrong-import-position
from importlib.util import find_spec

from fastapi_factory_utilities.core.plugins.extras import require_extra

require_extra("taskiq", "taskiq_redis")

from .configs import RedisCredentialsConfig
from .depends import depends_scheduler_component
from .exceptions import TaskiqPluginBaseError, TaskiqPluginConfigError
from .plugins import TaskiqPlugin
from .schedulers import SchedulerComponent

__all__: list[str] = [  # pylint: disable=invalid-name
    "RedisCredentialsConfig",
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
