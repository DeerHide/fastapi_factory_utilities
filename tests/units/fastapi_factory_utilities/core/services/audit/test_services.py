"""Unit tests for the audit services."""

import datetime
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from fastapi_factory_utilities.core.plugins.aiopika import (
    AbstractPublisher,
    AiopikaPluginBaseError,
    GenericMessage,
    RoutingKey,
)
from fastapi_factory_utilities.core.services.audit.exceptions import AuditServiceError
from fastapi_factory_utilities.core.services.audit.objects import (
    AuditEventObject,
    EntityFunctionalEventName,
    EntityName,
    ServiceName,
)
from fastapi_factory_utilities.core.services.audit.services import AbstractAuditPublisherService


# Test model class for generic service testing
class MockAuditEventObject(AuditEventObject[Any]):
    """Mock audit event object for testing."""

    pass


class ConcreteAuditPublisherService(AbstractAuditPublisherService[MockAuditEventObject]):
    """Concrete implementation for testing."""

    def build_routing_key_pattern(self, audit_event: MockAuditEventObject) -> RoutingKey:
        """Build the routing key pattern for the audit event."""
        return RoutingKey(f"audit.{audit_event.where}.{audit_event.what}.{audit_event.why}")


@pytest.fixture(name="mock_publisher")
def fixture_mock_publisher() -> AbstractPublisher[GenericMessage[MockAuditEventObject]]:
    """Create a mock publisher for testing.

    Returns:
        AbstractPublisher[GenericMessage[MockAuditEventObject]]: A mock publisher.
    """
    return MagicMock(spec=AbstractPublisher)


@pytest.fixture(name="service_name")
def fixutre_service_name() -> ServiceName:
    """Create a service name for testing.

    Returns:
        ServiceName: A test service name.
    """
    return ServiceName("test_service")


@pytest.fixture(name="audit_event")
def fixture_audit_event() -> MockAuditEventObject:
    """Create an audit event for testing.

    Returns:
        MockAuditEventObject: A test audit event.
    """
    return MockAuditEventObject(
        what=EntityName("test_entity"),
        why=EntityFunctionalEventName("created"),
        where=ServiceName("test_service"),
        when=datetime.datetime.now(datetime.timezone.utc),
        who={"id": str(uuid.uuid4())},
    )


