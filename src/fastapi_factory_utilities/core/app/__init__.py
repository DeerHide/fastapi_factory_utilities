"""Provides the core application module for the Python Factory."""

from .application import ApplicationAbstract
from .builder import ApplicationGenericBuilder
from .config import (
    AppCsrfConfig,
    BaseApplicationConfig,
    RootConfig,
)
from .depends import (
    DependsApplicationConfig,
    DependsRootConfig,
    depends_application_config,
    depends_csrf_config,
    depends_root_config,
)
from .enums import EnvironmentEnum
from .exceptions import ConfigBuilderError, UnableToAcquireApplicationConfigError

__all__: list[str] = [
    "AppCsrfConfig",
    "ApplicationAbstract",
    "ApplicationGenericBuilder",
    "BaseApplicationConfig",
    "ConfigBuilderError",
    "DependsApplicationConfig",
    "DependsRootConfig",
    "EnvironmentEnum",
    "RootConfig",
    "UnableToAcquireApplicationConfigError",
    "depends_application_config",
    "depends_csrf_config",
    "depends_root_config",
]
