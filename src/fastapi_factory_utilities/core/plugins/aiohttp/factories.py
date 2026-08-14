"""Aiohttp client factory."""

from fastapi_factory_utilities.core.plugins.aiohttp.configs import HttpServiceDependencyConfig
from fastapi_factory_utilities.core.utils.configs import build_config_from_file_in_package

from .exceptions import UnableToReadHttpDependencyConfigError

DEFAULT_APPLICATION_YAML_PATH: str = "application.yaml"
DEFAULT_YAML_BASE_KEY: str = "dependencies.http"


def build_http_dependency_config(key: str, application_package: str) -> HttpServiceDependencyConfig:
    """Build the HTTP dependency config.

    Args:
        key: The key of the HTTP dependency config.
        application_package: The package name of the application.

    Returns:
        HttpServiceDependencyConfig: The HTTP dependency config.
    """
    key_path: str = f"{DEFAULT_YAML_BASE_KEY}.{key}"
    return build_config_from_file_in_package(
        package_name=application_package,
        filename=DEFAULT_APPLICATION_YAML_PATH,
        config_class=HttpServiceDependencyConfig,
        yaml_base_key=key_path,
        error_type=UnableToReadHttpDependencyConfigError,
    )
