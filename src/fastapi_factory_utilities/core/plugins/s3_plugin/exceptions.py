"""Provides the exceptions for the S3 plugin."""

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError


class S3PluginBaseException(FastAPIFactoryUtilitiesError):
    """Base exception for the S3 plugin."""


class S3PluginConfigError(S3PluginBaseException):
    """Exception for S3 plugin configuration failures."""


class S3BucketResourceNotFoundError(S3PluginBaseException):
    """Exception when an S3 bucket resource is missing from application state."""


class S3BucketNotFoundError(S3PluginBaseException):
    """Exception when a configured bucket does not exist on the S3 endpoint."""
