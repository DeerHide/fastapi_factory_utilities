"""Provides the dependencies for the application."""

from fastapi import Request

from .config import BaseApplicationConfig, RootConfig
from .exceptions import UnableToAcquireApplicationConfigError


def depends_application_config(request: Request) -> BaseApplicationConfig:
    """Get the application config.

    Args:
        request (Request): The request.

    Returns:
        BaseApplicationConfig: The application config.

    Raises:
        UnableToAcquireApplicationConfigError: If the application config is not found.
    """
    if not hasattr(request.app.state, "config"):
        raise UnableToAcquireApplicationConfigError("Unable to acquire the application config.")
    root_config: RootConfig = request.app.state.config
    return root_config.application
