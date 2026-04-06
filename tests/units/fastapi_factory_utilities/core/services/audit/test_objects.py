"""Unit tests for audit objects."""

import datetime
import json
import uuid
from typing import Any, TypedDict

import pytest
from pydantic import ValidationError

from fastapi_factory_utilities.core.services.audit.objects import (
    AuditableEntity,
    AuditEventObject,
    DomainName,
    EntityFunctionalEventName,
    EntityName,
    ServiceName,
)


class _AuditableNamesKw(TypedDict):
    """Keyword bundle for AuditableEntity construction in tests."""

    entity_name: EntityName
    domain_name: DomainName
    service_name: ServiceName


def _auditable_names() -> _AuditableNamesKw:
    """Defaults for required auditable metadata (PartStr segments >= 3 chars)."""
    return {
        "entity_name": EntityName("test_entity"),
        "domain_name": DomainName("dom_testing"),
        "service_name": ServiceName("test_service"),
    }


class TestAuditableEntity:
    """Unit tests for AuditableEntity."""

    def test_valid_creation_with_all_required_fields(self) -> None:
        """Test valid creation with all required fields."""
        # Arrange
        entity_id = uuid.uuid4()
        created_at = datetime.datetime.now(datetime.timezone.utc)
        updated_at = datetime.datetime.now(datetime.timezone.utc)

        # Act
        entity = AuditableEntity(
            id=entity_id,
            created_at=created_at,
            updated_at=updated_at,
            **_auditable_names(),
        )

        # Assert
        assert entity.id == entity_id
        assert entity.created_at == created_at
        assert entity.updated_at == updated_at
        assert entity.deleted_at is None

    def test_valid_creation_with_deleted_at(self) -> None:
        """Test valid creation with deleted_at populated."""
        # Arrange
        entity_id = uuid.uuid4()
        created_at = datetime.datetime.now(datetime.timezone.utc)
        updated_at = datetime.datetime.now(datetime.timezone.utc)
        deleted_at = datetime.datetime.now(datetime.timezone.utc)

        # Act
        entity = AuditableEntity(
            id=entity_id,
            created_at=created_at,
            updated_at=updated_at,
            deleted_at=deleted_at,
            **_auditable_names(),
        )

        # Assert
        assert entity.deleted_at == deleted_at

    def test_missing_auditable_metadata_raises_validation_error(self) -> None:
        """Entity, domain, and service names are required."""
        with pytest.raises(ValidationError) as exc_info:
            AuditableEntity(
                id=uuid.uuid4(),
                created_at=datetime.datetime.now(datetime.timezone.utc),
                updated_at=datetime.datetime.now(datetime.timezone.utc),
            )

        locs = {err["loc"][0] for err in exc_info.value.errors()}
        assert "entity_name" in locs
        assert "domain_name" in locs
        assert "service_name" in locs

    def test_getters_return_constructor_metadata(self) -> None:
        """get_* accessors return the same values passed into the model."""
        names = _auditable_names()
        entity = AuditableEntity(
            id=uuid.uuid4(),
            created_at=datetime.datetime.now(datetime.timezone.utc),
            updated_at=datetime.datetime.now(datetime.timezone.utc),
            **names,
        )

        assert entity.get_entity_name() == names["entity_name"]
        assert entity.get_domain_name() == names["domain_name"]
        assert entity.get_service_name() == names["service_name"]

    def test_model_dump(self) -> None:
        """Test model serialization using model_dump."""
        # Arrange
        entity_id = uuid.uuid4()
        created_at = datetime.datetime.now(datetime.timezone.utc)
        updated_at = datetime.datetime.now(datetime.timezone.utc)
        deleted_at = datetime.datetime.now(datetime.timezone.utc)

        entity = AuditableEntity(
            id=entity_id,
            created_at=created_at,
            updated_at=updated_at,
            deleted_at=deleted_at,
            **_auditable_names(),
        )

        # Act
        dumped = entity.model_dump()

        # Assert
        assert dumped["id"] == entity_id
        assert dumped["created_at"] == created_at
        assert dumped["updated_at"] == updated_at
        assert dumped["deleted_at"] == deleted_at
        assert "entity_name" not in dumped
        assert "domain_name" not in dumped
        assert "service_name" not in dumped

    def test_model_dump_json(self) -> None:
        """Test model serialization using model_dump_json."""
        # Arrange
        entity_id = uuid.uuid4()
        created_at = datetime.datetime.now(datetime.timezone.utc)
        updated_at = datetime.datetime.now(datetime.timezone.utc)

        entity = AuditableEntity(
            id=entity_id,
            created_at=created_at,
            updated_at=updated_at,
            **_auditable_names(),
        )

        # Act
        json_str = entity.model_dump_json()

        # Assert
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert str(data["id"]) == str(entity_id)
        assert data["deleted_at"] is None


