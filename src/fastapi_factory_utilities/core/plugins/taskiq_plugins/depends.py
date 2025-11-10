"""Provides the dependencies for the Taskiq plugin."""

from importlib.util import find_spec
from typing import TYPE_CHECKING, Any

from fastapi import Request
from taskiq import TaskiqDepends

if TYPE_CHECKING:
    from .schedulers import SchedulerComponent

DEPENDS_SCHEDULER_COMPONENT_KEY: str = "scheduler_component"


def depends_scheduler_component(
    request: Request = TaskiqDepends(),
) -> "SchedulerComponent":
    """Dependency injection for the scheduler component."""
    return getattr(request.app.state, DEPENDS_SCHEDULER_COMPONENT_KEY)


if find_spec("beanie") is not None:
    from pymongo.asynchronous.database import AsyncDatabase

    def depends_odm_database(request: Request = TaskiqDepends()) -> AsyncDatabase[Any]:
        """Acquire the ODM database from the request.

        Args:
            request (Request): The request.

        Returns:
            AsyncDatabase: The ODM database.
        """
        return request.app.state.odm_database


if find_spec("aio_pika") is not None:
    from aio_pika.abc import AbstractRobustConnection

    from fastapi_factory_utilities.core.plugins.aiopika.depends import DEPENDS_AIOPIKA_ROBUST_CONNECTION_KEY

    def depends_aiopika_robust_connection(request: Request = TaskiqDepends()) -> AbstractRobustConnection:
        """Acquire the Aiopika robust connection from the request.

        Args:
            request (Request): The request.

        Returns:
            AbstractRobustConnection: The Aiopika robust connection.
        """
        return getattr(request.app.state, DEPENDS_AIOPIKA_ROBUST_CONNECTION_KEY)