class TestAbstractAuditPublisherService:
    """Various tests for the AbstractAuditPublisherService class."""

    def test_init(
        self,
        service_name: ServiceName,
        mock_publisher: AbstractPublisher[GenericMessage[MockAuditEventObject]],
    ) -> None:
        """Test that __init__ properly initializes the service.

        Args:
            service_name (ServiceName): Service name fixture.
            mock_publisher (AbstractPublisher[GenericMessage[MockAuditEventObject]]): Mock publisher fixture.
        """
        service = ConcreteAuditPublisherService(sender=service_name, publisher=mock_publisher)

        assert service._sender == service_name  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert service._publisher == mock_publisher  # type: ignore[attr-defined] # pylint: disable=protected-access

    @pytest.mark.asyncio
    async def test_publish_success(
        self,
        service_name: ServiceName,
        mock_publisher: AbstractPublisher[GenericMessage[MockAuditEventObject]],
        audit_event: MockAuditEventObject,
    ) -> None:
        """Test successful publish call.

        Args:
            service_name (ServiceName): Service name fixture.
            mock_publisher (AbstractPublisher[GenericMessage[MockAuditEventObject]]): Mock publisher fixture.
            audit_event (MockAuditEventObject): Audit event fixture.
        """
        service = ConcreteAuditPublisherService(sender=service_name, publisher=mock_publisher)
        mock_publisher.publish = AsyncMock()

        await service.publish(audit_event=audit_event)

        # Verify publish was called
        mock_publisher.publish.assert_called_once()
        call_args = mock_publisher.publish.call_args

        # Verify message
        message: GenericMessage[MockAuditEventObject] = call_args.kwargs["message"]
        assert isinstance(message, GenericMessage)
        assert message.data == audit_event

        # Verify routing key
        routing_key: RoutingKey = call_args.kwargs["routing_key"]
        expected_routing_key = f"audit.{audit_event.where}.{audit_event.what}.{audit_event.why}"
        assert routing_key == expected_routing_key

    @pytest.mark.asyncio
    async def test_publish_raises_audit_service_error_on_publisher_error(
        self,
        service_name: ServiceName,
        mock_publisher: AbstractPublisher[GenericMessage[MockAuditEventObject]],
        audit_event: MockAuditEventObject,
    ) -> None:
        """Test that publish raises AuditServiceError when publisher raises AiopikaPluginBaseError.

        Args:
            service_name (ServiceName): Service name fixture.
            mock_publisher (AbstractPublisher[GenericMessage[MockAuditEventObject]]): Mock publisher fixture.
            audit_event (MockAuditEventObject): Audit event fixture.
        """
        service = ConcreteAuditPublisherService(sender=service_name, publisher=mock_publisher)
        publisher_error = AiopikaPluginBaseError(message="Failed to publish")
        mock_publisher.publish = AsyncMock(side_effect=publisher_error)

        with pytest.raises(AuditServiceError) as exc_info:
            await service.publish(audit_event=audit_event)

        assert "Failed to publish the audit event" in str(exc_info.value)
        assert exc_info.value.__cause__ == publisher_error  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_build_routing_key_pattern_called_with_correct_event(
        self,
        service_name: ServiceName,
        mock_publisher: AbstractPublisher[GenericMessage[MockAuditEventObject]],
        audit_event: MockAuditEventObject,
    ) -> None:
        """Test that build_routing_key_pattern is called with the correct audit event.

        Args:
            service_name (ServiceName): Service name fixture.
            mock_publisher (AbstractPublisher[GenericMessage[MockAuditEventObject]]): Mock publisher fixture.
            audit_event (MockAuditEventObject): Audit event fixture.
        """
        service = ConcreteAuditPublisherService(sender=service_name, publisher=mock_publisher)
        mock_publisher.publish = AsyncMock()

        # Spy on build_routing_key_pattern
        original_method = service.build_routing_key_pattern
        service.build_routing_key_pattern = MagicMock(side_effect=original_method)

        await service.publish(audit_event=audit_event)

        # Verify build_routing_key_pattern was called with the audit event
        service.build_routing_key_pattern.assert_called_once_with(audit_event=audit_event)

    def test_build_routing_key_pattern_implementation(
        self,
        service_name: ServiceName,
        mock_publisher: AbstractPublisher[GenericMessage[MockAuditEventObject]],
        audit_event: MockAuditEventObject,
    ) -> None:
        """Test the build_routing_key_pattern implementation.

        Args:
            service_name (ServiceName): Service name fixture.
            mock_publisher (AbstractPublisher[GenericMessage[MockAuditEventObject]]): Mock publisher fixture.
            audit_event (MockAuditEventObject): Audit event fixture.
        """
        service = ConcreteAuditPublisherService(sender=service_name, publisher=mock_publisher)

        routing_key = service.build_routing_key_pattern(audit_event=audit_event)

        expected_routing_key = f"audit.{audit_event.where}.{audit_event.what}.{audit_event.why}"
        assert routing_key == expected_routing_key
        assert isinstance(routing_key, str)

    @pytest.mark.asyncio
    async def test_publish_creates_correct_generic_message(
        self,
        service_name: ServiceName,
        mock_publisher: AbstractPublisher[GenericMessage[MockAuditEventObject]],
        audit_event: MockAuditEventObject,
    ) -> None:
        """Test that publish creates a GenericMessage with the correct data.

        Args:
            service_name (ServiceName): Service name fixture.
            mock_publisher (AbstractPublisher[GenericMessage[MockAuditEventObject]]): Mock publisher fixture.
            audit_event (MockAuditEventObject): Audit event fixture.
        """
        service = ConcreteAuditPublisherService(sender=service_name, publisher=mock_publisher)
        mock_publisher.publish = AsyncMock()

        await service.publish(audit_event=audit_event)

        call_args = mock_publisher.publish.call_args
        message: GenericMessage[MockAuditEventObject] = call_args.kwargs["message"]

        assert isinstance(message, GenericMessage)
        assert message.data == audit_event
        assert message.data.what == audit_event.what
        assert message.data.why == audit_event.why
        assert message.data.where == audit_event.where
        assert message.data.when == audit_event.when
        assert message.data.who == audit_event.who
