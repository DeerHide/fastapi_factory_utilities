"""Exceptions for the Redis plugin."""

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError


class RedisPluginBaseError(FastAPIFactoryUtilitiesError):
    """Base exception for the Redis plugin."""


class RedisPluginConfigError(RedisPluginBaseError):
    """Raised when Redis credentials cannot be loaded or validated."""


class RedisPluginNotStartedError(RedisPluginBaseError):
    """Raised when the Redis client is accessed before ``on_startup``."""
