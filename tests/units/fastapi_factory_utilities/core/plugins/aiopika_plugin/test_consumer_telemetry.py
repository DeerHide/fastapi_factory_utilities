"""Unit tests for ConsumerTelemetry facades."""

# pylint: disable=protected-access

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from opentelemetry.trace import Span
from pydantic import BaseModel, Field

from fastapi_factory_utilities.core.plugins.aiopika_plugin import AbstractManagedListener, GenericMessage
from fastapi_factory_utilities.core.plugins.aiopika_plugin.concurrency.local import LocalConcurrencyGate
from fastapi_factory_utilities.core.plugins.aiopika_plugin.delivery import MessageDeliveryOutcome
from fastapi_factory_utilities.core.plugins.aiopika_plugin.telemetry import (
    PHASE_GATE,
    PHASE_PRECHECK,
    PHASE_PROCESS,
    SCOPE_GLOBAL,
    ConsumerTelemetry,
    NoOpConsumerTelemetry,
    OpenTelemetryConsumerTelemetry,
    ProcessDurationTracker,
    TracePhase,
    mark_span_error,
)


class _Body(BaseModel):
    msg: str = Field(description="Text.")


class _Msg(GenericMessage[_Body]):
    pass


class RecordingTelemetry(ConsumerTelemetry):
    """In-memory telemetry recorder for assertions."""

    def __init__(self) -> None:
        """Initialize empty event lists."""
        self.settlements: list[tuple[str, MessageDeliveryOutcome, str]] = []
        self.saturated: list[tuple[str, str, str]] = []
        self.acquires: list[tuple[str, str, bool]] = []
        self.in_flight: list[tuple[str, str, int]] = []
        self.durations: list[tuple[str, MessageDeliveryOutcome, float]] = []

    def record_settlement(
        self,
        *,
        listener: str,
        outcome: MessageDeliveryOutcome,
        phase: str,
    ) -> None:
        """Append a settlement event."""
        self.settlements.append((listener, outcome, phase))

    def record_gate_saturated(
        self,
        *,
        listener: str,
        backend: str,
        scope: str,
    ) -> None:
        """Append a gate saturation event."""
        self.saturated.append((listener, backend, scope))

    def record_gate_acquire(
        self,
        *,
        listener: str,
        backend: str,
        acquired: bool,
    ) -> None:
        """Append a gate acquire event."""
        self.acquires.append((listener, backend, acquired))

    def record_in_flight_delta(
        self,
        *,
        listener: str,
        backend: str,
        delta: int,
    ) -> None:
        """Append an in-flight delta event."""
        self.in_flight.append((listener, backend, delta))

    def record_process_duration(
        self,
        *,
        listener: str,
        outcome: MessageDeliveryOutcome,
        duration_seconds: float,
    ) -> None:
        """Append a process duration event."""
        self.durations.append((listener, outcome, duration_seconds))

    @contextmanager
    def trace_message(self, *, listener: str, queue: str) -> Iterator[Span]:
        """Yield a mock span."""
        del listener, queue
        yield MagicMock(spec=Span)

    @contextmanager
    def trace_phase(self, *, listener: str, phase: TracePhase) -> Iterator[Span]:
        """Yield a mock span."""
        del listener, phase
        yield MagicMock(spec=Span)


class TestNoOpConsumerTelemetry:
    """NoOpConsumerTelemetry does not raise."""

    def test_methods_are_no_op(self) -> None:
        """All recording methods accept calls silently."""
        telemetry = NoOpConsumerTelemetry()
        telemetry.record_settlement(
            listener="l",
            outcome=MessageDeliveryOutcome.ACK,
            phase=PHASE_PRECHECK,
        )
        telemetry.record_gate_saturated(listener="l", backend="local", scope=SCOPE_GLOBAL)
        telemetry.record_gate_acquire(listener="l", backend="local", acquired=False)
        telemetry.record_in_flight_delta(listener="l", backend="local", delta=1)
        telemetry.record_process_duration(
            listener="l",
            outcome=MessageDeliveryOutcome.ACK,
            duration_seconds=0.1,
        )
        with telemetry.trace_message(listener="l", queue="q") as span:
            assert span is not None
        with telemetry.trace_phase(listener="l", phase="precheck") as span:
            assert span is not None


