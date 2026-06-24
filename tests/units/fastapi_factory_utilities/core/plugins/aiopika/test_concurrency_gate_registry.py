"""Unit tests for the concurrency gate registry."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, Field

from fastapi_factory_utilities.core.plugins.aiopika import AbstractManagedListener, GenericMessage
from fastapi_factory_utilities.core.plugins.aiopika.concurrency import (
    ConcurrencyGate,
    LocalConcurrencyGate,
    get_concurrency_gate,
    reset_concurrency_gate_for_tests,
    set_concurrency_gate,
)
from fastapi_factory_utilities.core.plugins.aiopika.delivery import MessageDeliveryOutcome
from fastapi_factory_utilities.core.plugins.aiopika.telemetry import NoOpConsumerTelemetry


class _Body(BaseModel):
    msg: str = Field(description="Text.")


class _Msg(GenericMessage[_Body]):
    pass


class _StubGate(LocalConcurrencyGate):
    """Stub gate marking itself in registry tests."""


class TestConcurrencyGateRegistry:
    """Registry swap and default backend."""

    def setup_method(self) -> None:
        """Reset registry before each test."""
        reset_concurrency_gate_for_tests()

    def teardown_method(self) -> None:
        """Reset registry after each test."""
        reset_concurrency_gate_for_tests()

    def test_default_is_local_gate(self) -> None:
        """Default registry backend is LocalConcurrencyGate."""
        gate = get_concurrency_gate()
        assert isinstance(gate, LocalConcurrencyGate)
        assert gate.backend_name == "local"

    def test_set_concurrency_gate_swaps_backend(self) -> None:
        """set_concurrency_gate replaces the active backend."""
        stub = _StubGate()
        set_concurrency_gate(stub)
        assert get_concurrency_gate() is stub

    @pytest.mark.asyncio
    async def test_listener_injection_uses_custom_gate(self) -> None:
        """Managed listeners can inject a gate without touching the registry."""
        custom_gate = MagicMock(spec=ConcurrencyGate)
        custom_gate.backend_name = "stub"
        custom_gate.try_acquire = AsyncMock(return_value=True)
        custom_gate.release = MagicMock()

        class Listener(AbstractManagedListener[_Msg]):
            async def process_message(self, message: _Msg) -> MessageDeliveryOutcome | None:
                del message
                return None

        listener = Listener(
            queue=MagicMock(),
            concurrency_gate=custom_gate,
            telemetry=NoOpConsumerTelemetry(),
        )
        message = _Msg(data=_Body(msg="x"))
        incoming = MagicMock()
        incoming.ack = AsyncMock()
        message.set_incoming_message(incoming_message=incoming)

        await listener.on_message(message)

        custom_gate.try_acquire.assert_awaited_once()
        custom_gate.release.assert_called_once()
