"""Provides the exceptions for the application factory."""

from ..exceptions import FastAPIFactoryUtilitiesError


class BaseApplicationException(BaseException):
    """Base application exception."""

    pass


class UnableToAcquireApplicationConfigError(FastAPIFactoryUtilitiesError):
    """An Error occur when trying to acquire the application config."""


class ConfigBuilderError(FastAPIFactoryUtilitiesError):
    """Application configuration factory exception."""

    def __init__(self, message: str, config_class: type, package: str, filename: str) -> None:
        """Instantiate the exception."""
        super().__init__(
            message=f"Unable to build the configuration for the package {package} and "
            + f"the file {filename} with the class {config_class} - {message}"
        )
