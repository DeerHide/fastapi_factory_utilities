"""Provides the dependencies for the Aiopika plugin."""

from aio_pika.abc import AbstractRobustConnection
from fastapi import Request
from taskiq import TaskiqDepends

from fastapi_factory_utilities.core.plugins.state import AIOPIKA_CONNECTION, get_from_state

DEPENDS_AIOPIKA_ROBUST_CONNECTION_KEY: str = AIOPIKA_CONNECTION.attr


def depends_aiopika_robust_connection(
    request: Request = TaskiqDepends(),
) -> AbstractRobustConnection:
    """Get the Aiopika robust connection.

    Raises:
        PluginNotRegisteredError: If no ``AiopikaPlugin`` was registered.
    """
    return get_from_state(request.app.state, AIOPIKA_CONNECTION)
