"""Provides the abstract class for the Aiopika plugin."""

from abc import ABC
from typing import Self

from aio_pika.abc import AbstractChannel, AbstractRobustConnection

from .exceptions import AiopikaPluginBaseError, AiopikaPluginConnectionNotProvidedError


class AbstractAiopikaResource(ABC):
    """Abstract class for the Aiopika resource."""

    def __init__(self) -> None:
        """Initialize the Aiopika resource."""
        self._robust_connection: AbstractRobustConnection | None = None
        self._channel: AbstractChannel | None = None

    def set_robust_connection(self, robust_connection: AbstractRobustConnection) -> Self:
        """Set the robust connection."""
        self._robust_connection = robust_connection
        return self

    def set_channel(self, channel: AbstractChannel) -> Self:
        """Set the channel."""
        self._channel = channel
        return self

    def reset_channel(self) -> None:
        """Clear the cached channel handle after broker-side closure."""
        self._channel = None

    @staticmethod
    def _is_channel_usable(channel: AbstractChannel | None) -> bool:
        """Return whether the cached channel can still be reused."""
        return channel is not None and not channel.is_closed

    async def ensure_shared_channel_with(self, other: "AbstractAiopikaResource") -> AbstractChannel:
        """Ensure both resources share one open channel.

        Reuses an already-open channel from either side when available; otherwise
        acquires once and assigns it to both resources.

        Args:
            other: Related resource that should share the same channel.

        Returns:
            The shared channel instance.
        """
        # pylint: disable=protected-access
        if self._is_channel_usable(other._channel):
            self.set_channel(other._channel)  # type: ignore[arg-type]
            return other._channel  # type: ignore[return-value]
        if self._is_channel_usable(self._channel):
            other.set_channel(self._channel)  # type: ignore[arg-type]
            return self._channel  # type: ignore[return-value]
        channel = await self._acquire_channel()
        other.set_channel(channel)
        return channel

    async def _acquire_channel(self) -> AbstractChannel:
        """Acquire the channel."""
        if self._robust_connection is None:
            raise AiopikaPluginConnectionNotProvidedError(
                message="Robust connection not provided.",
            )
        if self._channel is None:
            try:
                self._channel = await self._robust_connection.channel()
            except Exception as exception:
                raise AiopikaPluginBaseError(
                    message="Failed to acquire the channel.",
                ) from exception
        return self._channel

    async def setup(self) -> Self:
        """Setup the Aiopika resource."""
        if self._channel is None:
            await self._acquire_channel()
        return self
