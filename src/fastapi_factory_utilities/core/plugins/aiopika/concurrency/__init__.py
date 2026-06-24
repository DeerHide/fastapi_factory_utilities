"""Concurrency gate abstractions for managed AMQP consumers."""

from .abstract import ConcurrencyGate
from .local import LocalConcurrencyGate
from .registry import get_concurrency_gate, reset_concurrency_gate_for_tests, set_concurrency_gate

__all__: list[str] = [
    "ConcurrencyGate",
    "LocalConcurrencyGate",
    "get_concurrency_gate",
    "reset_concurrency_gate_for_tests",
    "set_concurrency_gate",
]
