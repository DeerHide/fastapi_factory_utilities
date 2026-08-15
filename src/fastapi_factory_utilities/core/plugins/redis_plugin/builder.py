"""Config resolution for the Redis plugin."""

from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol
from fastapi_factory_utilities.core.utils.configs import build_config_from_file_in_package

from .configs import RedisCredentialsConfig
from .exceptions import RedisPluginConfigError


def build_redis_credentials_config(application: ApplicationAbstractProtocol) -> RedisCredentialsConfig:
    """Build Redis credentials from the application's ``redis:`` YAML section.

    Args:
        application: The application whose package holds ``application.yaml``.

    Returns:
        Validated Redis credentials.
    """
    return build_config_from_file_in_package(
        package_name=application.PACKAGE_NAME,
        filename="application.yaml",
        config_class=RedisCredentialsConfig,
        yaml_base_key="redis",
        error_type=RedisPluginConfigError,
    )
