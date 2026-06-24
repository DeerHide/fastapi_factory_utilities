"""OpenTelemetry instrumentation for managed AioPika consumers."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final, Literal

from opentelemetry import metrics, trace
from opentelemetry.trace import Span, Status, StatusCode

from .delivery import MessageDeliveryOutcome

__all__: list[str] = [
    "ATTR_BACKEND",
    "ATTR_LISTENER",
    "ATTR_OUTCOME",
    "ATTR_PHASE",
    "ATTR_QUEUE",
    "ATTR_SCOPE",
    "CONSUMER_GATE_IN_FLIGHT",
    "CONSUMER_GATE_SATURATED",
    "CONSUMER_MESSAGE_SETTLED",
    "CONSUMER_PROCESS_DURATION",
    "METER",
    "PHASE_ERROR",
    "PHASE_GATE",
    "PHASE_POISON",
    "PHASE_PRECHECK",
    "PHASE_PROCESS",
    "SCOPE_GLOBAL",
    "SCOPE_LISTENER",
    "TRACER",
    "ConsumerTelemetry",
    "NoOpConsumerTelemetry",
    "OpenTelemetryConsumerTelemetry",
]

INSTRUMENTING_MODULE_NAME: Final[str] = "fastapi_factory_utilities.plugins.aiopika.consumer"

TRACER: Final[trace.Tracer] = trace.get_tracer(INSTRUMENTING_MODULE_NAME)
METER: Final[metrics.Meter] = metrics.get_meter(INSTRUMENTING_MODULE_NAME)

CONSUMER_MESSAGE_SETTLED: Final[metrics.Counter] = METER.create_counter(
    name="aiopika.consumer.message.settled",
    unit="1",
    description="Managed consumer messages settled with a delivery outcome.",
)

CONSUMER_GATE_SATURATED: Final[metrics.Counter] = METER.create_counter(
    name="aiopika.consumer.gate.saturated",
    unit="1",
    description="Managed consumer gate rejections due to concurrency saturation.",
)

CONSUMER_PROCESS_DURATION: Final[metrics.Histogram] = METER.create_histogram(
    name="aiopika.consumer.process.duration",
    unit="s",
    description="Duration of managed consumer process_message handling.",
)

CONSUMER_GATE_IN_FLIGHT: Final[metrics.UpDownCounter] = METER.create_up_down_counter(
    name="aiopika.consumer.gate.in_flight",
    unit="1",
    description="In-flight managed consumer handlers holding a concurrency permit.",
)

ATTR_LISTENER: Final[str] = "aiopika.listener"
ATTR_OUTCOME: Final[str] = "aiopika.outcome"
ATTR_PHASE: Final[str] = "aiopika.phase"
ATTR_BACKEND: Final[str] = "aiopika.backend"
ATTR_SCOPE: Final[str] = "aiopika.scope"
ATTR_QUEUE: Final[str] = "aiopika.queue"

PHASE_PRECHECK: Final[str] = "precheck"
PHASE_GATE: Final[str] = "gate"
PHASE_PROCESS: Final[str] = "process"
PHASE_ERROR: Final[str] = "error"
PHASE_POISON: Final[str] = "poison"

GateScope = Literal["global", "listener"]
TracePhase = Literal["precheck", "gate.acquire", "process"]

SCOPE_GLOBAL: GateScope = "global"
SCOPE_LISTENER: GateScope = "listener"


class ConsumerTelemetry(ABC):
    """Observability hook for the managed consumer pipeline."""

    @abstractmethod
    def record_settlement(
        self,
        *,
        listener: str,
        outcome: MessageDeliveryOutcome,
        phase: str,
    ) -> None:
        """Record a message settlement decision."""

    @abstractmethod
    def record_gate_saturated(
        self,
        *,
        listener: str,
        backend: str,
        scope: GateScope,
    ) -> None:
        """Record a concurrency gate saturation event."""

    @abstractmethod
    def record_gate_acquire(
        self,
        *,
        listener: str,
        backend: str,
        acquired: bool,
    ) -> None:
        """Record the result of a gate acquisition attempt."""

    @abstractmethod
    def record_in_flight_delta(
        self,
        *,
        listener: str,
        backend: str,
        delta: int,
    ) -> None:
        """Adjust the in-flight handler gauge for a listener/backend pair."""

    @abstractmethod
    def record_process_duration(
        self,
        *,
        listener: str,
        outcome: MessageDeliveryOutcome,
        duration_seconds: float,
    ) -> None:
        """Record process_message wall time."""

    @abstractmethod
    @contextmanager
    def trace_message(self, *, listener: str, queue: str) -> Iterator[Span]:
        """Create the root span for one managed message delivery."""

    @abstractmethod
    @contextmanager
    def trace_phase(self, *, listener: str, phase: TracePhase) -> Iterator[Span]:
        """Create a child span for a pipeline phase."""


class NoOpConsumerTelemetry(ConsumerTelemetry):
    """Explicit no-op telemetry for tests or minimal deployments."""

    def record_settlement(
        self,
        *,
        listener: str,
        outcome: MessageDeliveryOutcome,
        phase: str,
    ) -> None:
        """No-op."""
        del listener, outcome, phase

    def record_gate_saturated(
        self,
        *,
        listener: str,
        backend: str,
        scope: GateScope,
    ) -> None:
        """No-op."""
        del listener, backend, scope

    def record_gate_acquire(
        self,
        *,
        listener: str,
        backend: str,
        acquired: bool,
    ) -> None:
        """No-op."""
        del listener, backend, acquired

    def record_in_flight_delta(
        self,
        *,
        listener: str,
        backend: str,
        delta: int,
    ) -> None:
        """No-op."""
        del listener, backend, delta

    def record_process_duration(
        self,
        *,
        listener: str,
        outcome: MessageDeliveryOutcome,
        duration_seconds: float,
    ) -> None:
        """No-op."""
        del listener, outcome, duration_seconds

    @contextmanager
    def trace_message(self, *, listener: str, queue: str) -> Iterator[Span]:
        """Yield an invalid span."""
        del listener, queue
        yield trace.INVALID_SPAN

    @contextmanager
    def trace_phase(self, *, listener: str, phase: TracePhase) -> Iterator[Span]:
        """Yield an invalid span."""
        del listener, phase
        yield trace.INVALID_SPAN


class OpenTelemetryConsumerTelemetry(ConsumerTelemetry):
    """Default telemetry backed by module-level OpenTelemetry instruments."""

    def record_settlement(
        self,
        *,
        listener: str,
        outcome: MessageDeliveryOutcome,
        phase: str,
    ) -> None:
        """Record a message settlement counter event."""
        CONSUMER_MESSAGE_SETTLED.add(
            1,
            attributes={
                ATTR_LISTENER: listener,
                ATTR_OUTCOME: outcome.value,
                ATTR_PHASE: phase,
            },
        )

    def record_gate_saturated(
        self,
        *,
        listener: str,
        backend: str,
        scope: GateScope,
    ) -> None:
        """Record a gate saturation counter event."""
        CONSUMER_GATE_SATURATED.add(
            1,
            attributes={
                ATTR_LISTENER: listener,
                ATTR_BACKEND: backend,
                ATTR_SCOPE: scope,
            },
        )

    def record_gate_acquire(
        self,
        *,
        listener: str,
        backend: str,
        acquired: bool,
    ) -> None:
        """Record a successful gate acquisition (no-op when not acquired)."""
        if not acquired:
            return
        del listener, backend

    def record_in_flight_delta(
        self,
        *,
        listener: str,
        backend: str,
        delta: int,
    ) -> None:
        """Adjust the in-flight handler up/down counter."""
        CONSUMER_GATE_IN_FLIGHT.add(
            delta,
            attributes={
                ATTR_LISTENER: listener,
                ATTR_BACKEND: backend,
            },
        )

    def record_process_duration(
        self,
        *,
        listener: str,
        outcome: MessageDeliveryOutcome,
        duration_seconds: float,
    ) -> None:
        """Record process_message duration in the histogram."""
        CONSUMER_PROCESS_DURATION.record(
            duration_seconds,
            attributes={
                ATTR_LISTENER: listener,
                ATTR_OUTCOME: outcome.value,
            },
        )

    @contextmanager
    def trace_message(self, *, listener: str, queue: str) -> Iterator[Span]:
        """Create the root span for one managed message delivery."""
        with TRACER.start_as_current_span(
            "aiopika.consumer.handle",
            attributes={
                ATTR_LISTENER: listener,
                ATTR_QUEUE: queue,
            },
        ) as span:
            yield span

    @contextmanager
    def trace_phase(self, *, listener: str, phase: TracePhase) -> Iterator[Span]:
        """Create a child span for a pipeline phase."""
        with TRACER.start_as_current_span(
            f"aiopika.consumer.{phase}",
            attributes={ATTR_LISTENER: listener},
        ) as span:
            yield span


def mark_span_error(span: Span, exc: BaseException) -> None:
    """Record ``exc`` on ``span`` and set error status.

    Args:
        span: Active OpenTelemetry span.
        exc: Exception to record.
    """
    span.record_exception(exc)
    span.set_status(Status(StatusCode.ERROR, str(exc)))


class ProcessDurationTracker:
    """Wall-clock helper for process_message duration histograms."""

    def __init__(self) -> None:
        """Capture the start timestamp."""
        self._started_at: float = time.perf_counter()

    def elapsed_seconds(self) -> float:
        """Return elapsed seconds since construction."""
        return time.perf_counter() - self._started_at
