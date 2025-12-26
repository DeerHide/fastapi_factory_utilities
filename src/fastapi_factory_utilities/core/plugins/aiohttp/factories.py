"""Aiohttp client factory."""

from pathlib import Path
from typing import Any

from fastapi_factory_utilities.core.plugins.aiohttp.configs import HttpServiceDependencyConfig
from fastapi_factory_utilities.core.utils.yaml_reader import UnableToReadYamlFileError, YamlFileReader

from .exceptions import UnableToReadHttpDependencyConfigError

BASE_YAML_PATH: Path = Path("application.yaml")
DEFAULT_YAML_BASE_KEY: str = "dependencies.http"


def build_http_dependency_config(key: str) -> HttpServiceDependencyConfig:
    """Build the HTTP dependency config.

    Args:
        key (str): The key of the HTTP dependency config.

    Returns:
        HttpServiceDependencyConfig: The HTTP dependency config.
    """
    key_path: str = f"{DEFAULT_YAML_BASE_KEY}.{key}"
    try:
        yaml_reader: YamlFileReader = YamlFileReader(file_path=BASE_YAML_PATH, yaml_base_key=key_path)
    except (FileNotFoundError, ImportError, UnableToReadYamlFileError) as exception:
        raise UnableToReadHttpDependencyConfigError(
            "Unable to read the HTTP dependency config", key_path=key_path, file_path=BASE_YAML_PATH
        ) from exception
    try:
        yaml_data: dict[str, Any] = yaml_reader.read()
    except ValueError as exception:
        raise UnableToReadHttpDependencyConfigError(
            "Unable to read the HTTP dependency config", key_path=key_path, file_path=BASE_YAML_PATH
        ) from exception
    return HttpServiceDependencyConfig(**yaml_data)
