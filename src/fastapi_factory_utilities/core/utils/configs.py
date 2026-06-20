"""Provides utilities to handle configurations."""

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from fastapi_factory_utilities.core.utils.importlib import get_path_file_in_package
from fastapi_factory_utilities.core.utils.yaml_reader import (
    UnableToReadYamlFileError,
    YamlFileReader,
)

GenericConfigBaseModelType = TypeVar("GenericConfigBaseModelType", bound=BaseModel)  # pylint: disable=invalid-name


class ConfigBaseException(BaseException):
    """Base exception for all the configuration exceptions."""

    pass


class UnableToReadConfigFileError(ConfigBaseException):
    """Exception raised when the configuration file cannot be read.

    Mainly used when the file is not found or the file is not a YAML file.
    """

    pass


class ValueErrorConfigError(ConfigBaseException):
    """Exception raised when the configuration object cannot be created.

    Mainly used when validation fails when creating the configuration object.
    """

    pass


def format_validation_errors(exception: ValidationError) -> str:
    """Format Pydantic validation errors into readable field-level lines.

    Args:
        exception (ValidationError): The validation error raised by Pydantic.

    Returns:
        str: One line per error, e.g. ``server.port: Input should be a valid integer``.
    """
    lines: list[str] = []
    for error in exception.errors():
        location: str = ".".join(str(part) for part in error["loc"])
        message: str = error["msg"]
        lines.append(f"{location}: {message}")
    return "\n".join(lines)


def build_config_from_file_in_package(
    package_name: str,
    filename: str,
    config_class: type[GenericConfigBaseModelType],
    yaml_base_key: str | None = None,
) -> GenericConfigBaseModelType:
    """Build a configuration object from a file in a package.

    Args:
        package_name (str): The package name.
        filename (str): The filename.
        config_class (type[GenericConfigBaseModelType]): The configuration class.
        yaml_base_key (str): The base key in the YAML file.

    Returns:
        GenericConfigBaseModelType: The configuration object.

    Raises:
        UnableToReadConfigFileError: If the configuration file cannot be read.
        ValueErrorConfigError: If the configuration file is invalid.
    """
    # Read the application configuration file
    try:
        yaml_file_content: dict[str, Any] = YamlFileReader(
            file_path=get_path_file_in_package(
                filename=filename,
                package=package_name,
            ),
            yaml_base_key=yaml_base_key,
            use_environment_injection=True,
        ).read()
    except (FileNotFoundError, ImportError, UnableToReadYamlFileError) as exception:
        raise UnableToReadConfigFileError("Unable to read the application configuration file.") from exception

    # Create the application configuration model
    try:
        config: GenericConfigBaseModelType = config_class(**yaml_file_content)
    except ValidationError as exception:
        raise ValueErrorConfigError(
            f"Invalid configuration values:\n{format_validation_errors(exception)}"
        ) from exception
    except ValueError as exception:
        raise ValueErrorConfigError(f"Unable to create the configuration model: {exception}") from exception

    return config
