"""Provides the builders for the Aiopika plugin."""

from abc import ABC, abstractmethod
from typing import Self

from .types import ExchangeName, PartStr, QueueName, RoutingKey


class AbstractEventRoutingKeyBuilder(ABC):
    """Abstract event routing key builder."""

    def __init__(self, prefix: PartStr | None = None) -> None:
        """Initialize the event routing key builder."""
        self._prefix: PartStr | None = None if prefix is None else PartStr(prefix)
        self._domain_name: PartStr = PartStr("domain")
        self._service_name: PartStr = PartStr("service")
        self._entity_name: PartStr = PartStr("entity")
        self._functional_event_name: PartStr = PartStr("functional_event")

    # Setters ================================================================

    def set_prefix(self, prefix: str) -> Self:
        """Set the prefix."""
        self._prefix = PartStr(prefix)
        return self

    def set_domain_name(self, domain_name: str) -> Self:
        """Set the domain name."""
        self._domain_name = PartStr(domain_name)
        return self

    def set_service_name(self, service_name: str) -> Self:
        """Set the service name."""
        self._service_name = PartStr(service_name)
        return self

    def set_entity_name(self, entity_name: str) -> Self:
        """Set the entity name."""
        self._entity_name = PartStr(entity_name)
        return self

    def set_functional_event_name(self, functional_event_name: str) -> Self:
        """Set the functional event name."""
        self._functional_event_name = PartStr(functional_event_name)
        return self

    # Builders ================================================================

    @abstractmethod
    def build(self) -> RoutingKey:
        """Build the routing key."""
        raise NotImplementedError


class EventRoutingKeyBuilder(AbstractEventRoutingKeyBuilder):
    """Event routing key builder."""

    # Builders ================================================================

    def build(self) -> RoutingKey:
        """Build the routing key."""
        parts: list[PartStr] = []
        if self._prefix is not None:
            parts.append(self._prefix)
        parts.append(self._domain_name)
        parts.append(self._service_name)
        parts.append(self._entity_name)
        parts.append(self._functional_event_name)
        return RoutingKey(".".join(parts))


class ListenerRoutingKeyBuilder(EventRoutingKeyBuilder):
    """Listener routing key builder."""

    def __init__(self, prefix: PartStr | None = None) -> None:
        """Initialize the listener routing key builder."""
        super().__init__(prefix=prefix)
        self._domain_name: PartStr = PartStr("*")
        self._service_name: PartStr = PartStr("*")
        self._entity_name: PartStr = PartStr("*")
        self._functional_event_name: PartStr = PartStr("*")


class QueueNameBuilder:
    """Abstract queue name builder."""

    def __init__(self, prefix: str | None = None) -> None:
        """Initialize the queue name builder."""
        self._prefix: PartStr | None = None if prefix is None else PartStr(prefix)
        self._domain_name: PartStr | None = None
        self._service_name: PartStr | None = None
        self._entity_name: PartStr | None = None
        self._functional_queue_name: PartStr | None = None

    # Setters ================================================================

    def set_prefix(self, prefix: str) -> Self:
        """Set the prefix."""
        self._prefix = PartStr(prefix)
        return self

    def set_domain_name(self, domain_name: str) -> Self:
        """Set the domain name."""
        self._domain_name = PartStr(domain_name)
        return self

    def set_service_name(self, service_name: str) -> Self:
        """Set the service name."""
        self._service_name = PartStr(service_name)
        return self

    def set_entity_name(self, entity_name: str) -> Self:
        """Set the entity name."""
        self._entity_name = PartStr(entity_name)
        return self

    def set_functional_queue_name(self, functional_queue_name: str) -> Self:
        """Set the functional queue name."""
        self._functional_queue_name = PartStr(functional_queue_name)
        return self

    # Builders ================================================================

    def build(self) -> QueueName:
        """Build the queue name."""
        parts: list[PartStr] = []
        if self._prefix is not None:
            parts.append(self._prefix)
        if self._domain_name is not None:
            parts.append(self._domain_name)
        if self._service_name is not None:
            parts.append(self._service_name)
        if self._entity_name is not None:
            parts.append(self._entity_name)
        if self._functional_queue_name is not None:
            parts.append(self._functional_queue_name)
        return QueueName(".".join(parts))


class ExchangeNameBuilder:
    """Exchange name builder."""

    def __init__(self, prefix: str | None = None) -> None:
        """Initialize the exchange name builder."""
        self._prefix: PartStr | None = None if prefix is None else PartStr(prefix)
        self._domain_name: PartStr | None = None
        self._service_name: PartStr | None = None

    # Setters ================================================================

    def set_prefix(self, prefix: str) -> Self:
        """Set the prefix."""
        self._prefix = PartStr(prefix)
        return self

    def set_domain_name(self, domain_name: str) -> Self:
        """Set the domain name."""
        self._domain_name = PartStr(domain_name)
        return self

    def set_service_name(self, service_name: str) -> Self:
        """Set the service name."""
        self._service_name = PartStr(service_name)
        return self

    # Builders ================================================================

    def build(self) -> ExchangeName:
        """Build the exchange name."""
        parts: list[PartStr] = []
        if self._prefix is not None:
            parts.append(self._prefix)
        if self._domain_name is not None:
            parts.append(self._domain_name)
        if self._service_name is not None:
            parts.append(self._service_name)
        if len(parts) == 0:
            return ExchangeName(PartStr("default"))
        return ExchangeName(".".join(parts))
