"""Unit tests for AbstractListener."""

# pylint: disable=protected-access  # white-box tests for AbstractListener lifecycle and parsing

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, Field

from fastapi_factory_utilities.core.plugins.aiopika import AbstractListener, GenericMessage


class Body(BaseModel):
    """Payload for test messages."""

    msg: str = Field(description="Text.")


class Msg(GenericMessage[Body]):
    """Concrete generic message for listener typing."""


class _RecordingListener(AbstractListener[Msg]):
    """Minimal listener implementation for tests."""

    def __init__(
        self,
        queue: MagicMock,
        name: str | None = None,
        exclusive: bool | None = None,
    ) -> None:
        super().__init__(queue=queue, name=name, exclusive=exclusive)
        self.on_calls: list[Msg] = []

    async def on_message(self, message: Msg) -> None:
        self.on_calls.append(message)


class TestAbstractListenerInit:
    """Construction and generic typing."""

    def test_default_name_is_class_name(self) -> None:
        """Default listener name falls back to the concrete class name."""
        queue_resource = MagicMock()
        listener = _RecordingListener(queue=queue_resource)
        assert listener._name == "_RecordingListener"  # type: ignore[attr-defined]

    def test_custom_name(self) -> None:
        """Optional name is stored when provided."""
        queue_resource = MagicMock()
        listener = _RecordingListener(queue=queue_resource, name="orders")
        assert listener._name == "orders"  # type: ignore[attr-defined]

    def test_message_type_from_generic_arg(self) -> None:
        """Generic parameter resolves to the Pydantic message model."""
        queue_resource = MagicMock()
        listener = _RecordingListener(queue=queue_resource)
        assert listener._message_type is Msg  # type: ignore[attr-defined]


class TestAbstractListenerLifecycle:
    """setup, listen, and close."""

    @pytest.mark.asyncio
    async def test_setup_awaits_queue_setup(self) -> None:
        """Setup delegates to the bound queue after acquiring a channel."""
        queue_resource = MagicMock()
        queue_resource.setup = AsyncMock(return_value=queue_resource)
        listener = _RecordingListener(queue=queue_resource)
        listener._channel = MagicMock()  # type: ignore[attr-defined]

        result = await listener.setup()

        assert result is listener
        queue_resource.setup.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_listen_registers_exclusive_consumer(self) -> None:
        """Listen subscribes with an exclusive consumer when the queue is exclusive."""
        aiopika_queue = MagicMock()
        aiopika_queue.consume = AsyncMock(return_value="ctag-1")
        queue_resource = MagicMock()
        queue_resource.exclusive = True
        queue_resource.queue = aiopika_queue
        listener = _RecordingListener(queue=queue_resource)

        await listener.listen()

        aiopika_queue.consume.assert_awaited_once()
        assert aiopika_queue.consume.await_args.kwargs["exclusive"] is True
        assert listener._consumer_tag == "ctag-1"  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_listen_respects_queue_exclusive_false(self) -> None:
        """Listen passes exclusive=False when the queue resource is not exclusive."""
        aiopika_queue = MagicMock()
        aiopika_queue.consume = AsyncMock(return_value="ctag-2")
        queue_resource = MagicMock()
        queue_resource.exclusive = False
        queue_resource.queue = aiopika_queue
        listener = _RecordingListener(queue=queue_resource)

        await listener.listen()

        assert aiopika_queue.consume.await_args.kwargs["exclusive"] is False

    @pytest.mark.asyncio
    async def test_listen_exclusive_constructor_overrides_queue(self) -> None:
        """Optional listener exclusive flag overrides the queue default."""
        aiopika_queue = MagicMock()
        aiopika_queue.consume = AsyncMock(return_value="ctag-3")
        queue_resource = MagicMock()
        queue_resource.exclusive = False
        queue_resource.queue = aiopika_queue
        listener = _RecordingListener(queue=queue_resource, exclusive=True)

        await listener.listen()

        assert aiopika_queue.consume.await_args.kwargs["exclusive"] is True

    @pytest.mark.asyncio
    async def test_listen_exclusive_false_overrides_exclusive_queue(self) -> None:
        """Explicit exclusive=False overrides an exclusive queue."""
        aiopika_queue = MagicMock()
        aiopika_queue.consume = AsyncMock(return_value="ctag-4")
        queue_resource = MagicMock()
        queue_resource.exclusive = True
        queue_resource.queue = aiopika_queue
        listener = _RecordingListener(queue=queue_resource, exclusive=False)

        await listener.listen()

        assert aiopika_queue.consume.await_args.kwargs["exclusive"] is False

    @pytest.mark.asyncio
    async def test_close_cancels_when_consumer_tag_set(self) -> None:
        """Close cancels the AMQP consumer when a tag was assigned."""
        aiopika_queue = MagicMock()
        aiopika_queue.cancel = AsyncMock()
        queue_resource = MagicMock()
        queue_resource.queue = aiopika_queue
        listener = _RecordingListener(queue=queue_resource)
        listener._consumer_tag = "ctag-1"  # type: ignore[attr-defined]

        await listener.close()

        aiopika_queue.cancel.assert_awaited_once_with(consumer_tag="ctag-1")

    @pytest.mark.asyncio
    async def test_close_skips_cancel_without_consumer_tag(self) -> None:
        """Close is a no-op on the broker when nothing has consumed yet."""
        aiopika_queue = MagicMock()
        aiopika_queue.cancel = AsyncMock()
        queue_resource = MagicMock()
        queue_resource.queue = aiopika_queue
        listener = _RecordingListener(queue=queue_resource)
        listener._consumer_tag = None  # type: ignore[attr-defined]

        await listener.close()

        aiopika_queue.cancel.assert_not_called()


