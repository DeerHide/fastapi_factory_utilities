"""Provides FastAPI / Taskiq dependencies for the Redis plugin."""

from typing import TYPE_CHECKING

from fastapi import Request
from taskiq import TaskiqDepends

from fastapi_factory_utilities.core.plugins.state import REDIS_CLIENT, REDIS_PLUGIN, get_from_state

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from .plugins import RedisPlugin


def depends_redis(request: Request = TaskiqDepends()) -> "Redis":
    """Acquire the async Redis client from application state.

    Works for HTTP routes and Taskiq workers (via ``TaskiqDepends``).

    Args:
        request: The incoming request (or Taskiq-bridged request).

    Returns:
        The shared ``redis.asyncio.Redis`` client.

    Raises:
        PluginNotRegisteredError: If no ``RedisPlugin`` was registered.
    """
    return get_from_state(request.app.state, REDIS_CLIENT)


def depends_redis_plugin(request: Request = TaskiqDepends()) -> "RedisPlugin":
    """Acquire the Redis plugin (client + ``build_key``) from application state.

    Args:
        request: The incoming request (or Taskiq-bridged request).

    Returns:
        The started ``RedisPlugin`` instance.

    Raises:
        PluginNotRegisteredError: If no ``RedisPlugin`` was registered.
    """
    return get_from_state(request.app.state, REDIS_PLUGIN)
