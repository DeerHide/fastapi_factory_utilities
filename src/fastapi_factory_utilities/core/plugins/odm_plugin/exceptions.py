"""Provides the exceptions for the ODM_Plugin."""


class ODMPluginBaseException(Exception):  # noqa: N818
    """Base exception for the ODM_Plugin."""

    pass


class ODMPluginConfigError(ODMPluginBaseException):
    """Exception for the ODM_Plugin configuration."""

    pass


class UnableToCreateEntityDueToDuplicateKeyError(ODMPluginBaseException):
    """Exception for when the entity cannot be created due to a duplicate key error."""

    pass


class OperationError(ODMPluginBaseException):
    """Exception for when an operation fails."""

    pass


class VaultUnwrapError(ODMPluginConfigError):
    """Exception for when the CSFLE master key cannot be unwrapped from Vault."""

    pass


class EncryptedFieldIndexCollisionError(ODMPluginConfigError):
    """Exception for when a declared encrypted field is also indexed."""

    pass
