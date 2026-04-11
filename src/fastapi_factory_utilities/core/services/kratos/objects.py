"""Provides the Kratos Objects."""

import datetime
import uuid
from typing import Annotated, ClassVar, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from fastapi_factory_utilities.core.utils.api import ApiResponseField, ApiResponseModelAbstract
from fastapi_factory_utilities.core.utils.queries import SearchableEntity, SearchableField

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

    id: Annotated[uuid.UUID, ApiResponseField, SearchableField]
    value: Annotated[str, ApiResponseField, SearchableField]
    created_at: Annotated[datetime.datetime, ApiResponseField, SearchableField]
    updated_at: Annotated[datetime.datetime, ApiResponseField, SearchableField]
    via: Annotated[str, ApiResponseField, SearchableField]


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

    id: Annotated[KratosIdentityId, ApiResponseField, SearchableField]
    state: Annotated[KratosIdentityStateEnum, ApiResponseField, SearchableField]
    state_changed_at: Annotated[datetime.datetime, ApiResponseField, SearchableField]
    traits: Annotated[GenericTraitsObject, ApiResponseField, SearchableField]
    created_at: Annotated[datetime.datetime, ApiResponseField, SearchableField]
    updated_at: Annotated[datetime.datetime, ApiResponseField, SearchableField]
    external_id: Annotated[KratosExternalId | None, ApiResponseField, SearchableField] = None
    metadata_admin: Annotated[GenericMetadataAdminObject | None, ApiResponseField, SearchableField] = None
    metadata_public: Annotated[GenericMetadataPublicObject | None, ApiResponseField, SearchableField] = None
    recovery_addresses: Annotated[list[KratosRecoveryAddressObject], ApiResponseField, SearchableField]
    schema_id: Annotated[KratosSchemaId, ApiResponseField, SearchableField]
    schema_url: Annotated[str, ApiResponseField, SearchableField]


GenericKratosIdentityObject = TypeVar("GenericKratosIdentityObject", bound=BaseModel)


class KratosAuthenticationMethod(SearchableEntity, ApiResponseModelAbstract, BaseModel):
    """Authentication method for Kratos."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    aal: Annotated[AuthenticatorAssuranceLevelEnum, ApiResponseField, SearchableField]
    completed_at: Annotated[datetime.datetime, ApiResponseField, SearchableField]
    method: Annotated[AuthenticationMethodEnum, ApiResponseField, SearchableField]
    provider: Annotated[KratosProvider | None, ApiResponseField, SearchableField] = None


class KratosSessionObject(SearchableEntity, ApiResponseModelAbstract, BaseModel, Generic[GenericKratosIdentityObject]):
    """Session object for Kratos."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    id: Annotated[uuid.UUID, ApiResponseField, SearchableField]
    active: Annotated[bool, ApiResponseField, SearchableField]
    issued_at: Annotated[datetime.datetime, ApiResponseField, SearchableField]
    expires_at: Annotated[datetime.datetime, ApiResponseField, SearchableField]
    authenticated_at: Annotated[datetime.datetime, ApiResponseField, SearchableField]
    authentication_methods: Annotated[list[KratosAuthenticationMethod], ApiResponseField, SearchableField]
    authenticator_assurance_level: Annotated[AuthenticatorAssuranceLevelEnum, ApiResponseField, SearchableField]
    identity: Annotated[GenericKratosIdentityObject, ApiResponseField, SearchableField]
    tokenized: Annotated[str | None, ApiResponseField, SearchableField] = None
