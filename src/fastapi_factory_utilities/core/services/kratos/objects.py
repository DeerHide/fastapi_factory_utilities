"""Provides the Kratos Objects."""

import datetime
import uuid
from typing import Annotated, ClassVar, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from fastapi_factory_utilities.core.utils.api import ApiField, ApiResponseModelAbstract, SearchableEntity

from .enums import AuthenticationMethodEnum, AuthenticatorAssuranceLevelEnum, KratosIdentityStateEnum
from .types import KratosExternalId, KratosIdentityId, KratosProvider, KratosSchemaId


class KratosTraitsObject(SearchableEntity, ApiResponseModelAbstract, BaseModel):
    """Traits for Kratos.

    Can be extended to include additional traits.

    email: The email address of the user.
    realm_id: The realm ID of the user. (it's the segmentation id for all resources)
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")


class MetadataObject(SearchableEntity, ApiResponseModelAbstract, BaseModel):
    """Metadata for Kratos."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")


class KratosRecoveryAddressObject(SearchableEntity, ApiResponseModelAbstract, BaseModel):
    """Recovery address for Kratos."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    id: Annotated[uuid.UUID, ApiField(searchable=True)]
    value: Annotated[str, ApiField(searchable=True)]
    created_at: Annotated[datetime.datetime, ApiField(searchable=True)]
    updated_at: Annotated[datetime.datetime, ApiField(searchable=True)]
    via: Annotated[str, ApiField(searchable=True)]


GenericTraitsObject = TypeVar("GenericTraitsObject", bound=KratosTraitsObject)
GenericMetadataPublicObject = TypeVar("GenericMetadataPublicObject", bound=MetadataObject)
GenericMetadataAdminObject = TypeVar("GenericMetadataAdminObject", bound=MetadataObject)


class KratosIdentityObject(
    SearchableEntity,
    ApiResponseModelAbstract,
    BaseModel,
    Generic[GenericTraitsObject, GenericMetadataPublicObject, GenericMetadataAdminObject],
):
    """Identity for Kratos."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    id: Annotated[KratosIdentityId, ApiField(searchable=True)]
    state: Annotated[KratosIdentityStateEnum, ApiField(searchable=True)]
    state_changed_at: Annotated[datetime.datetime, ApiField(searchable=True)]
    traits: Annotated[GenericTraitsObject, ApiField(searchable=True)]
    created_at: Annotated[datetime.datetime, ApiField(searchable=True)]
    updated_at: Annotated[datetime.datetime, ApiField(searchable=True)]
    external_id: Annotated[KratosExternalId | None, ApiField(searchable=True)] = None
    metadata_admin: Annotated[GenericMetadataAdminObject | None, ApiField(searchable=True)] = None
    metadata_public: Annotated[GenericMetadataPublicObject | None, ApiField(searchable=True)] = None
    recovery_addresses: Annotated[list[KratosRecoveryAddressObject], ApiField(searchable=True)]
    schema_id: Annotated[KratosSchemaId, ApiField(searchable=True)]
    schema_url: Annotated[str, ApiField(searchable=True)]


GenericKratosIdentityObject = TypeVar("GenericKratosIdentityObject", bound=BaseModel)


class KratosAuthenticationMethod(SearchableEntity, ApiResponseModelAbstract, BaseModel):
    """Authentication method for Kratos."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    aal: Annotated[AuthenticatorAssuranceLevelEnum, ApiField(searchable=True)]
    completed_at: Annotated[datetime.datetime, ApiField(searchable=True)]
    method: Annotated[AuthenticationMethodEnum, ApiField(searchable=True)]
    provider: Annotated[KratosProvider | None, ApiField(searchable=True)] = None


class KratosSessionObject(SearchableEntity, ApiResponseModelAbstract, BaseModel, Generic[GenericKratosIdentityObject]):
    """Session object for Kratos."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    id: Annotated[uuid.UUID, ApiField(searchable=True)]
    active: Annotated[bool, ApiField(searchable=True)]
    issued_at: Annotated[datetime.datetime, ApiField(searchable=True)]
    expires_at: Annotated[datetime.datetime, ApiField(searchable=True)]
    authenticated_at: Annotated[datetime.datetime, ApiField(searchable=True)]
    authentication_methods: Annotated[list[KratosAuthenticationMethod], ApiField(searchable=True)]
    authenticator_assurance_level: Annotated[AuthenticatorAssuranceLevelEnum, ApiField(searchable=True)]
    identity: Annotated[GenericKratosIdentityObject, ApiField(searchable=True)]
    tokenized: Annotated[str | None, ApiField(searchable=True)] = None
