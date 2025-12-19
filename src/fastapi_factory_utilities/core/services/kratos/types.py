"""Kratos types module."""

import uuid
from typing import NewType

# Provider is the name of the authentication provider for oidc/saml
KratosIdentityId = NewType("KratosIdentityId", uuid.UUID)
KratosProvider = NewType("KratosProvider", str)
KratosExternalId = NewType("KratosExternalId", str)
KratosSchemaId = NewType("KratosSchemaId", str)
KratosRecoveryCode = NewType("KratosRecoveryCode", str)
KratosRecoveryLink = NewType("KratosRecoveryLink", str)
__all__: list[str] = [
    "KratosExternalId",
    "KratosIdentityId",
    "KratosProvider",
    "KratosSchemaId",
]
