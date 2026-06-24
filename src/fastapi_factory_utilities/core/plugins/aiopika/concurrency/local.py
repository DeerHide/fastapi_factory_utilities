"""Process-local asyncio semaphore concurrency gate."""

from __future__ import annotations

import asyncio

from ..telemetry import (
    SCOPE_GLOBAL,
    SCOPE_LISTENER,
    ConsumerTelemetry,
    OpenTelemetryConsumerTelemetry,
)
from .abstract import ConcurrencyGate


class LocalConcurrencyGate(ConcurrencyGate):
    """Process-local :class:`asyncio.Semaphore` registry (one pod / one worker process)."""

    def __init__(self, telemetry: ConsumerTelemetry | None = None) -> None:
        """Initialize an unconfigured local gate.

        Args:
            telemetry: Optional telemetry facade. Defaults to
                :class:`~fastapi_factory_utilities.core.plugins.aiopika.telemetry.OpenTelemetryConsumerTelemetry`.
        """
        self._global_semaphore: asyncio.Semaphore | None = None
        self._listener_semaphores: dict[str, asyncio.Semaphore] = {}
        self._telemetry: ConsumerTelemetry = telemetry or OpenTelemetryConsumerTelemetry()

    @property
    def backend_name(self) -> str:
        """Return the stable backend identifier ``local``."""
        return "local"

    def configure(self, *, global_limit: int | None = None) -> None:
        """Configure the global concurrency cap for this process.

        Args:
            global_limit: Maximum concurrent handlers across all listeners.

        Raises:
            ValueError: When ``global_limit`` is less than 1.
        """
        if global_limit is None:
            return
        if global_limit < 1:
            raise ValueError("global_limit must be at least 1")
        self._global_semaphore = asyncio.Semaphore(global_limit)

    def configure_listener(self, listener_key: str, limit: int) -> None:
        """Configure a per-listener concurrency cap.

        Args:
            listener_key: Logical listener or pool identifier.
            limit: Maximum concurrent handlers for ``listener_key``.

        Raises:
            ValueError: When ``limit`` is less than 1.
        """
        if limit < 1:
            raise ValueError("limit must be at least 1")
        self._listener_semaphores[listener_key] = asyncio.Semaphore(limit)

    def _is_configured(self) -> bool:
        return self._global_semaphore is not None or bool(self._listener_semaphores)

    async def try_acquire(self, listener_key: str) -> bool:
        """Try to acquire configured permits without blocking.

        Args:
            listener_key: Listener or pool key for per-listener limits.

        Returns:
            ``True`` when permits were acquired; ``False`` when saturated.
        """
        if not self._is_configured():
            return True

        global_semaphore: asyncio.Semaphore | None = self._global_semaphore
        if global_semaphore is not None:
            if global_semaphore.locked():
                self._telemetry.record_gate_saturated(
                    listener=listener_key,
                    backend=self.backend_name,
                    scope=SCOPE_GLOBAL,
                )
                self._telemetry.record_gate_acquire(
                    listener=listener_key,
                    backend=self.backend_name,
                    acquired=False,
                )
                return False
            await global_semaphore.acquire()

        listener_semaphore: asyncio.Semaphore | None = self._listener_semaphores.get(listener_key)
        if listener_semaphore is not None:
            if listener_semaphore.locked():
                if global_semaphore is not None:
                    global_semaphore.release()
                self._telemetry.record_gate_saturated(
                    listener=listener_key,
                    backend=self.backend_name,
                    scope=SCOPE_LISTENER,
                )
                self._telemetry.record_gate_acquire(
                    listener=listener_key,
                    backend=self.backend_name,
                    acquired=False,
                )
                return False
            await listener_semaphore.acquire()

        self._telemetry.record_gate_acquire(
            listener=listener_key,
            backend=self.backend_name,
            acquired=True,
        )
        self._telemetry.record_in_flight_delta(
            listener=listener_key,
            backend=self.backend_name,
            delta=1,
        )
        return True

    def release(self, listener_key: str) -> None:
        """Release permits previously acquired for ``listener_key``.

        Args:
            listener_key: Same key passed to :meth:`try_acquire`.
        """
        if not self._is_configured():
            return

        listener_semaphore: asyncio.Semaphore | None = self._listener_semaphores.get(listener_key)
        if listener_semaphore is not None:
            listener_semaphore.release()
        if self._global_semaphore is not None:
            self._global_semaphore.release()
        self._telemetry.record_in_flight_delta(
            listener=listener_key,
            backend=self.backend_name,
            delta=-1,
        )
