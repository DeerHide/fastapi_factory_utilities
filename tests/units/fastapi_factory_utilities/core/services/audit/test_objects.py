"""Unit tests for audit objects."""

import datetime
import json
import uuid
from typing import Any

import pytest
from pydantic import ValidationError

from typing import Any

from fastapi_factory_utilities.core.services.audit.objects import (
    AuditableEntity,
    AuditEventObject,
    EntityFunctionalEventName,
    EntityName,
    ServiceName,
)


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
        )

        # Assert
        assert entity.deleted_at == deleted_at

    def test_get_audit_name_raises_value_error_when_not_set(self) -> None:
        """Test that get_audit_name raises ValueError when audit name is not set."""
        # Arrange
        entity = AuditableEntity(
            id=uuid.uuid4(),
            created_at=datetime.datetime.now(datetime.timezone.utc),
            updated_at=datetime.datetime.now(datetime.timezone.utc),
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Audit name is not set"):
            entity.get_audit_name()

    def test_get_audit_name_returns_audit_name_when_set(self) -> None:
        """Test that get_audit_name returns the audit name when set."""
        # Arrange
        entity = AuditableEntity(
            id=uuid.uuid4(),
            created_at=datetime.datetime.now(datetime.timezone.utc),
            updated_at=datetime.datetime.now(datetime.timezone.utc),
        )
        audit_name = EntityName("test_entity")
        entity._audit_name = audit_name  # type: ignore[attr-defined]

        # Act
        result = entity.get_audit_name()

        # Assert
        assert result == audit_name

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
        )

        # Act
        dumped = entity.model_dump()

        # Assert
        assert dumped["id"] == entity_id
        assert dumped["created_at"] == created_at
        assert dumped["updated_at"] == updated_at
        assert dumped["deleted_at"] == deleted_at

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

    def test_who_without_id_raises_validation_error(self) -> None:
        """Test that who without id key raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AuditEventObject(
                what=EntityName("test_entity"),
                why=EntityFunctionalEventName("created"),
                where=ServiceName("test_service"),
                when=datetime.datetime.now(datetime.timezone.utc),
                who={"realm_id": str(uuid.uuid4())},
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("who",)
        assert "must contain id key" in str(errors[0]["msg"]).lower()

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

