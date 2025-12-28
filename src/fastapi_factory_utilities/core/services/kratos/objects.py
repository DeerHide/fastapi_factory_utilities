"""Provides the Kratos Objects."""

import datetime
import uuid
from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from .enums import AuthenticationMethodEnum, AuthenticatorAssuranceLevelEnum, KratosIdentityStateEnum
from .types import KratosExternalId, KratosIdentityId, KratosProvider, KratosSchemaId


class KratosTraitsObject(BaseModel):
    """Traits for Kratos.

    Can be extended to include additional traits.

    email: The email address of the user.
    realm_id: The realm ID of the user. (it's the segmentation id for all resources)
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")


class MetadataObject(BaseModel):
    """Metadata for Kratos."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")


class KratosRecoveryAddressObject(BaseModel):
    """Recovery address for Kratos."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    id: uuid.UUID
    value: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    via: str


GenericTraitsObject = TypeVar("GenericTraitsObject", bound=KratosTraitsObject)
GenericMetadataPublicObject = TypeVar("GenericMetadataPublicObject", bound=MetadataObject)
GenericMetadataAdminObject = TypeVar("GenericMetadataAdminObject", bound=MetadataObject)


class KratosIdentityObject(
    BaseModel, Generic[GenericTraitsObject, GenericMetadataPublicObject, GenericMetadataAdminObject]
):
    """Identity for Kratos."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    id: KratosIdentityId
    state: KratosIdentityStateEnum
    state_changed_at: datetime.datetime
    traits: GenericTraitsObject
    created_at: datetime.datetime
    updated_at: datetime.datetime
    external_id: KratosExternalId
    metadata_admin: GenericMetadataAdminObject | None = None
    metadata_public: GenericMetadataPublicObject | None = None
    recovery_addresses: list[KratosRecoveryAddressObject]
    schema_id: KratosSchemaId
    schema_url: str


GenericKratosIdentityObject = TypeVar("GenericKratosIdentityObject", bound=BaseModel)


class KratosAuthenticationMethod(BaseModel):
    """Authentication method for Kratos."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    aal: AuthenticatorAssuranceLevelEnum
    completed_at: datetime.datetime
    method: AuthenticationMethodEnum
    provider: KratosProvider


class KratosSessionObject(BaseModel, Generic[GenericKratosIdentityObject]):
    """Session object for Kratos."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    id: uuid.UUID
    active: bool
    issued_at: datetime.datetime
    expires_at: datetime.datetime
    authenticated_at: datetime.datetime
    authentication_methods: list[KratosAuthenticationMethod]
    authenticator_assurance_level: AuthenticatorAssuranceLevelEnum
    identity: GenericKratosIdentityObject
    tokenized: str
