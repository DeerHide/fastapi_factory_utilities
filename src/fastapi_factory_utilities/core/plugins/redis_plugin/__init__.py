"""Redis plugin — general-purpose async Redis client."""

from fastapi_factory_utilities.core.utils.redis_configs import RedisCredentialsConfig

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
