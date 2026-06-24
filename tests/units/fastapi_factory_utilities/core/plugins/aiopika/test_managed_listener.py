"""Unit tests for AbstractManagedListener pipeline."""

# pylint: disable=protected-access

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, Field

from fastapi_factory_utilities.core.plugins.aiopika import AbstractManagedListener, GenericMessage
from fastapi_factory_utilities.core.plugins.aiopika.concurrency.local import LocalConcurrencyGate
from fastapi_factory_utilities.core.plugins.aiopika.delivery import MessageDeliveryOutcome
from fastapi_factory_utilities.core.plugins.aiopika.telemetry import NoOpConsumerTelemetry


class Body(BaseModel):
    """Payload for test messages."""

    msg: str = Field(description="Text.")


class Msg(GenericMessage[Body]):
    """Concrete generic message for listener typing."""


class _ManagedListener(AbstractManagedListener[Msg]):
    """Test double with configurable hooks."""

    precheck_outcome: MessageDeliveryOutcome = MessageDeliveryOutcome.CONTINUE
    process_outcome: MessageDeliveryOutcome | None = None
    process_error: Exception | None = None
    precheck_error: Exception | None = None
    process_calls: int = 0

    async def precheck(self, message: Msg) -> MessageDeliveryOutcome:
        """Return configured precheck outcome or raise a configured error."""
        if self.precheck_error is not None:
            raise self.precheck_error
        del message
        return self.precheck_outcome

    async def process_message(self, message: Msg) -> MessageDeliveryOutcome | None:
        """Return configured process outcome or raise a configured error."""
        del message
        self.process_calls += 1
        if self.process_error is not None:
            raise self.process_error
        return self.process_outcome


class TestAbstractManagedListenerPipeline:
    """Managed listener precheck, gate, and settlement paths."""

    @staticmethod
    def _incoming(body: dict[str, object]) -> MagicMock:
        incoming = MagicMock()
        incoming.body = json.dumps(body).encode("utf-8")
        incoming.headers = {}
        incoming.ack = AsyncMock()
        incoming.reject = AsyncMock()
        return incoming

    @pytest.mark.asyncio
    async def test_precheck_ack_settles_without_processing(self) -> None:
        """Precheck ACK acks immediately without calling process_message."""
        listener = _ManagedListener(queue=MagicMock(), telemetry=NoOpConsumerTelemetry())
        listener.precheck_outcome = MessageDeliveryOutcome.ACK
        incoming = self._incoming({"data": {"msg": "hello"}})

        await listener._on_message(incoming)  # type: ignore[attr-defined]

        assert listener.process_calls == 0
        incoming.ack.assert_awaited_once()
        incoming.reject.assert_not_called()

    @pytest.mark.asyncio
    async def test_precheck_requeue_delayed(self) -> None:
        """Precheck REQUEUE_DELAYED rejects without requeue."""
        listener = _ManagedListener(queue=MagicMock(), telemetry=NoOpConsumerTelemetry())
        listener.precheck_outcome = MessageDeliveryOutcome.REQUEUE_DELAYED
        incoming = self._incoming({"data": {"msg": "hello"}})

        await listener._on_message(incoming)  # type: ignore[attr-defined]

        incoming.reject.assert_awaited_once_with(requeue=False)

    @pytest.mark.asyncio
    async def test_gate_saturated_requeues(self) -> None:
        """Saturated gate rejects with requeue=True."""
        gate = LocalConcurrencyGate(telemetry=NoOpConsumerTelemetry())
        gate.configure(global_limit=1)
        release = asyncio.Event()

        class BlockingListener(_ManagedListener):
            async def process_message(self, message: Msg) -> MessageDeliveryOutcome | None:
                del message
                await release.wait()
                return None

        listener = BlockingListener(queue=MagicMock(), concurrency_gate=gate, telemetry=NoOpConsumerTelemetry())

        hold = self._incoming({"data": {"msg": "hold"}})
        hold_task = asyncio.create_task(listener._on_message(hold))  # type: ignore[attr-defined]
        await asyncio.sleep(0)

        blocked = self._incoming({"data": {"msg": "blocked"}})
        await listener._on_message(blocked)  # type: ignore[attr-defined]

        blocked.reject.assert_awaited_once_with(requeue=True)
        release.set()
        await hold_task
        hold.ack.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_success_acks(self) -> None:
        """Successful process_message settles as ACK."""
        listener = _ManagedListener(queue=MagicMock(), telemetry=NoOpConsumerTelemetry())
        incoming = self._incoming({"data": {"msg": "hello"}})

        await listener._on_message(incoming)  # type: ignore[attr-defined]

        assert listener.process_calls == 1
        incoming.ack.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_explicit_outcome(self) -> None:
        """process_message may return an explicit delivery outcome."""
        listener = _ManagedListener(queue=MagicMock(), telemetry=NoOpConsumerTelemetry())
        listener.process_outcome = MessageDeliveryOutcome.REQUEUE_DELAYED
        incoming = self._incoming({"data": {"msg": "hello"}})

        await listener._on_message(incoming)  # type: ignore[attr-defined]

        incoming.reject.assert_awaited_once_with(requeue=False)

    @pytest.mark.asyncio
    async def test_process_exception_maps_to_requeue(self) -> None:
        """Handler exceptions use map_exception_to_outcome (default REQUEUE)."""
        listener = _ManagedListener(queue=MagicMock(), telemetry=NoOpConsumerTelemetry())
        listener.process_error = RuntimeError("boom")
        incoming = self._incoming({"data": {"msg": "hello"}})

        await listener._on_message(incoming)  # type: ignore[attr-defined]

        incoming.reject.assert_awaited_once_with(requeue=True)

    @pytest.mark.asyncio
    async def test_poison_message_drop_when_requeue_disabled(self) -> None:
        """Invalid JSON is dropped when POISON_MESSAGE_REQUEUE is False."""

        class DropPoisonListener(_ManagedListener):
            POISON_MESSAGE_REQUEUE = False

        listener = DropPoisonListener(queue=MagicMock(), telemetry=NoOpConsumerTelemetry())
        incoming = self._incoming({})
        incoming.body = b"not-json"

        await listener._on_message(incoming)  # type: ignore[attr-defined]

        incoming.reject.assert_awaited_once_with(requeue=False)

    @pytest.mark.asyncio
    async def test_precheck_exception_requeues(self) -> None:
        """Precheck exceptions default to REQUEUE settlement."""
        listener = _ManagedListener(queue=MagicMock(), telemetry=NoOpConsumerTelemetry())
        listener.precheck_error = RuntimeError("precheck failed")
        incoming = self._incoming({"data": {"msg": "hello"}})

        await listener._on_message(incoming)  # type: ignore[attr-defined]

        incoming.reject.assert_awaited_once_with(requeue=True)
