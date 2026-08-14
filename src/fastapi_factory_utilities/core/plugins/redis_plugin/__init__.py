"""Redis plugin — general-purpose async Redis client."""

# ruff: noqa: E402
# pylint: disable=wrong-import-position
from fastapi_factory_utilities.core.plugins.extras import require_extra
from fastapi_factory_utilities.core.utils.redis_configs import RedisCredentialsConfig

require_extra("redis", "redis")

from .constants import STATE_REDIS_CLIENT_KEY, STATE_REDIS_PLUGIN_KEY
from .depends import depends_redis, depends_redis_plugin
from .plugins import RedisPlugin

__all__: list[str] = [
    "STATE_REDIS_CLIENT_KEY",
    "STATE_REDIS_PLUGIN_KEY",
    "RedisCredentialsConfig",
    "RedisPlugin",
    "depends_redis",
    "depends_redis_plugin",
]
