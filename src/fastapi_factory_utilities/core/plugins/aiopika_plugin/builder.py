"""Config resolution for the Aiopika plugin."""

from fastapi_factory_utilities.core.utils.configs import build_config_from_file_in_package

from .configs import RabbitMQCredentialsConfig
from .exceptions import AiopikaPluginConfigError


def build_rabbitmq_credentials_config(package_name: str) -> RabbitMQCredentialsConfig:
    """Build AMQP credentials from the application's ``aiopika:`` YAML section.

    Args:
        package_name: Application package that contains ``application.yaml``.

    Returns:
        Validated RabbitMQ credentials.
    """
    return build_config_from_file_in_package(
        package_name=package_name,
        filename="application.yaml",
        config_class=RabbitMQCredentialsConfig,
        yaml_base_key="aiopika",
        error_type=AiopikaPluginConfigError,
    )
