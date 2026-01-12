"""Provides the core application module for the Python Factory."""

from .application import ApplicationAbstract
from .builder import ApplicationGenericBuilder
from .config import (
    BaseApplicationConfig,
    RootConfig,
)
from .depends import depends_application_config
from .enums import EnvironmentEnum
from .exceptions import ConfigBuilderError, UnableToAcquireApplicationConfigError

__all__: list[str] = [
    "ApplicationAbstract",
    "ApplicationGenericBuilder",
    "BaseApplicationConfig",
    "ConfigBuilderError",
    "EnvironmentEnum",
    "RootConfig",
    "UnableToAcquireApplicationConfigError",
    "depends_application_config",
]
