"""Backward-compatible aliases for Redis plugin state keys."""

from fastapi_factory_utilities.core.plugins.state import REDIS_CLIENT, REDIS_PLUGIN

STATE_REDIS_CLIENT_KEY: str = REDIS_CLIENT.attr
STATE_REDIS_PLUGIN_KEY: str = REDIS_PLUGIN.attr
