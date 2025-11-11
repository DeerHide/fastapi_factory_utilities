"""Provides utilities to handle Redis Configuration."""

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, ValidationError

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError
from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol
from fastapi_factory_utilities.core.utils.importlib import get_path_file_in_package
from fastapi_factory_utilities.core.utils.yaml_reader import UnableToReadYamlFileError, YamlFileReader


class RedisCredentialsConfigError(FastAPIFactoryUtilitiesError):
    """Redis credentials config error."""


class RedisCredentialsConfig(BaseModel):
    """Redis credentials config."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
    url: str


def build_redis_credentials_config(application: "ApplicationAbstractProtocol") -> RedisCredentialsConfig:
    """Build the Redis credentials configuration.

    Args:
        application: The application.

    Returns:
        RedisCredentialsConfig: The Redis credentials configuration.

    Raises:
        TaskiqPluginConfigError: for any error occurred while building the Redis credentials configuration.
    """
    if application.PACKAGE_NAME == "":
        raise RedisCredentialsConfigError("The package name must be set in the concrete application class.")

    try:
        yaml_file_content: dict[str, Any] = YamlFileReader(
            file_path=get_path_file_in_package(
                filename="application.yaml",
                package=application.PACKAGE_NAME,
            ),
            yaml_base_key="redis",
            use_environment_injection=True,
        ).read()
    except (FileNotFoundError, ImportError, UnableToReadYamlFileError) as exception:
        raise RedisCredentialsConfigError("Unable to read the application configuration file.") from exception

    try:
        config: RedisCredentialsConfig = RedisCredentialsConfig.model_validate(yaml_file_content)
    except ValidationError as exception:
        raise RedisCredentialsConfigError("Unable to create the application configuration model.") from exception
    return config
