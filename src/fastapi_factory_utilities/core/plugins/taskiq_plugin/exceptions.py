"""Provides the exceptions for the Taskiq plugin."""

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError


class TaskiqPluginBaseError(FastAPIFactoryUtilitiesError):
    """Base class for all exceptions raised by the Taskiq plugin."""


class TaskiqPluginConfigError(TaskiqPluginBaseError):
    """Exception for the Taskiq plugin configuration."""
