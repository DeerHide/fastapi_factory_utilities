"""Provides the services for the audit service."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from fastapi_factory_utilities.core.plugins.aiopika import (
    AbstractPublisher,
    AiopikaPluginBaseError,
    GenericMessage,
    RoutingKey,
)

from .exceptions import AuditServiceError
from .objects import AuditEventObject, ServiceName

AuditEventGeneric = TypeVar("AuditEventGeneric", bound=AuditEventObject[Any])


class AbstractAuditPublisherService(ABC, Generic[AuditEventGeneric]):
    """Audit publisher service."""

    def __init__(self, sender: ServiceName, publisher: AbstractPublisher[GenericMessage[AuditEventGeneric]]) -> None:
        """Initialize the audit publisher service."""
        self._sender: ServiceName = sender
        self._publisher: AbstractPublisher[GenericMessage[AuditEventGeneric]] = publisher

    @abstractmethod
    def build_routing_key_pattern(self, audit_event: AuditEventGeneric) -> RoutingKey:
        """Build the routing key pattern for the audit event.

        The routing key should follow the pattern: {prefix}.{where}.{what}.{why}
        where:
        - where: The service name from audit_event.where
        - what: The entity name from audit_event.what
        - why: The functional event name from audit_event.why

        Returns:
            RoutingKey: The routing key pattern for routing the message.
        """
        raise NotImplementedError

    async def publish(self, audit_event: AuditEventGeneric) -> None:
        """Publish the audit event."""
        message: GenericMessage[AuditEventGeneric] = GenericMessage(
            data=audit_event,
        )
        routing_key: RoutingKey = self.build_routing_key_pattern(audit_event=audit_event)

        try:
            await self._publisher.publish(message=message, routing_key=routing_key)
        except AiopikaPluginBaseError as exception:
            raise AuditServiceError(
                "Failed to publish the audit event.",
                cause=exception,
                audit_event=audit_event,
                routing_key=routing_key,
            ) from exception
