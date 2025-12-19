"""Kratos service module."""

from .enums import (
    AuthenticationMethodEnum,
    AuthenticatorAssuranceLevelEnum,
    KratosFlowTypeEnum,
    KratosIdentityPatchOpEnum,
    KratosIdentityStateEnum,
)
from .exceptions import KratosIdentityNotFoundError, KratosOperationError, KratosSessionInvalidError
from .objects import (
    KratosIdentityObject,
    KratosRecoveryAddressObject,
    KratosSessionObject,
    KratosTraitsObject,
    MetadataObject,
)
from .services import KratosGenericWhoamiService, KratosIdentityGenericService, KratosIdentityPatchObject
from .types import (
    KratosExternalId,
    KratosIdentityId,
    KratosProvider,
    KratosRecoveryCode,
    KratosRecoveryLink,
    KratosSchemaId,
)

__all__: list[str] = [
    "AuthenticationMethodEnum",
    "AuthenticatorAssuranceLevelEnum",
    "KratosExternalId",
    "KratosFlowTypeEnum",
    "KratosGenericWhoamiService",
    "KratosIdentityGenericService",
    "KratosIdentityId",
    "KratosIdentityNotFoundError",
    "KratosIdentityObject",
    "KratosIdentityPatchObject",
    "KratosIdentityPatchOpEnum",
    "KratosIdentityStateEnum",
    "KratosOperationError",
    "KratosProvider",
    "KratosRecoveryAddressObject",
    "KratosRecoveryCode",
    "KratosRecoveryLink",
    "KratosSchemaId",
    "KratosSessionInvalidError",
    "KratosSessionObject",
    "KratosTraitsObject",
    "MetadataObject",
]
