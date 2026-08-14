"""Provides the exceptions for the OpenTelemetryPlugin."""

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError


class OpenTelemetryPluginBaseException(FastAPIFactoryUtilitiesError):  # noqa: N818
    """Base exception for the OpenTelemetryPlugin."""


class OpenTelemetryPluginConfigError(OpenTelemetryPluginBaseException):
    """Exception for the OpenTelemetryPlugin configuration."""
