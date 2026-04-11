"""Provides the objects for the audit service."""

import datetime
import uuid
from typing import Annotated, Any, Generic, NewType, TypeVar, cast

from pydantic import BaseModel, Field, field_validator

from fastapi_factory_utilities.core.plugins.aiopika.types import PartStr
from fastapi_factory_utilities.core.utils.api import ApiResponseField, ApiResponseModelAbstract
from fastapi_factory_utilities.core.utils.queries import SearchableEntity, SearchableField

EntityName = NewType("EntityName", PartStr)
EntityFunctionalEventName = NewType("EntityFunctionalEventName", PartStr)
ServiceName = NewType("ServiceName", PartStr)
DomainName = NewType("DomainName", PartStr)


class AuditableEntity(SearchableEntity, ApiResponseModelAbstract, BaseModel):
    """Auditable entity.

    Attributes:
        entity_name: Name used to identify the entity in the audit trail; must be unique in the ecosystem.
            Excluded from serialized model output by default.
        domain_name: Owning domain name (excluded from serialization).
        service_name: Owning service name (excluded from serialization).
        id: The ID of the entity.
        created_at: The creation date of the entity.
        updated_at: The last update date of the entity.
        deleted_at: The deletion date of the entity.
    """

    entity_name: EntityName = Field(exclude=True)
    domain_name: DomainName = Field(exclude=True)
    service_name: ServiceName = Field(exclude=True)

    id: Annotated[uuid.UUID, ApiResponseField, SearchableField]
    created_at: Annotated[datetime.datetime, ApiResponseField, SearchableField]
    updated_at: Annotated[datetime.datetime, ApiResponseField, SearchableField]
    deleted_at: Annotated[datetime.datetime | None, ApiResponseField, SearchableField] = None

    def get_domain_name(self) -> DomainName:
        """Get the domain name."""
        return self.domain_name

    def get_service_name(self) -> ServiceName:
        """Get the service name."""
        return self.service_name

    def get_entity_name(self) -> EntityName:
        """Get the entity audit name."""
        return self.entity_name


AuditEventActorGeneric = TypeVar("AuditEventActorGeneric", bound=AuditableEntity)


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
