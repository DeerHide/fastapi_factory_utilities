"""Provides the services for the audit service."""

from abc import ABC
from typing import Any, ClassVar, Generic, Self, TypeVar

from aio_pika.abc import AbstractRobustConnection, ExchangeType

from fastapi_factory_utilities.core.plugins.aiopika import (
    AbstractListener,
    AbstractPublisher,
    AiopikaPluginBaseError,
    EventRoutingKeyBuilder,
    Exchange,
    ExchangeName,
    GenericMessage,
    PartStr,
    RoutingKey,
)

from .exceptions import AuditServiceError
from .objects import AuditableEntity, AuditEventObject, DomainName, EntityName, ServiceName

AuditEventGeneric = TypeVar("AuditEventGeneric", bound=AuditEventObject[AuditableEntity[Any]])


class AbstractAuditPublisherService(
    AbstractPublisher[GenericMessage[AuditEventGeneric]], ABC, Generic[AuditEventGeneric]
):
    """Audit publisher service."""

    EXCHANGE_NAME: ClassVar[ExchangeName] = ExchangeName("default")
    EXCHANGE_TYPE: ClassVar[ExchangeType] = ExchangeType.TOPIC

    ROUTING_KEY_PREFIX: ClassVar[PartStr] = PartStr("all")
    ROUTING_KEY_DOMAIN_NAME: ClassVar[DomainName] = DomainName(PartStr("default"))
    ROUTING_KEY_SERVICE_NAME: ClassVar[ServiceName] = ServiceName(PartStr("default"))
    ROUTING_KEY_ENTITY_NAME: ClassVar[EntityName] = EntityName(PartStr("default"))

    def __init__(self, sender: ServiceName) -> None:
        """Initialize the audit publisher service."""
        self._exchange: Exchange = self.build_exchange()
        super().__init__(exchange=self._exchange)
        self._sender: ServiceName = sender

    def build_exchange(self) -> Exchange:
        """Build the exchange."""
        return Exchange(
            name=self.EXCHANGE_NAME,
            exchange_type=self.EXCHANGE_TYPE,
            durable=True,
            auto_delete=False,
            internal=False,
            passive=False,
        )

    def build_routing_key_pattern(self, audit_event: AuditEventGeneric) -> RoutingKey:
        """Return ``{prefix}.{domain}.{service}.{entity}.{functional_event}``."""
        builder: EventRoutingKeyBuilder = EventRoutingKeyBuilder(prefix=self.ROUTING_KEY_PREFIX)
        builder.set_domain_name(str(self.ROUTING_KEY_DOMAIN_NAME))
        builder.set_service_name(str(self.ROUTING_KEY_SERVICE_NAME))
        builder.set_entity_name(str(self.ROUTING_KEY_ENTITY_NAME))
        builder.set_functional_event_name(str(audit_event.why))
        return builder.build()

    async def publish(self, message: GenericMessage[AuditEventGeneric], routing_key: RoutingKey) -> None:
        """Publish the audit event."""
        # Filter the entity to expurgate sensitive data
        message.data.entity = message.data.pre_publish_hook(message.data.entity)

        try:
            await super().publish(message=message, routing_key=routing_key)
        except AiopikaPluginBaseError as exception:
            raise AuditServiceError(
                "Failed to publish the audit event.",
                cause=exception,
                audit_event=message.data,
                routing_key=routing_key,
            ) from exception

    def set_robust_connection(self, robust_connection: AbstractRobustConnection) -> Self:
        """Set the robust connection."""
        self._exchange.set_robust_connection(robust_connection)
        return super().set_robust_connection(robust_connection)

    async def setup(self) -> Self:
        """Setup the audit publisher service."""
        return await super().setup()


class AbstractAuditListenerService(
    AbstractListener[GenericMessage[AuditEventGeneric]], ABC, Generic[AuditEventGeneric]
):
    """Audit listener service."""
