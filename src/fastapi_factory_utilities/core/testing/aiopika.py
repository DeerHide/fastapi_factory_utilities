"""AMQP test doubles: record publishes; fake incoming messages for listeners.

Deliberately no broker, routing, confirms, or DLX — those stay on the RabbitMQ
testcontainer. This covers usecase assertions and ``AbstractListener._on_message``
decode / validate / reject logic only.
"""

import json
from typing import Any, Generic, TypeVar
from unittest.mock import AsyncMock, MagicMock

from aio_pika.abc import AbstractIncomingMessage, HeadersType

from fastapi_factory_utilities.core.plugins.aiopika.abstract import AbstractAiopikaResource
from fastapi_factory_utilities.core.plugins.aiopika.message import GenericMessage
from fastapi_factory_utilities.core.plugins.aiopika.publisher.abstract import AbstractPublisher
from fastapi_factory_utilities.core.plugins.aiopika.types import RoutingKey

GenericMessageType = TypeVar("GenericMessageType", bound=GenericMessage[Any])  # pylint: disable=invalid-name


class InMemoryPublisher(AbstractPublisher[GenericMessageType], Generic[GenericMessageType]):
    """Recording publisher — appends ``(message, routing_key)``; no broker I/O."""

    def __init__(self, name: str | None = None) -> None:  # pylint: disable=super-init-not-called
        """Initialize the recording publisher.

        Args:
            name: Optional publisher name (defaults to the class name).
        """
        # Skip AbstractPublisher.__init__ (needs a real Exchange).
        AbstractAiopikaResource.__init__(self)  # pylint: disable=non-parent-init-called
        self._name: str = name or self.__class__.__name__
        self._exchange = None  # type: ignore[assignment]
        self.published: list[tuple[GenericMessageType, RoutingKey]] = []

    async def setup(self) -> "InMemoryPublisher[GenericMessageType]":
        """No-op setup (no exchange declaration)."""
        return self

    async def publish(self, message: GenericMessageType, routing_key: RoutingKey) -> None:
        """Record the publish call.

        Args:
            message: Message that would be published.
            routing_key: Routing key that would be used.
        """
        self.published.append((message, routing_key))

    def clear(self) -> None:
        """Clear recorded publishes."""
        self.published.clear()


def build_incoming_message(
    body: bytes | str | dict[str, Any],
    *,
    headers: HeadersType | None = None,
) -> MagicMock:
    """Build a fake ``AbstractIncomingMessage`` with ack/reject spies.

    Args:
        body: Message body as bytes, UTF-8 str, or a JSON-serializable mapping
            (encoded as UTF-8 JSON).
        headers: Optional AMQP headers.

    Returns:
        A ``MagicMock(spec=AbstractIncomingMessage)`` with async ``ack`` / ``reject``.
    """
    if isinstance(body, dict):
        raw: bytes = json.dumps(body).encode("utf-8")
    elif isinstance(body, str):
        raw = body.encode("utf-8")
    else:
        raw = body

    incoming = MagicMock(spec=AbstractIncomingMessage)
    incoming.body = raw
    incoming.headers = headers or {}
    incoming.ack = AsyncMock()
    incoming.reject = AsyncMock()
    incoming.nack = AsyncMock()
    return incoming
