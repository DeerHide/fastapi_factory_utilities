"""Provides the exceptions for the Aiohttp plugin."""

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError


class AioHttpClientError(FastAPIFactoryUtilitiesError):
    """Exception for the Aiohttp client."""


class UnableToReadHttpDependencyConfigError(AioHttpClientError):
    """Exception for the unable to read the HTTP dependency config."""


class AioHttpClientResourceNotFoundError(AioHttpClientError):
    """Exception for the Aiohttp resource not found in the application state."""
