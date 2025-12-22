"""Provides the objects for the audit service."""

import datetime
import uuid
from typing import Any, Generic, NewType, TypeVar, cast

from pydantic import BaseModel, PrivateAttr, field_validator

EntityName = NewType("EntityName", str)
EntityFunctionalEventName = NewType("EntityFunctionalEventName", str)
ServiceName = NewType("ServiceName", str)


class AuditableEntity(BaseModel):
    """Auditable entity.

    Attributes:
        _audit_name: The name of the audit. This is used to identify the entity in the audit trail.
            It's must be unique on the whole ecosystem.
        id: The ID of the entity.
        created_at: The creation date of the entity.
        updated_at: The last update date of the entity.
        deleted_at: The deletion date of the entity.
    """

    _audit_name: EntityName = PrivateAttr(default=EntityName(""))

    id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    deleted_at: datetime.datetime | None = None

    def get_audit_name(self) -> str:
        """Get the audit name."""
        if self._audit_name == EntityName(""):
            raise ValueError("Audit name is not set.")
        return self._audit_name


AuditEventActorGeneric = TypeVar("AuditEventActorGeneric", bound=AuditableEntity)


class AuditEventObject(BaseModel, Generic[AuditEventActorGeneric]):
    """Audit event object.

    Attributes:
        what: The name of the entity.
        why: The name of the functional event.
        where: The name of the service.
        when: The date and time of the event.
        who: The dictionary of ids of the actors involved in the event.
        (always at least contains the id of the actor who performed the event but can contains more ids id needed like
        segmentation ids (realms, groups, etc.))
    """

    what: EntityName
    why: EntityFunctionalEventName
    where: ServiceName
    when: datetime.datetime
    who: dict[str, Any]

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
        # Check if the dictionary contains id key
        if "id" not in value_dict:
            raise ValueError("Who must contain id key.")
        return value_dict