class TestAuditEventObject:
    """Unit tests for AuditEventObject."""

    def test_valid_creation_with_all_required_fields(self) -> None:
        """Test valid creation with all required fields."""
        # Arrange
        what = EntityName("test_entity")
        why = EntityFunctionalEventName("created")
        where = ServiceName("test_service")
        when = datetime.datetime.now(datetime.timezone.utc)
        who = {"id": str(uuid.uuid4())}

        # Act
        audit_event: AuditEventObject[Any] = AuditEventObject(
            what=what,
            why=why,
            where=where,
            when=when,
            who=who,
        )

        # Assert
        assert audit_event.what == what
        assert audit_event.why == why
        assert audit_event.where == where
        assert audit_event.when == when
        assert audit_event.who == who

    def test_valid_creation_with_additional_who_fields(self) -> None:
        """Test valid creation with additional fields in who."""
        # Arrange
        what = EntityName("test_entity")
        why = EntityFunctionalEventName("created")
        where = ServiceName("test_service")
        when = datetime.datetime.now(datetime.timezone.utc)
        who = {
            "id": str(uuid.uuid4()),
            "realm_id": str(uuid.uuid4()),
            "group_id": str(uuid.uuid4()),
        }

        # Act
        audit_event: AuditEventObject[Any] = AuditEventObject(
            what=what,
            why=why,
            where=where,
            when=when,
            who=who,
        )

        # Assert
        assert audit_event.who == who
        assert "realm_id" in audit_event.who
        assert "group_id" in audit_event.who

    def test_missing_what_raises_validation_error(self) -> None:
        """Test that missing what raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AuditEventObject(
                why=EntityFunctionalEventName("created"),
                where=ServiceName("test_service"),
                when=datetime.datetime.now(datetime.timezone.utc),
                who={"id": str(uuid.uuid4())},
            )  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("what",)

    def test_missing_who_raises_validation_error(self) -> None:
        """Test that missing who raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AuditEventObject(
                what=EntityName("test_entity"),
                why=EntityFunctionalEventName("created"),
                where=ServiceName("test_service"),
                when=datetime.datetime.now(datetime.timezone.utc),
            )  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("who",)

    def test_empty_who_raises_validation_error(self) -> None:
        """Test that empty who raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AuditEventObject(
                what=EntityName("test_entity"),
                why=EntityFunctionalEventName("created"),
                where=ServiceName("test_service"),
                when=datetime.datetime.now(datetime.timezone.utc),
                who={},
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("who",)
        assert "must not be empty" in str(errors[0]["msg"]).lower()

    def test_who_without_id_allowed_when_non_empty(self) -> None:
        """Who is only required to be a non-empty dict (id key not enforced)."""
        audit_event: AuditEventObject[Any] = AuditEventObject(
            what=EntityName("test_entity"),
            why=EntityFunctionalEventName("created"),
            where=ServiceName("test_service"),
            when=datetime.datetime.now(datetime.timezone.utc),
            who={"realm_id": str(uuid.uuid4())},
        )

        assert "realm_id" in audit_event.who
        assert "id" not in audit_event.who

    def test_invalid_who_type_raises_validation_error(self) -> None:
        """Test that invalid who type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AuditEventObject(
                what=EntityName("test_entity"),
                why=EntityFunctionalEventName("created"),
                where=ServiceName("test_service"),
                when=datetime.datetime.now(datetime.timezone.utc),
                who="not_a_dict",  # type: ignore[arg-type]
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("who",)
        assert "dictionary" in str(errors[0]["msg"]).lower()

    def test_model_dump(self) -> None:
        """Test model serialization using model_dump."""
        # Arrange
        what = EntityName("test_entity")
        why = EntityFunctionalEventName("created")
        where = ServiceName("test_service")
        when = datetime.datetime.now(datetime.timezone.utc)
        who = {"id": str(uuid.uuid4())}

        audit_event: AuditEventObject[Any] = AuditEventObject(
            what=what,
            why=why,
            where=where,
            when=when,
            who=who,
        )

        # Act
        dumped = audit_event.model_dump()

        # Assert
        assert dumped["what"] == what
        assert dumped["why"] == why
        assert dumped["where"] == where
        assert dumped["when"] == when
        assert dumped["who"] == who

    def test_model_dump_json(self) -> None:
        """Test model serialization using model_dump_json."""
        # Arrange
        what = EntityName("test_entity")
        why = EntityFunctionalEventName("created")
        where = ServiceName("test_service")
        when = datetime.datetime.now(datetime.timezone.utc)
        who = {"id": str(uuid.uuid4())}

        audit_event: AuditEventObject[Any] = AuditEventObject(
            what=what,
            why=why,
            where=where,
            when=when,
            who=who,
        )

        # Act
        json_str = audit_event.model_dump_json()

        # Assert
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["what"] == what
        assert data["why"] == why
        assert data["where"] == where
        assert data["who"] == who

    def test_model_validate(self) -> None:
        """Test model deserialization using model_validate."""
        # Arrange
        what = EntityName("test_entity")
        why = EntityFunctionalEventName("created")
        where = ServiceName("test_service")
        when = datetime.datetime.now(datetime.timezone.utc)
        who = {"id": str(uuid.uuid4())}

        data: dict[str, Any] = {
            "what": what,
            "why": why,
            "where": where,
            "when": when,
            "who": who,
        }

        # Act
        audit_event: AuditEventObject[Any] = AuditEventObject.model_validate(data)

        # Assert
        assert audit_event.what == what
        assert audit_event.why == why
        assert audit_event.where == where
        assert audit_event.when == when
        assert audit_event.who == who

    def test_model_validate_json(self) -> None:
        """Test model deserialization using model_validate_json."""
        # Arrange
        what = EntityName("test_entity")
        why = EntityFunctionalEventName("created")
        where = ServiceName("test_service")
        when = datetime.datetime.now(datetime.timezone.utc)
        who = {"id": str(uuid.uuid4())}

        json_str = json.dumps(
            {
                "what": what,
                "why": why,
                "where": where,
                "when": when.isoformat(),
                "who": who,
            }
        )

        # Act
        audit_event: AuditEventObject[Any] = AuditEventObject.model_validate_json(json_str)

        # Assert
        assert audit_event.what == what
        assert audit_event.why == why
        assert audit_event.where == where
        assert audit_event.who == who

    def test_round_trip_serialization(self) -> None:
        """Test round-trip serialization: create → serialize → deserialize."""
        # Arrange
        what = EntityName("test_entity")
        why = EntityFunctionalEventName("created")
        where = ServiceName("test_service")
        when = datetime.datetime.now(datetime.timezone.utc)
        who = {
            "id": str(uuid.uuid4()),
            "realm_id": str(uuid.uuid4()),
        }

        original: AuditEventObject[Any] = AuditEventObject(
            what=what,
            why=why,
            where=where,
            when=when,
            who=who,
        )

        # Act
        dumped = original.model_dump()
        restored: AuditEventObject[Any] = AuditEventObject.model_validate(dumped)

        # Assert
        assert restored.what == original.what
        assert restored.why == original.why
        assert restored.where == original.where
        assert restored.when == original.when
        assert restored.who == original.who
