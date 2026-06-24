"""Message delivery outcomes and AMQP settlement helpers for managed consumers."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from .message import GenericMessage


class MessageDeliveryOutcome(StrEnum):
    """Typed delivery decision for a consumed AMQP message.

    Maps to ack / reject semantics via :func:`settle_message`:

    * ``CONTINUE`` — proceed to concurrency gate and processing (not settled here).
    * ``ACK`` — message handled without further work; ack.
    * ``REQUEUE`` — immediate redelivery; reject with ``requeue=True``.
    * ``REQUEUE_DELAYED`` — defer via dead-letter / TTL retry topology; reject with ``requeue=False``.
    """

    CONTINUE = "continue"
    ACK = "ack"
    REQUEUE = "requeue"
    REQUEUE_DELAYED = "requeue_delayed"


async def settle_message(message: GenericMessage[Any], outcome: MessageDeliveryOutcome) -> None:
    """Apply the AMQP settlement action for ``outcome``.

    Args:
        message: Validated message with an attached incoming delivery.
        outcome: Delivery decision to apply. ``CONTINUE`` is a no-op.

    Raises:
        ValueError: When the incoming message is not set on ``message``.
    """
    if outcome == MessageDeliveryOutcome.CONTINUE:
        return
    if outcome == MessageDeliveryOutcome.ACK:
        await message.ack()
        return
    if outcome == MessageDeliveryOutcome.REQUEUE:
        await message.reject(requeue=True)
        return
    if outcome == MessageDeliveryOutcome.REQUEUE_DELAYED:
        await message.reject(requeue=False)
        return
