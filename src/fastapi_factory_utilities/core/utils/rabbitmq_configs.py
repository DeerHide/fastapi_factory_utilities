"""Provides the configuration for the RabbitMQ."""

from typing import Annotated, Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, UrlConstraints
from pydantic_core import Url, ValidationError

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError
from fastapi_factory_utilities.core.utils.importlib import get_path_file_in_package
from fastapi_factory_utilities.core.utils.yaml_reader import (
    UnableToReadYamlFileError,
    YamlFileReader,
)


class RabbitMQCredentialsConfigError(FastAPIFactoryUtilitiesError):
    """RabbitMQ credentials config error."""


class RabbitMQCredentialsConfig(BaseModel):
    """Provides the configuration model for the Aiopika plugin.

    https://docs.aio-pika.com/#aio-pika-connect-robust-function-and-aio-pika-robustconnection-class-specific

    Possible query parameters for the AMQP URL:
        name (str url encoded) - A string that will be visible in the RabbitMQ management console
        and in the server logs, convenient for diagnostics.
        cafile (str) - Path to Certificate Authority file
        capath (str) - Path to Certificate Authority directory
        cadata (str url encoded) - URL encoded CA certificate content
        keyfile (str) - Path to client ssl private key file
        certfile (str) - Path to client ssl certificate file
        no_verify_ssl - No verify server SSL certificates. 0 by default and means False other value means True.
        heartbeat (int-like) - interval in seconds between AMQP heartbeat packets. 0 disables this feature.
        reconnect_interval (float-like) - is the period in seconds, not more often than the attempts
        to re-establish the connection will take place.
        fail_fast (true/yes/y/enable/on/enabled/1 means True, otherwise False) - special behavior
        for the start connection attempt, if it fails, all other attempts stops
        and an exception will be thrown at the connection stage. Enabled by default, if you are sure you need
        to disable this feature, be ensures for the passed URL is really working.
        Otherwise, your program will go into endless reconnection attempts that can not be successed.

    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    amqp_url: Annotated[Url, UrlConstraints(allowed_schemes=["amqp", "amqps"])] = Field(description="The AMQP URL.")


def build_rabbitmq_credentials_config(package_name: str) -> RabbitMQCredentialsConfig:
    """Build the configuration from the package.

    Args:
        package_name (str): The package name.

    Returns:
        AiopikaConfig: The Aiopika configuration.

    Raises:
        AiopikaPluginConfigError: If the configuration cannot be read or created or the configuration is invalid.
    """
    try:
        yaml_file_content: dict[str, Any] = YamlFileReader(
            file_path=get_path_file_in_package(
                filename="application.yaml",
                package=package_name,
            ),
            yaml_base_key="aiopika",
            use_environment_injection=True,
        ).read()
    except (FileNotFoundError, ImportError, UnableToReadYamlFileError) as exception:
        raise RabbitMQCredentialsConfigError(
            message="Unable to read the application configuration file for the Aiopika plugin in the package.",
            package_name=package_name,
        ) from exception

    # Create the application configuration model
    config: RabbitMQCredentialsConfig
    try:
        config = RabbitMQCredentialsConfig.model_validate(yaml_file_content)
    except ValidationError as exception:
        raise RabbitMQCredentialsConfigError(
            message="Unable to create the application configuration model for the Aiopika plugin in the package.",
            package_name=package_name,
            validation_errors=exception.errors(),
        ) from exception

    return config
