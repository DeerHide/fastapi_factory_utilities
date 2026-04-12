"""Unit tests for audit objects."""

import datetime
import json
import uuid
from typing import Any

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


def _sample_auditable_entity() -> AuditableEntity:
    """Minimal `AuditableEntity` for `AuditEventObject` tests."""
    return AuditableEntity(
        id=uuid.uuid4(),
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )


def _audit_event_base_kwargs() -> dict[str, Any]:
    """Full valid kwargs for `AuditEventObject` construction in tests."""
    when = datetime.datetime.now(datetime.timezone.utc)
    return {
        "what": EntityName("test_entity"),
        "why": EntityFunctionalEventName("created"),
        "where": ServiceName("test_service"),
        "when": when,
        "who": {"id": str(uuid.uuid4())},
        "entity": _sample_auditable_entity(),
        "domain": DomainName("dom_testing"),
        "service": ServiceName("evt_service"),
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

    def test_missing_id_raises_validation_error(self) -> None:
        """Primary key is required."""
        with pytest.raises(ValidationError) as exc_info:
            AuditableEntity(
                created_at=datetime.datetime.now(datetime.timezone.utc),
                updated_at=datetime.datetime.now(datetime.timezone.utc),
            )

        locs = {err["loc"][0] for err in exc_info.value.errors()}
        assert "id" in locs

    def test_published_fields_defaults(self) -> None:
        """Published and published_at default when omitted."""
        entity = AuditableEntity(
            id=uuid.uuid4(),
            created_at=datetime.datetime.now(datetime.timezone.utc),
            updated_at=datetime.datetime.now(datetime.timezone.utc),
        )
        assert entity.published is False
        assert entity.published_at is None

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
        assert dumped["published"] is False
        assert dumped["published_at"] is None

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
        kwargs = _audit_event_base_kwargs()
        what = kwargs["what"]
        why = kwargs["why"]
        where = kwargs["where"]
        when = kwargs["when"]
        who = kwargs["who"]
        entity = kwargs["entity"]
        domain = kwargs["domain"]
        service = kwargs["service"]

        # Act
        audit_event: AuditEventObject[Any] = AuditEventObject(**kwargs)

        # Assert
        assert audit_event.what == what
        assert audit_event.why == why
        assert audit_event.where == where
        assert audit_event.when == when
        assert audit_event.who == who
        assert audit_event.entity == entity
        assert audit_event.domain == domain
        assert audit_event.service == service

    def test_valid_creation_with_additional_who_fields(self) -> None:
        """Test valid creation with additional fields in who."""
        # Arrange
        kwargs = _audit_event_base_kwargs()
        who = {
            "id": str(uuid.uuid4()),
            "realm_id": str(uuid.uuid4()),
            "group_id": str(uuid.uuid4()),
        }
        kwargs["who"] = who

        # Act
        audit_event: AuditEventObject[Any] = AuditEventObject(**kwargs)

        # Assert
        assert audit_event.who == who
        assert "realm_id" in audit_event.who
        assert "group_id" in audit_event.who

    def test_missing_what_raises_validation_error(self) -> None:
        """Test that missing what raises ValidationError."""
        kwargs = _audit_event_base_kwargs()
        del kwargs["what"]
        with pytest.raises(ValidationError) as exc_info:
            AuditEventObject(**kwargs)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("what",)

    def test_missing_who_raises_validation_error(self) -> None:
        """Test that missing who raises ValidationError."""
        kwargs = _audit_event_base_kwargs()
        del kwargs["who"]
        with pytest.raises(ValidationError) as exc_info:
            AuditEventObject(**kwargs)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("who",)

    def test_empty_who_raises_validation_error(self) -> None:
        """Test that empty who raises ValidationError."""
        kwargs = _audit_event_base_kwargs()
        kwargs["who"] = {}
        with pytest.raises(ValidationError) as exc_info:
            AuditEventObject(**kwargs)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("who",)
        assert "must not be empty" in str(errors[0]["msg"]).lower()

    def test_who_without_id_allowed_when_non_empty(self) -> None:
        """Who is only required to be a non-empty dict (id key not enforced)."""
        kwargs = _audit_event_base_kwargs()
        kwargs["who"] = {"realm_id": str(uuid.uuid4())}
        audit_event: AuditEventObject[Any] = AuditEventObject(**kwargs)

        assert "realm_id" in audit_event.who
        assert "id" not in audit_event.who

    def test_invalid_who_type_raises_validation_error(self) -> None:
        """Test that invalid who type raises ValidationError."""
        kwargs = _audit_event_base_kwargs()
        kwargs["who"] = "not_a_dict"  # type: ignore[assignment]
        with pytest.raises(ValidationError) as exc_info:
            AuditEventObject(**kwargs)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("who",)
        assert "dictionary" in str(errors[0]["msg"]).lower()

    def test_model_dump(self) -> None:
        """Test model serialization using model_dump."""
        # Arrange
        kwargs = _audit_event_base_kwargs()
        audit_event: AuditEventObject[Any] = AuditEventObject(**kwargs)

        # Act
        dumped = audit_event.model_dump()

        # Assert
        assert dumped["what"] == kwargs["what"]
        assert dumped["why"] == kwargs["why"]
        assert dumped["where"] == kwargs["where"]
        assert dumped["when"] == kwargs["when"]
        assert dumped["who"] == kwargs["who"]
        assert dumped["entity"] == kwargs["entity"].model_dump()
        assert dumped["domain"] == kwargs["domain"]
        assert dumped["service"] == kwargs["service"]

    def test_model_dump_json(self) -> None:
        """Test model serialization using model_dump_json."""
        # Arrange
        kwargs = _audit_event_base_kwargs()
        audit_event: AuditEventObject[Any] = AuditEventObject(**kwargs)

        # Act
        json_str = audit_event.model_dump_json()

        # Assert
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["what"] == kwargs["what"]
        assert data["why"] == kwargs["why"]
        assert data["where"] == kwargs["where"]
        assert data["who"] == kwargs["who"]
        assert data["domain"] == kwargs["domain"]
        assert data["service"] == kwargs["service"]
        assert data["entity"]["id"] == str(kwargs["entity"].id)

    def test_model_validate(self) -> None:
        """Test model deserialization using model_validate."""
        # Arrange
        kwargs = _audit_event_base_kwargs()
        data: dict[str, Any] = dict(kwargs)

        # Act
        audit_event: AuditEventObject[Any] = AuditEventObject.model_validate(data)

        # Assert
        assert audit_event.what == kwargs["what"]
        assert audit_event.why == kwargs["why"]
        assert audit_event.where == kwargs["where"]
        assert audit_event.when == kwargs["when"]
        assert audit_event.who == kwargs["who"]
        assert audit_event.entity == kwargs["entity"]
        assert audit_event.domain == kwargs["domain"]
        assert audit_event.service == kwargs["service"]

    def test_model_validate_json(self) -> None:
        """Test model deserialization using model_validate_json."""
        # Arrange
        kwargs = _audit_event_base_kwargs()
        entity = kwargs["entity"]
        when = kwargs["when"]
        json_str = json.dumps(
            {
                "what": kwargs["what"],
                "why": kwargs["why"],
                "where": kwargs["where"],
                "when": when.isoformat(),
                "who": kwargs["who"],
                "domain": kwargs["domain"],
                "service": kwargs["service"],
                "entity": {
                    "id": str(entity.id),
                    "created_at": entity.created_at.isoformat(),
                    "updated_at": entity.updated_at.isoformat(),
                    "deleted_at": None,
                    "published": False,
                    "published_at": None,
                },
            }
        )

        # Act
        audit_event: AuditEventObject[Any] = AuditEventObject.model_validate_json(json_str)

        # Assert
        assert audit_event.what == kwargs["what"]
        assert audit_event.why == kwargs["why"]
        assert audit_event.where == kwargs["where"]
        assert audit_event.who == kwargs["who"]
        assert audit_event.domain == kwargs["domain"]
        assert audit_event.service == kwargs["service"]
        assert str(audit_event.entity.id) == str(entity.id)

    def test_round_trip_serialization(self) -> None:
        """Test round-trip serialization: create → serialize → deserialize."""
        # Arrange
        kwargs = _audit_event_base_kwargs()
        kwargs["who"] = {
            "id": str(uuid.uuid4()),
            "realm_id": str(uuid.uuid4()),
        }
        original: AuditEventObject[Any] = AuditEventObject(**kwargs)

        dumped = original.model_dump()
        restored: AuditEventObject[Any] = AuditEventObject.model_validate(dumped)

        # Assert
        assert restored.what == original.what
        assert restored.why == original.why
        assert restored.where == original.where
        assert restored.when == original.when
        assert restored.who == original.who
        assert restored.entity == original.entity
        assert restored.domain == original.domain
        assert restored.service == original.service
