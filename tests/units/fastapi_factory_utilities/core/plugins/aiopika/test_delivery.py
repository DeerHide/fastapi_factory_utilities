"""Unit tests for message delivery outcomes and settlement."""

# pylint: disable=protected-access

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, Field

from fastapi_factory_utilities.core.plugins.aiopika.delivery import MessageDeliveryOutcome, settle_message
from fastapi_factory_utilities.core.plugins.aiopika.message import GenericMessage


class _Body(BaseModel):
    msg: str = Field(description="Text.")


class _Msg(GenericMessage[_Body]):
    pass


class TestSettleMessage:
    """settle_message AMQP mapping."""

    @staticmethod
    def _message() -> _Msg:
        message = _Msg(data=_Body(msg="hello"))
        incoming = MagicMock()
        incoming.ack = AsyncMock()
        incoming.reject = AsyncMock()
        message.set_incoming_message(incoming_message=incoming)
        return message

    @pytest.mark.asyncio
    async def test_continue_is_no_op(self) -> None:
        """CONTINUE does not ack or reject."""
        message = self._message()
        await settle_message(message, MessageDeliveryOutcome.CONTINUE)
        message._incoming_message.ack.assert_not_called()  # type: ignore[attr-defined, union-attr]
        message._incoming_message.reject.assert_not_called()  # type: ignore[attr-defined, union-attr]

    @pytest.mark.asyncio
    async def test_ack(self) -> None:
        """ACK calls message.ack()."""
        message = self._message()
        await settle_message(message, MessageDeliveryOutcome.ACK)
        message._incoming_message.ack.assert_awaited_once()  # type: ignore[attr-defined, union-attr]

    @pytest.mark.asyncio
    async def test_requeue(self) -> None:
        """REQUEUE rejects with requeue=True."""
        message = self._message()
        await settle_message(message, MessageDeliveryOutcome.REQUEUE)
        incoming = message._incoming_message
        assert incoming is not None
        incoming.reject.assert_awaited_once_with(requeue=True)

    @pytest.mark.asyncio
    async def test_requeue_delayed(self) -> None:
        """REQUEUE_DELAYED rejects with requeue=False."""
        message = self._message()
        await settle_message(message, MessageDeliveryOutcome.REQUEUE_DELAYED)
        incoming = message._incoming_message
        assert incoming is not None
        incoming.reject.assert_awaited_once_with(requeue=False)
