"""Registry for the active :class:`~.abstract.ConcurrencyGate` implementation."""

from __future__ import annotations

from .abstract import ConcurrencyGate
from .local import LocalConcurrencyGate

_default_gate: ConcurrencyGate = LocalConcurrencyGate()


def get_concurrency_gate() -> ConcurrencyGate:
    """Return the active concurrency gate backend.

    Returns:
        The configured :class:`~.abstract.ConcurrencyGate` instance.
    """
    return _default_gate


def set_concurrency_gate(gate: ConcurrencyGate) -> None:
    """Replace the active concurrency gate backend.

    Call only during application startup before listeners begin consuming.

    Args:
        gate: Backend implementation to use for subsequent consumer acquisitions.
    """
    global _default_gate  # noqa: PLW0603
    _default_gate = gate


def reset_concurrency_gate_for_tests() -> None:
    """Reset the registry to a fresh :class:`~.local.LocalConcurrencyGate` (tests only)."""
    global _default_gate  # noqa: PLW0603
    _default_gate = LocalConcurrencyGate()