class TestAbstractListenerOnMessage:
    """_on_message decode, validate, and dispatch."""

    @staticmethod
    def _incoming(body_bytes: bytes) -> MagicMock:
        """Build a minimal incoming delivery mock with async reject."""
        incoming = MagicMock()
        incoming.body = body_bytes
        incoming.headers = {}
        incoming.reject = AsyncMock()
        return incoming

    @pytest.mark.asyncio
    async def test_success_dispatches_on_message(self) -> None:
        """Valid JSON is validated, enriched, and passed to on_message."""
        queue_resource = MagicMock()
        listener = _RecordingListener(queue=queue_resource)
        payload = {"data": {"msg": "hello"}}
        incoming = self._incoming(json.dumps(payload).encode("utf-8"))

        await listener._on_message(incoming)  # type: ignore[attr-defined]

        assert len(listener.on_calls) == 1
        assert listener.on_calls[0].data.msg == "hello"
        incoming.reject.assert_not_called()

    @pytest.mark.asyncio
    async def test_json_decode_error_rejects_requeue(self) -> None:
        """Invalid JSON triggers reject with requeue."""
        queue_resource = MagicMock()
        listener = _RecordingListener(queue=queue_resource)
        incoming = self._incoming(b"not-json{")

        await listener._on_message(incoming)  # type: ignore[attr-defined]

        assert not listener.on_calls
        incoming.reject.assert_awaited_once_with(requeue=True)

    @pytest.mark.asyncio
    async def test_non_json_decode_failure_rejects_requeue(self) -> None:
        """Non-decodable UTF-8 body triggers reject with requeue."""
        queue_resource = MagicMock()
        listener = _RecordingListener(queue=queue_resource)
        incoming = self._incoming(b"\xff\xfe")

        await listener._on_message(incoming)  # type: ignore[attr-defined]

        assert not listener.on_calls
        incoming.reject.assert_awaited_once_with(requeue=True)

    @pytest.mark.asyncio
    async def test_validation_error_rejects_requeue(self) -> None:
        """Schema validation failure triggers reject with requeue."""
        queue_resource = MagicMock()
        listener = _RecordingListener(queue=queue_resource)
        incoming = self._incoming(json.dumps({"data": {}}).encode("utf-8"))

        await listener._on_message(incoming)  # type: ignore[attr-defined]

        assert not listener.on_calls
        incoming.reject.assert_awaited_once_with(requeue=True)
