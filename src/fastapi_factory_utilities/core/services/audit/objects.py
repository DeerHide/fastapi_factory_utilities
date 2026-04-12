"""Provides the objects for the audit service."""

import datetime
import uuid
from typing import Annotated, Any, Generic, NewType, TypeVar, cast

from pydantic import BaseModel, Field, field_validator

from fastapi_factory_utilities.core.plugins.aiopika.types import PartStr
from fastapi_factory_utilities.core.plugins.odm_plugin.helpers import PersistedEntity
from fastapi_factory_utilities.core.utils.api import ApiResponseField, ApiResponseModelAbstract
from fastapi_factory_utilities.core.utils.queries import SearchableEntity, SearchableField

EntityName = NewType("EntityName", PartStr)
UseCaseName = NewType("UseCaseName", PartStr)
EntityFunctionalEventName = NewType("EntityFunctionalEventName", PartStr)
ServiceName = NewType("ServiceName", PartStr)
DomainName = NewType("DomainName", PartStr)

GenericPersistedEntityId = TypeVar("GenericPersistedEntityId", bound=uuid.UUID)


class AuditableEntity(PersistedEntity[GenericPersistedEntityId], Generic[GenericPersistedEntityId]):
    """Auditable entity persisted in the platform sense.

    Attributes:
        id: The ID of the entity (required; overrides ``PersistedEntity`` auto-generated default).
        created_at: The creation date of the entity.
        updated_at: The last update date of the entity.
        deleted_at: The deletion date of the entity.
        published: Whether the entity is published.
        published_at: When the entity was published, if applicable.
    """

    id: Annotated[GenericPersistedEntityId, ApiResponseField, SearchableField]
    deleted_at: Annotated[datetime.datetime | None, ApiResponseField, SearchableField] = None
    published: Annotated[bool, ApiResponseField, SearchableField] = False
    published_at: Annotated[datetime.datetime | None, ApiResponseField, SearchableField] = None


class PersistedAuditableEntity(AuditableEntity[GenericPersistedEntityId], Generic[GenericPersistedEntityId]):
    """Auditable entity backed by ODM persistence (Beanie document base)."""

    pass


AuditEventActorGeneric = TypeVar("AuditEventActorGeneric", bound=AuditableEntity[Any])


class AuditEventObject(SearchableEntity, ApiResponseModelAbstract, BaseModel, Generic[AuditEventActorGeneric]):
    """Audit event object.

    Attributes:
        id: The ID of the entity that triggered the event if has one (optional).
        what: The name of the entity.
        why: The name of the functional event.
        where: The name of the service.
        when: The date and time of the event.
        who: The dictionary of ids of the actors involved in the event.
        (always at least contains the id of the actor who performed the event but can contains more ids id needed like
        segmentation ids (realms, groups, etc.))
    """

    id: Annotated[uuid.UUID | None, ApiResponseField, SearchableField] = None
    what: Annotated[EntityName, ApiResponseField, SearchableField]
    why: Annotated[EntityFunctionalEventName, ApiResponseField, SearchableField]
    where: Annotated[ServiceName, ApiResponseField, SearchableField]
    when: Annotated[datetime.datetime, ApiResponseField, SearchableField]
    who: Annotated[dict[str, Any], ApiResponseField, SearchableField]
    entity: Annotated[AuditEventActorGeneric, ApiResponseField, SearchableField]
    domain: Annotated[DomainName, ApiResponseField, SearchableField]
    service: Annotated[ServiceName, ApiResponseField, SearchableField]
    use_case: Annotated[UseCaseName, ApiResponseField, SearchableField] = Field(default=UseCaseName(PartStr("unknown")))
    metadata: Annotated[dict[str, Any], ApiResponseField, SearchableField] = Field(default_factory=dict)

    @field_validator("who")
    @classmethod
    def who_validator(cls, value: Any) -> dict[str, Any]:
        """Validate the who."""
        # Check if the value is a dictionary
        if not isinstance(value, dict):
            raise ValueError("Who must be a dictionary.")
        value_dict: dict[str, Any] = cast(dict[str, Any], value)
        # Check if the dictionary is empty
        if len(value_dict) == 0:
            raise ValueError("Who must not be empty.")
        return value_dict
