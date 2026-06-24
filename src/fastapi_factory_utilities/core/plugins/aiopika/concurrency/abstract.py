"""Abstract concurrency gate for managed consumer message handling."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ConcurrencyGate(ABC):
    """Non-blocking concurrency permit for consumer message handling.

    Backends must honour:

    * **Non-blocking** — ``try_acquire`` never waits on a contended permit.
    * **Acquire order** — global permit first, then per-listener; release in reverse.
    * **Partial failure** — when global succeeds but listener slot fails, release global.
    * **No-op when unconfigured** — ``try_acquire`` returns ``True`` when no limits are set.

    Future distributed backends (e.g. Redis) must use TTL leases and release tokens
    to avoid double-release after lease expiry.
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return a stable backend identifier for metrics (e.g. ``local``, ``redis``)."""

    @abstractmethod
    def configure(self, *, global_limit: int | None = None) -> None:
        """Set the process/cluster-wide concurrency cap.

        Args:
            global_limit: Maximum concurrent handlers across all listeners. ``None`` leaves
                global limiting unchanged; omit on subsequent calls to keep prior value.
        """

    @abstractmethod
    def configure_listener(self, listener_key: str, limit: int) -> None:
        """Set a per-listener (or per-pool) concurrency cap.

        Args:
            listener_key: Logical listener or pool identifier.
            limit: Maximum concurrent handlers for ``listener_key``.
        """

    @abstractmethod
    async def try_acquire(self, listener_key: str) -> bool:
        """Try to acquire permits without blocking.

        Args:
            listener_key: Listener or pool key used for per-listener limits.

        Returns:
            ``True`` when all configured permits were acquired; ``False`` when saturated.
        """

    @abstractmethod
    def release(self, listener_key: str) -> None:
        """Release permits acquired by a successful :meth:`try_acquire`.

        Args:
            listener_key: Same key passed to :meth:`try_acquire`.
        """
