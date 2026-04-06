"""Unit tests for GenericMessage."""

import json
from unittest.mock import AsyncMock

import pytest
from aio_pika.abc import DeliveryMode
from pydantic import BaseModel, ValidationError

from fastapi_factory_utilities.core.plugins.aiopika.message import GenericMessage


class BodyForTest(BaseModel):
    """Payload model for tests."""

    title: str


class TestGenericMessage:
    """Tests for GenericMessage."""

    def test_rejects_extra_fields(self) -> None:
        """Model is closed to unknown keys."""
        with pytest.raises(ValidationError):
            GenericMessage[BodyForTest](data=BodyForTest(title="x"), extra_field=1)  # type: ignore[call-arg]

    def test_to_aiopika_message_json_body_and_headers(self) -> None:
        """Published message carries JSON body and headers."""
        msg = GenericMessage[BodyForTest](data=BodyForTest(title="hello"))
        msg.set_headers({"x-trace": "abc"})
        amqp = msg.to_aiopika_message()
        payload = json.loads(amqp.body.decode("utf-8"))
        assert payload == {"data": {"title": "hello"}}
        assert amqp.headers == {"x-trace": "abc"}
        assert amqp.content_type == "application/json"
        assert amqp.delivery_mode == DeliveryMode.PERSISTENT

    def test_set_incoming_message_copies_headers(self) -> None:
        """Binding incoming aio_pika message copies headers onto the wrapper."""
        incoming = AsyncMock()
        incoming.headers = {"h": "v"}
        msg = GenericMessage[BodyForTest](data=BodyForTest(title="a"))
        msg.set_incoming_message(incoming)
        assert msg.get_headers() == {"h": "v"}

    @pytest.mark.asyncio
    async def test_ack_without_incoming_raises(self) -> None:
        """Ack requires an incoming message reference."""
        msg = GenericMessage[BodyForTest](data=BodyForTest(title="a"))
        with pytest.raises(ValueError, match="Incoming message is not set"):
            await msg.ack()

    @pytest.mark.asyncio
    async def test_ack_delegates(self) -> None:
        """Ack forwards to the underlying incoming message."""
        incoming = AsyncMock()
        msg = GenericMessage[BodyForTest](data=BodyForTest(title="a"))
        msg.set_incoming_message(incoming)
        await msg.ack()
        incoming.ack.assert_awaited_once_with(multiple=False)

    @pytest.mark.asyncio
    async def test_reject_delegates(self) -> None:
        """Reject forwards requeue flag."""
        incoming = AsyncMock()
        msg = GenericMessage[BodyForTest](data=BodyForTest(title="a"))
        msg.set_incoming_message(incoming)
        await msg.reject(requeue=False)
        incoming.reject.assert_awaited_once_with(requeue=False)
