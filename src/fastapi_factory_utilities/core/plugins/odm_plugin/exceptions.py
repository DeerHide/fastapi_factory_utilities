"""Provides the exceptions for the ODM_Plugin."""

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError


class ODMPluginBaseException(FastAPIFactoryUtilitiesError):  # noqa: N818
    """Base exception for the ODM_Plugin."""


class ODMPluginConfigError(ODMPluginBaseException):
    """Exception for the ODM_Plugin configuration."""


class UnableToCreateEntityDueToDuplicateKeyError(ODMPluginBaseException):
    """Exception for when the entity cannot be created due to a duplicate key error."""


class OperationError(ODMPluginBaseException):
    """Exception for when an operation fails."""


class VaultUnwrapError(ODMPluginConfigError):
    """Exception for when the CSFLE master key cannot be unwrapped from Vault."""


class EncryptedFieldIndexCollisionError(ODMPluginConfigError):
    """Exception for when a declared encrypted field is also indexed."""
