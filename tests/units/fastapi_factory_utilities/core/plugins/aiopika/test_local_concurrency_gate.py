"""Unit tests for LocalConcurrencyGate."""

import pytest

from fastapi_factory_utilities.core.plugins.aiopika.concurrency.local import LocalConcurrencyGate
from fastapi_factory_utilities.core.plugins.aiopika.telemetry import NoOpConsumerTelemetry


class TestLocalConcurrencyGate:
    """Process-local semaphore gate behaviour."""

    @pytest.mark.asyncio
    async def test_unconfigured_always_acquires(self) -> None:
        """No limits configured means try_acquire always succeeds."""
        gate = LocalConcurrencyGate(telemetry=NoOpConsumerTelemetry())
        assert await gate.try_acquire("listener-a") is True
        gate.release("listener-a")

    @pytest.mark.asyncio
    async def test_global_limit_blocks_second_acquire(self) -> None:
        """Global saturation returns False without blocking."""
        gate = LocalConcurrencyGate(telemetry=NoOpConsumerTelemetry())
        gate.configure(global_limit=1)
        assert await gate.try_acquire("listener-a") is True
        assert await gate.try_acquire("listener-b") is False
        gate.release("listener-a")
        assert await gate.try_acquire("listener-b") is True
        gate.release("listener-b")

    @pytest.mark.asyncio
    async def test_listener_limit_blocks_same_key(self) -> None:
        """Per-listener saturation is scoped to the listener key."""
        gate = LocalConcurrencyGate(telemetry=NoOpConsumerTelemetry())
        gate.configure_listener("orders", limit=1)
        assert await gate.try_acquire("orders") is True
        assert await gate.try_acquire("orders") is False
        assert await gate.try_acquire("billing") is True
        gate.release("orders")
        gate.release("billing")

    @pytest.mark.asyncio
    async def test_global_then_listener_acquire_order(self) -> None:
        """Listener saturation releases the global permit acquired first."""
        gate = LocalConcurrencyGate(telemetry=NoOpConsumerTelemetry())
        gate.configure(global_limit=2)
        gate.configure_listener("orders", limit=1)
        assert await gate.try_acquire("orders") is True
        assert await gate.try_acquire("orders") is False
        assert await gate.try_acquire("billing") is True
        gate.release("orders")
        gate.release("billing")

    def test_configure_rejects_invalid_limits(self) -> None:
        """Limits must be at least 1."""
        gate = LocalConcurrencyGate(telemetry=NoOpConsumerTelemetry())
        with pytest.raises(ValueError, match="global_limit"):
            gate.configure(global_limit=0)
        with pytest.raises(ValueError, match="limit"):
            gate.configure_listener("orders", 0)
