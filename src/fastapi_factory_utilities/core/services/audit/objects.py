"""Provides the objects for the audit service."""

import datetime
import uuid
from typing import Any, Generic, NewType, TypeVar, cast

from pydantic import BaseModel, Field, field_validator

from fastapi_factory_utilities.core.plugins.aiopika.types import PartStr

EntityName = NewType("EntityName", PartStr)
EntityFunctionalEventName = NewType("EntityFunctionalEventName", PartStr)
ServiceName = NewType("ServiceName", PartStr)
DomainName = NewType("DomainName", PartStr)


class AuditableEntity(BaseModel):
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

    id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    deleted_at: datetime.datetime | None = None

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


class AuditEventObject(BaseModel, Generic[AuditEventActorGeneric]):
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

    id: uuid.UUID | None = None
    what: EntityName
    why: EntityFunctionalEventName
    where: ServiceName
    when: datetime.datetime
    who: dict[str, Any]
    entity: AuditEventActorGeneric
    domain: DomainName
    service: ServiceName

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
