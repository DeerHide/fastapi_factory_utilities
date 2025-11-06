"""Provides the exceptions for the Taskiq plugin."""

from typing import Any

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError


class TaskiqPluginBaseError(FastAPIFactoryUtilitiesError):
    """Base class for all exceptions raised by the Taskiq plugin."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        """Initialize the Taskiq plugin base exception."""
        super().__init__(message, **kwargs)
