"""Provides FastAPI / Taskiq dependencies for the Redis plugin."""

from typing import TYPE_CHECKING

from fastapi import Request
from taskiq import TaskiqDepends

from .constants import STATE_REDIS_CLIENT_KEY, STATE_REDIS_PLUGIN_KEY

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
    """
    return getattr(request.app.state, STATE_REDIS_CLIENT_KEY)


def depends_redis_plugin(request: Request = TaskiqDepends()) -> "RedisPlugin":
    """Acquire the Redis plugin (client + ``build_key``) from application state.

    Args:
        request: The incoming request (or Taskiq-bridged request).

    Returns:
        The started ``RedisPlugin`` instance.
    """
    return getattr(request.app.state, STATE_REDIS_PLUGIN_KEY)
