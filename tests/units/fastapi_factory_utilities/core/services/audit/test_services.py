"""Unit tests for the audit services."""

import datetime
import uuid
from collections.abc import Callable
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from fastapi_factory_utilities.core.plugins.aiopika import (
    AbstractPublisher,
    AiopikaPluginBaseError,
    ExchangeName,
    GenericMessage,
    RoutingKey,
)
from fastapi_factory_utilities.core.plugins.aiopika.types import PartStr
from fastapi_factory_utilities.core.services.audit.exceptions import AuditServiceError
from fastapi_factory_utilities.core.services.audit.objects import (
    AuditableEntity,
    AuditEventObject,
    DomainName,
    EntityFunctionalEventName,
    EntityName,
    ServiceName,
)
from fastapi_factory_utilities.core.services.audit.services import AbstractAuditPublisherService


def _sample_auditable_entity() -> AuditableEntity[uuid.UUID]:
    """Minimal entity for audit service tests."""
    return AuditableEntity(
        id=uuid.uuid4(),
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )


class MockAuditEventObject(AuditEventObject[AuditableEntity[uuid.UUID]]):
    """Mock audit event object for testing."""


class ConcreteAuditPublisherService(AbstractAuditPublisherService[MockAuditEventObject]):
    """Concrete implementation for testing."""


class CustomizedAuditPublisherService(ConcreteAuditPublisherService):
    """Publisher service overriding routing key parts."""

    EXCHANGE_NAME = ExchangeName("audit")
    ROUTING_KEY_PREFIX = PartStr("events")
    ROUTING_KEY_DOMAIN_NAME = DomainName(PartStr("identity"))
    ROUTING_KEY_SERVICE_NAME = ServiceName(PartStr("iam"))
    ROUTING_KEY_ENTITY_NAME = EntityName(PartStr("user"))


@pytest.fixture(name="service_name")
def fixture_service_name() -> ServiceName:
    """Create a service name for testing."""
    return ServiceName(PartStr("test_service"))


@pytest.fixture(name="audit_event")
def fixture_audit_event() -> MockAuditEventObject:
    """Create an audit event for testing."""
    return MockAuditEventObject(
        what=EntityName(PartStr("test_entity")),
        why=EntityFunctionalEventName(PartStr("created")),
        where=ServiceName(PartStr("test_service")),
        when=datetime.datetime.now(datetime.timezone.utc),
        who={"id": str(uuid.uuid4())},
        entity=_sample_auditable_entity(),
        domain=DomainName(PartStr("dom_testing")),
        service=ServiceName(PartStr("evt_service")),
    )


class TestAbstractAuditPublisherService:
    """Tests for the AbstractAuditPublisherService class."""

    def test_init_builds_exchange_and_sender(self, service_name: ServiceName) -> None:
        """Service initializes sender and exchange."""
        service = ConcreteAuditPublisherService(sender=service_name)

        assert getattr(service, "_sender") == service_name
        assert getattr(service.build_exchange(), "_name") == ExchangeName("default")

    def test_build_routing_key_pattern_uses_class_config(self, audit_event: MockAuditEventObject) -> None:
        """Routing key pattern is based on configurable class values."""
        service = CustomizedAuditPublisherService(sender=ServiceName(PartStr("publisher")))

        routing_key = service.build_routing_key_pattern(audit_event=audit_event)

        assert routing_key == RoutingKey("events.identity.iam.user.created")

    @pytest.mark.asyncio
    async def test_publish_applies_pre_publish_hook_and_calls_base_publisher(
        self,
        monkeypatch: pytest.MonkeyPatch,
        service_name: ServiceName,
        audit_event: MockAuditEventObject,
    ) -> None:
        """Publish filters entity then delegates to base publisher."""
        service = ConcreteAuditPublisherService(sender=service_name)
        publish_mock = AsyncMock()
        monkeypatch.setattr(AbstractPublisher, "publish", publish_mock)

        def _mark_published(
            cls_: type[MockAuditEventObject],
            entity: AuditableEntity[uuid.UUID],
        ) -> AuditableEntity[uuid.UUID]:
            _ = cls_
            return entity.model_copy(update={"published": True})

        monkeypatch.setattr(
            MockAuditEventObject,
            "pre_publish_hook",
            classmethod(cast(Callable[..., Any], _mark_published)),
        )

        message = GenericMessage(data=audit_event)
        routing_key = service.build_routing_key_pattern(audit_event=message.data)

        await service.publish(message=message, routing_key=routing_key)

        publish_mock.assert_awaited_once_with(message=message, routing_key=routing_key)
        assert message.data.entity.published is True

    @pytest.mark.asyncio
    async def test_publish_wraps_aiopika_errors(
        self,
        monkeypatch: pytest.MonkeyPatch,
        service_name: ServiceName,
        audit_event: MockAuditEventObject,
    ) -> None:
        """Aiopika publish failure is translated into AuditServiceError."""
        service = ConcreteAuditPublisherService(sender=service_name)
        publisher_error = AiopikaPluginBaseError(message="Failed to publish")
        monkeypatch.setattr(AbstractPublisher, "publish", AsyncMock(side_effect=publisher_error))

        message = GenericMessage(data=audit_event)
        routing_key = service.build_routing_key_pattern(audit_event=audit_event)

        with pytest.raises(AuditServiceError) as exc_info:
            await service.publish(message=message, routing_key=routing_key)

        err = exc_info.value
        assert "Failed to publish the audit event" in str(err)
        assert err.__cause__ == publisher_error
        assert getattr(err, "audit_event", None) == str(audit_event)
        assert getattr(err, "routing_key", None) == str(routing_key)
