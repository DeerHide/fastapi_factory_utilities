"""Aiohttp client factory."""

from typing import Any

from fastapi_factory_utilities.core.plugins.aiohttp.configs import HttpServiceDependencyConfig
from fastapi_factory_utilities.core.utils.importlib import get_path_file_in_package
from fastapi_factory_utilities.core.utils.yaml_reader import UnableToReadYamlFileError, YamlFileReader

from .exceptions import UnableToReadHttpDependencyConfigError

DEFAULT_APPLICATION_YAML_PATH: str = "application.yaml"
DEFAULT_YAML_BASE_KEY: str = "dependencies.http"


def build_http_dependency_config(key: str, application_package: str) -> HttpServiceDependencyConfig:
    """Build the HTTP dependency config.

    Args:
        key (str): The key of the HTTP dependency config.
        application_package (str): The package name of the application.

    Returns:
        HttpServiceDependencyConfig: The HTTP dependency config.
    """
    key_path: str = f"{DEFAULT_YAML_BASE_KEY}.{key}"
    try:
        yaml_reader: YamlFileReader = YamlFileReader(
            file_path=get_path_file_in_package(
                filename=DEFAULT_APPLICATION_YAML_PATH,
                package=application_package,
            ),
            yaml_base_key=key_path,
        )
    except (FileNotFoundError, ImportError, UnableToReadYamlFileError) as exception:
        raise UnableToReadHttpDependencyConfigError(
            "Unable to read the HTTP dependency config", key_path=key_path, file_path=DEFAULT_APPLICATION_YAML_PATH
        ) from exception
    try:
        yaml_data: dict[str, Any] = yaml_reader.read()
    except ValueError as exception:
        raise UnableToReadHttpDependencyConfigError(
            "Unable to read the HTTP dependency config", key_path=key_path, file_path=DEFAULT_APPLICATION_YAML_PATH
        ) from exception
    return HttpServiceDependencyConfig(**yaml_data)
