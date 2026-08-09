"""Unit tests for AMQP recording doubles."""

import json
from unittest.mock import MagicMock

from pydantic import BaseModel, Field

from fastapi_factory_utilities.core.plugins.aiopika.listener.abstract import AbstractListener
from fastapi_factory_utilities.core.plugins.aiopika.message import GenericMessage
from fastapi_factory_utilities.core.plugins.aiopika.types import RoutingKey
from fastapi_factory_utilities.core.testing.aiopika import InMemoryPublisher, build_incoming_message


class _Payload(BaseModel):
    """Minimal message payload."""

    value: str = Field(default="x")


class _Message(GenericMessage[_Payload]):
    """Minimal GenericMessage for tests."""


class _Listener(AbstractListener[_Message]):
    """Listener that records successfully decoded messages."""

    def __init__(self) -> None:  # pylint: disable=super-init-not-called
        """Initialize without a real queue."""
        # ponytail: skip AbstractListener.__init__ (needs Exchange-bound Queue).
        # _on_message only uses _message_type; listen()/setup() still need a broker.
        self._name = self.__class__.__name__
        self._queue = MagicMock()
        self._consumer_tag = None
        self._exclusive = False
        self._message_type = _Message
        self.received: list[_Message] = []

    async def on_message(self, message: _Message) -> None:
        """Record the message."""
        self.received.append(message)


class TestInMemoryPublisher:
    """Tests for InMemoryPublisher."""

    async def test_publish_records_message_and_routing_key(self) -> None:
        """Publish appends to published without broker I/O."""
        publisher: InMemoryPublisher[_Message] = InMemoryPublisher()
        message = _Message(data=_Payload(value="hello"))
        routing_key = RoutingKey("audit.domain.svc.create.user")
        await publisher.setup()
        await publisher.publish(message=message, routing_key=routing_key)
        assert len(publisher.published) == 1
        assert publisher.published[0][0] is message
        assert publisher.published[0][1] == routing_key

    async def test_clear(self) -> None:
        """Clear empties the recorded list."""
        publisher: InMemoryPublisher[_Message] = InMemoryPublisher()
        await publisher.publish(
            message=_Message(data=_Payload()),
            routing_key=RoutingKey("audit.domain.svc.create.user"),
        )
        publisher.clear()
        assert not publisher.published


class TestBuildIncomingMessage:
    """Tests for build_incoming_message."""

    async def test_dict_body_encoded_as_json(self) -> None:
        """Dict bodies are JSON-encoded for listener decode."""
        incoming = build_incoming_message({"data": {"value": "ok"}})
        assert json.loads(incoming.body.decode("utf-8")) == {"data": {"value": "ok"}}

    async def test_listener_rejects_invalid_json(self) -> None:
        """Malformed JSON is rejected with requeue=False."""
        listener = _Listener()
        incoming = build_incoming_message(b"not-json{")
        await listener._on_message(incoming)  # pylint: disable=protected-access
        incoming.reject.assert_awaited_once_with(requeue=False)
        assert not listener.received

    async def test_listener_rejects_schema_mismatch(self) -> None:
        """Schema mismatch is rejected with requeue=False."""
        listener = _Listener()
        incoming = build_incoming_message({"data": {"value": 123}})  # value must be str
        await listener._on_message(incoming)  # pylint: disable=protected-access
        incoming.reject.assert_awaited_once_with(requeue=False)
        assert not listener.received

    async def test_listener_accepts_valid_message(self) -> None:
        """Valid JSON + schema reaches on_message."""
        listener = _Listener()
        incoming = build_incoming_message({"data": {"value": "ok"}})
        await listener._on_message(incoming)  # pylint: disable=protected-access
        incoming.reject.assert_not_awaited()
        assert len(listener.received) == 1
        assert listener.received[0].data.value == "ok"
