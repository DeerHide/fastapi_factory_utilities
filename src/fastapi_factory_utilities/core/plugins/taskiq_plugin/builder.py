"""Config resolution for the Taskiq plugin."""

from fastapi_factory_utilities.core.plugins.redis_plugin.builder import build_redis_credentials_config
from fastapi_factory_utilities.core.plugins.redis_plugin.configs import RedisCredentialsConfig
from fastapi_factory_utilities.core.plugins.redis_plugin.exceptions import RedisPluginConfigError
from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol

from .exceptions import TaskiqPluginConfigError


def build_taskiq_redis_config(application: ApplicationAbstractProtocol) -> RedisCredentialsConfig:
    """Build Redis credentials for Taskiq from the application's ``redis:`` YAML section.

    Args:
        application: The application whose package holds ``application.yaml``.

    Returns:
        Validated Redis credentials.

    Raises:
        TaskiqPluginConfigError: If Redis credentials cannot be built.
    """
    try:
        return build_redis_credentials_config(application=application)
    except RedisPluginConfigError as exception:
        raise TaskiqPluginConfigError("Unable to build the Redis credentials configuration.") from exception
