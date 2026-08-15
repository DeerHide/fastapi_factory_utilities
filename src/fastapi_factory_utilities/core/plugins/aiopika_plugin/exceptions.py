"""Provides the exceptions for the Aiopika plugin."""

from typing import Any

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError


class AiopikaPluginBaseError(FastAPIFactoryUtilitiesError):
    """Base class for all exceptions raised by the Aiopika plugin."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        """Initialize the Aiopika plugin base exception."""
        super().__init__(message, **kwargs)


class AiopikaPluginConfigError(AiopikaPluginBaseError):
    """Exception for the Aiopika plugin configuration."""


class AiopikaPluginConnectionNotProvidedError(AiopikaPluginBaseError):
    """Exception for the Aiopika plugin connection not provided."""


class AiopikaPluginExchangeNotDeclaredError(AiopikaPluginBaseError):
    """Exception for the Aiopika plugin exchange not declared."""


class AiopikaPluginQueueNotDeclaredError(AiopikaPluginBaseError):
    """Exception for the Aiopika plugin queue not declared."""