class TestRecordingTelemetryIntegration:
    """Telemetry hooks invoked by managed listener and gate."""

    @pytest.mark.asyncio
    async def test_precheck_ack_records_settlement(self) -> None:
        """Precheck ACK emits a precheck-phase settlement event."""
        telemetry = RecordingTelemetry()

        class Listener(AbstractManagedListener[_Msg]):
            async def precheck(self, message: _Msg) -> MessageDeliveryOutcome:
                del message
                return MessageDeliveryOutcome.ACK

            async def process_message(self, message: _Msg) -> MessageDeliveryOutcome | None:
                del message
                return None

        listener = Listener(queue=MagicMock(), telemetry=telemetry)
        message = _Msg(data=_Body(msg="x"))
        incoming = MagicMock()
        incoming.ack = AsyncMock()
        message.set_incoming_message(incoming_message=incoming)

        await listener.on_message(message)

        assert telemetry.settlements == [("Listener", MessageDeliveryOutcome.ACK, PHASE_PRECHECK)]

    @pytest.mark.asyncio
    async def test_gate_saturated_records_events(self) -> None:
        """Gate saturation records saturated + gate settlement events."""
        telemetry = RecordingTelemetry()
        gate = LocalConcurrencyGate(telemetry=telemetry)
        gate.configure(global_limit=1)
        release = asyncio.Event()

        class Listener(AbstractManagedListener[_Msg]):
            async def process_message(self, message: _Msg) -> MessageDeliveryOutcome | None:
                del message
                await release.wait()
                return None

        listener = Listener(queue=MagicMock(), concurrency_gate=gate, telemetry=telemetry)

        hold_message = _Msg(data=_Body(msg="hold"))
        hold_incoming = MagicMock()
        hold_incoming.ack = AsyncMock()
        hold_message.set_incoming_message(incoming_message=hold_incoming)
        hold_task = asyncio.create_task(listener.on_message(hold_message))
        await asyncio.sleep(0)

        blocked = _Msg(data=_Body(msg="blocked"))
        blocked_incoming = MagicMock()
        blocked_incoming.reject = AsyncMock()
        blocked.set_incoming_message(incoming_message=blocked_incoming)
        await listener.on_message(blocked)

        release.set()
        await hold_task

        assert (listener._name, "local", SCOPE_GLOBAL) in telemetry.saturated
        assert (listener._name, MessageDeliveryOutcome.REQUEUE, PHASE_GATE) in telemetry.settlements

    @pytest.mark.asyncio
    async def test_process_success_records_duration(self) -> None:
        """Successful processing records process settlement and duration."""
        telemetry = RecordingTelemetry()

        class Listener(AbstractManagedListener[_Msg]):
            async def process_message(self, message: _Msg) -> MessageDeliveryOutcome | None:
                del message
                return None

        listener = Listener(queue=MagicMock(), telemetry=telemetry)
        message = _Msg(data=_Body(msg="x"))
        incoming = MagicMock()
        incoming.ack = AsyncMock()
        message.set_incoming_message(incoming_message=incoming)

        await listener.on_message(message)

        assert telemetry.settlements[-1] == (listener._name, MessageDeliveryOutcome.ACK, PHASE_PROCESS)
        assert telemetry.durations
        assert telemetry.durations[-1][0] == listener._name
        assert telemetry.durations[-1][1] == MessageDeliveryOutcome.ACK


class TestOpenTelemetryConsumerTelemetry:
    """OpenTelemetryConsumerTelemetry writes to module-level instruments."""

    def test_record_settlement_adds_counter(self) -> None:
        """Settlement increments the settled counter."""
        telemetry = OpenTelemetryConsumerTelemetry()
        with patch(
            "fastapi_factory_utilities.core.plugins.aiopika_plugin.telemetry.CONSUMER_MESSAGE_SETTLED",
        ) as counter:
            telemetry.record_settlement(
                listener="L",
                outcome=MessageDeliveryOutcome.ACK,
                phase=PHASE_PROCESS,
            )
            counter.add.assert_called_once()

    def test_record_gate_saturated_adds_counter(self) -> None:
        """Saturation increments the saturated counter."""
        telemetry = OpenTelemetryConsumerTelemetry()
        with patch(
            "fastapi_factory_utilities.core.plugins.aiopika_plugin.telemetry.CONSUMER_GATE_SATURATED",
        ) as counter:
            telemetry.record_gate_saturated(listener="L", backend="local", scope=SCOPE_GLOBAL)
            counter.add.assert_called_once()

    def test_record_gate_acquire_is_noop_when_not_acquired(self) -> None:
        """A failed acquire does not touch instruments."""
        telemetry = OpenTelemetryConsumerTelemetry()
        telemetry.record_gate_acquire(listener="L", backend="local", acquired=False)

    def test_record_gate_acquire_when_acquired(self) -> None:
        """A successful acquire is currently a no-op (counter reserved)."""
        telemetry = OpenTelemetryConsumerTelemetry()
        telemetry.record_gate_acquire(listener="L", backend="local", acquired=True)

    def test_record_in_flight_delta_and_duration(self) -> None:
        """In-flight gauge and process histogram are written."""
        telemetry = OpenTelemetryConsumerTelemetry()
        with (
            patch(
                "fastapi_factory_utilities.core.plugins.aiopika_plugin.telemetry.CONSUMER_GATE_IN_FLIGHT",
            ) as gauge,
            patch(
                "fastapi_factory_utilities.core.plugins.aiopika_plugin.telemetry.CONSUMER_PROCESS_DURATION",
            ) as histogram,
        ):
            telemetry.record_in_flight_delta(listener="L", backend="local", delta=1)
            telemetry.record_process_duration(
                listener="L",
                outcome=MessageDeliveryOutcome.ACK,
                duration_seconds=0.05,
            )
            gauge.add.assert_called_once()
            histogram.record.assert_called_once()

    def test_trace_message_and_phase_yield_spans(self) -> None:
        """trace_message / trace_phase start spans on the module tracer."""
        telemetry = OpenTelemetryConsumerTelemetry()
        span = MagicMock()
        with patch(
            "fastapi_factory_utilities.core.plugins.aiopika_plugin.telemetry.TRACER",
        ) as tracer:
            tracer.start_as_current_span.return_value.__enter__.return_value = span
            with telemetry.trace_message(listener="L", queue="q") as yielded:
                assert yielded is span
            with telemetry.trace_phase(listener="L", phase="process") as yielded:
                assert yielded is span

    def test_mark_span_error_records_exception(self) -> None:
        """mark_span_error sets error status on the span."""
        span = MagicMock()
        mark_span_error(span, RuntimeError("boom"))
        span.record_exception.assert_called_once()
        span.set_status.assert_called_once()

    def test_process_duration_tracker_elapsed_is_non_negative(self) -> None:
        """ProcessDurationTracker reports elapsed seconds."""
        tracker = ProcessDurationTracker()
        assert tracker.elapsed_seconds() >= 0
