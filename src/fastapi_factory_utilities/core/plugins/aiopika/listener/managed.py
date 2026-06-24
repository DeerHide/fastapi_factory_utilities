"""Managed AMQP listener with pre-check gate, concurrency control, and settlement."""

from __future__ import annotations

import json
from abc import abstractmethod
from typing import Any, ClassVar, Generic, TypeVar

from aio_pika.abc import AbstractIncomingMessage
from pydantic import ValidationError
from structlog.stdlib import BoundLogger, get_logger

from ..concurrency import ConcurrencyGate, get_concurrency_gate
from ..delivery import MessageDeliveryOutcome, settle_message
from ..message import GenericMessage
from ..queue import Queue
from ..telemetry import (
    PHASE_ERROR,
    PHASE_GATE,
    PHASE_POISON,
    PHASE_PRECHECK,
    PHASE_PROCESS,
    ConsumerTelemetry,
    NoOpConsumerTelemetry,
    OpenTelemetryConsumerTelemetry,
    ProcessDurationTracker,
    mark_span_error,
)
from .abstract import AbstractListener

_logger: BoundLogger = get_logger(__package__)

GenericManagedMessageType = TypeVar("GenericManagedMessageType", bound=GenericMessage[Any])  # pylint: disable=invalid-name


class AbstractManagedListener(AbstractListener[GenericManagedMessageType], Generic[GenericManagedMessageType]):
    """Managed consumer with pre-check, concurrency gate, and delivery settlement.

    Subclasses implement :meth:`process_message`. Optional overrides:

    * :meth:`precheck` — cheap filter before gate acquisition.
    * :meth:`map_exception_to_outcome` — map handler exceptions to delivery outcomes.
    """

    LISTENER_CONCURRENCY_LIMIT: ClassVar[int | None] = None
    GATE_KEY: ClassVar[str | None] = None
    POISON_MESSAGE_REQUEUE: ClassVar[bool] = True
    ENABLE_TELEMETRY: ClassVar[bool] = True

    def __init__(
        self,
        queue: Queue,
        name: str | None = None,
        exclusive: bool | None = None,
        *,
        concurrency_gate: ConcurrencyGate | None = None,
        telemetry: ConsumerTelemetry | None = None,
    ) -> None:
        """Initialize the managed listener.

        Args:
            queue: Bound queue resource.
            name: Optional listener name used for metrics and gate keys.
            exclusive: Optional exclusive consume override.
            concurrency_gate: Optional gate backend override for tests.
            telemetry: Optional telemetry facade override.
        """
        super().__init__(queue=queue, name=name, exclusive=exclusive)
        self._concurrency_gate: ConcurrencyGate = concurrency_gate or get_concurrency_gate()
        self._telemetry: ConsumerTelemetry = (
            NoOpConsumerTelemetry() if not self.ENABLE_TELEMETRY else (telemetry or OpenTelemetryConsumerTelemetry())
        )
        if self.LISTENER_CONCURRENCY_LIMIT is not None:
            self._concurrency_gate.configure_listener(
                self._gate_key(),
                self.LISTENER_CONCURRENCY_LIMIT,
            )

    def _gate_key(self) -> str:
        """Return the concurrency gate key for this listener."""
        return self.GATE_KEY or self._name

    def _queue_name(self) -> str:
        """Return the bound queue name for tracing."""
        return str(getattr(self._queue, "_name", self._name))

    async def _on_message(self, incoming_message: AbstractIncomingMessage) -> None:
        """Decode and validate the message, then dispatch to :meth:`on_message`.

        Args:
            incoming_message: Raw AMQP delivery from aio-pika.
        """
        body: str
        json_body: dict[str, Any]
        message: GenericManagedMessageType
        requeue_poison: bool = self.POISON_MESSAGE_REQUEUE
        try:
            body = incoming_message.body.decode("utf-8")
            json_body = json.loads(body)
        except json.JSONDecodeError as error:
            _logger.error("Failed to decode message", error=error, body=incoming_message.body)
            self._telemetry.record_settlement(
                listener=self._name,
                outcome=MessageDeliveryOutcome.REQUEUE if requeue_poison else MessageDeliveryOutcome.ACK,
                phase=PHASE_POISON,
            )
            await incoming_message.reject(requeue=requeue_poison)
            return
        except Exception as error:  # pylint: disable=broad-exception-caught
            _logger.error("Failed to decode message", error=error, body=incoming_message.body)
            self._telemetry.record_settlement(
                listener=self._name,
                outcome=MessageDeliveryOutcome.REQUEUE if requeue_poison else MessageDeliveryOutcome.ACK,
                phase=PHASE_POISON,
            )
            await incoming_message.reject(requeue=requeue_poison)
            return
        try:
            message = self._message_type.model_validate(json_body)
        except ValidationError as error:
            _logger.error("Failed to validate message", error=error, body=body)
            self._telemetry.record_settlement(
                listener=self._name,
                outcome=MessageDeliveryOutcome.REQUEUE if requeue_poison else MessageDeliveryOutcome.ACK,
                phase=PHASE_POISON,
            )
            await incoming_message.reject(requeue=requeue_poison)
            return
        message.set_incoming_message(incoming_message=incoming_message)
        await self.on_message(message=message)

    async def precheck(self, message: GenericManagedMessageType) -> MessageDeliveryOutcome:
        """Run cheap precondition checks before acquiring the concurrency gate.

        Args:
            message: Validated incoming message.

        Returns:
            Delivery outcome. ``CONTINUE`` proceeds to gate acquisition and processing.
        """
        del message
        return MessageDeliveryOutcome.CONTINUE

    def map_exception_to_outcome(self, exc: BaseException) -> MessageDeliveryOutcome:
        """Map an exception raised during processing to a delivery outcome.

        Args:
            exc: Exception raised by :meth:`process_message` or :meth:`precheck`.

        Returns:
            Delivery outcome used for settlement.
        """
        del exc
        return MessageDeliveryOutcome.REQUEUE

    @abstractmethod
    async def process_message(self, message: GenericManagedMessageType) -> MessageDeliveryOutcome | None:
        """Execute the message handler after pre-check and gate acquisition.

        Args:
            message: Validated incoming message.

        Returns:
            Optional explicit delivery outcome. ``None`` settles as ``ACK`` on success.

        Raises:
            BaseException: Propagates to :meth:`map_exception_to_outcome` when not ``CancelledError``.
        """

    async def on_message(self, message: GenericManagedMessageType) -> None:
        """Orchestrate pre-check, gate acquisition, processing, and settlement.

        Args:
            message: Validated incoming message with an attached delivery.
        """
        gate_key: str = self._gate_key()
        final_outcome: MessageDeliveryOutcome | None = None

        with self._telemetry.trace_message(listener=self._name, queue=self._queue_name()) as root_span:
            try:
                with self._telemetry.trace_phase(listener=self._name, phase="precheck"):
                    precheck_outcome: MessageDeliveryOutcome = await self.precheck(message)
            except BaseException as exc:
                if isinstance(exc, Exception):
                    final_outcome = self.map_exception_to_outcome(exc)
                    self._telemetry.record_settlement(
                        listener=self._name,
                        outcome=final_outcome,
                        phase=PHASE_ERROR,
                    )
                    mark_span_error(root_span, exc)
                    await settle_message(message, final_outcome)
                    return
                raise

            if precheck_outcome is not MessageDeliveryOutcome.CONTINUE:
                self._telemetry.record_settlement(
                    listener=self._name,
                    outcome=precheck_outcome,
                    phase=PHASE_PRECHECK,
                )
                root_span.set_attribute("aiopika.delivery.outcome", precheck_outcome.value)
                await settle_message(message, precheck_outcome)
                return

            with self._telemetry.trace_phase(listener=self._name, phase="gate.acquire"):
                gate_acquired: bool = await self._concurrency_gate.try_acquire(gate_key)
            if not gate_acquired:
                final_outcome = MessageDeliveryOutcome.REQUEUE
                self._telemetry.record_settlement(
                    listener=self._name,
                    outcome=final_outcome,
                    phase=PHASE_GATE,
                )
                root_span.set_attribute("aiopika.delivery.outcome", final_outcome.value)
                root_span.set_attribute("aiopika.gate.acquired", False)
                await settle_message(message, final_outcome)
                return

            root_span.set_attribute("aiopika.gate.acquired", True)
            try:
                duration_tracker: ProcessDurationTracker = ProcessDurationTracker()
                with self._telemetry.trace_phase(listener=self._name, phase="process"):
                    try:
                        process_outcome: MessageDeliveryOutcome | None = await self.process_message(message)
                    except BaseException as exc:
                        if isinstance(exc, Exception):
                            final_outcome = self.map_exception_to_outcome(exc)
                            self._telemetry.record_settlement(
                                listener=self._name,
                                outcome=final_outcome,
                                phase=PHASE_ERROR,
                            )
                            self._telemetry.record_process_duration(
                                listener=self._name,
                                outcome=final_outcome,
                                duration_seconds=duration_tracker.elapsed_seconds(),
                            )
                            mark_span_error(root_span, exc)
                            await settle_message(message, final_outcome)
                            return
                        raise

                final_outcome = process_outcome or MessageDeliveryOutcome.ACK
                self._telemetry.record_process_duration(
                    listener=self._name,
                    outcome=final_outcome,
                    duration_seconds=duration_tracker.elapsed_seconds(),
                )
                self._telemetry.record_settlement(
                    listener=self._name,
                    outcome=final_outcome,
                    phase=PHASE_PROCESS,
                )
                root_span.set_attribute("aiopika.delivery.outcome", final_outcome.value)
                await settle_message(message, final_outcome)
            finally:
                self._concurrency_gate.release(gate_key)
