"""Unit tests for AMQP channel sharing and lifecycle."""

# pylint: disable=protected-access

from unittest.mock import AsyncMock, MagicMock

import pytest
from aio_pika import ExchangeType
from pydantic import BaseModel, Field

from fastapi_factory_utilities.core.plugins.aiopika import (
    AbstractListener,
    AbstractPublisher,
    Exchange,
    ExchangeName,
    GenericMessage,
    Queue,
    QueueName,
    RoutingKey,
)
from fastapi_factory_utilities.core.plugins.aiopika.abstract import AbstractAiopikaResource


class _Payload(BaseModel):
    """Minimal payload."""

    value: str = Field(description="Value.")


class _Message(GenericMessage[_Payload]):
    """Concrete message type."""


class _Listener(AbstractListener[_Message]):
    """Minimal listener for channel tests."""

    async def on_message(self, message: _Message) -> None:
        """No-op handler."""


def _robust_connection(*, channel: MagicMock) -> MagicMock:
    """Build a mock robust connection returning the given channel."""
    connection = MagicMock()
    connection.channel = AsyncMock(return_value=channel)
    return connection


class TestResetChannel:
    """Tests for reset_channel and re-acquire behavior."""

    @pytest.mark.asyncio
    async def test_reset_channel_causes_reacquire(self) -> None:
        """Clearing the cache opens a new channel on the next acquire."""
        first_channel = MagicMock(is_closed=False)
        second_channel = MagicMock(is_closed=False)
        connection = MagicMock()
        connection.channel = AsyncMock(side_effect=[first_channel, second_channel])

        resource = AbstractAiopikaResource()
        resource.set_robust_connection(connection)

        assert await resource._acquire_channel() is first_channel
        resource.reset_channel()
        assert await resource._acquire_channel() is second_channel
        expected_acquire_count = 2
        assert connection.channel.await_count == expected_acquire_count


class TestEnsureSharedChannelWith:
    """Tests for ensure_shared_channel_with."""

    @pytest.mark.asyncio
    async def test_reuses_other_open_channel(self) -> None:
        """When the peer already has a channel, both sides share it."""
        shared = MagicMock(is_closed=False)
        connection = MagicMock()
        connection.channel = AsyncMock()

        left = AbstractAiopikaResource()
        right = AbstractAiopikaResource()
        left.set_robust_connection(connection)
        right.set_robust_connection(connection)
        right.set_channel(shared)

        result = await left.ensure_shared_channel_with(right)

        assert result is shared
        assert left._channel is shared
        assert right._channel is shared
        connection.channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_acquires_once_when_neither_has_channel(self) -> None:
        """A single acquire is shared between both resources."""
        shared = MagicMock(is_closed=False)
        connection = _robust_connection(channel=shared)

        left = AbstractAiopikaResource()
        right = AbstractAiopikaResource()
        left.set_robust_connection(connection)
        right.set_robust_connection(connection)

        result = await left.ensure_shared_channel_with(right)

        assert result is shared
        assert left._channel is shared
        assert right._channel is shared
        connection.channel.assert_awaited_once()


class TestPublisherChannelUsage:
    """Publisher setup should not open its own channel."""

    @pytest.mark.asyncio
    async def test_publisher_setup_uses_exchange_channel_only(self) -> None:
        """Publisher setup delegates to the owned exchange without a publisher channel."""
        channel = MagicMock(is_closed=False)
        declared_exchange = MagicMock()
        channel.declare_exchange = AsyncMock(return_value=declared_exchange)
        connection = _robust_connection(channel=channel)

        exchange = Exchange(name=ExchangeName("test"), exchange_type=ExchangeType.TOPIC)
        exchange.set_robust_connection(connection)
        publisher = AbstractPublisher(exchange=exchange)
        publisher.set_robust_connection(connection)

        await publisher.setup()

        connection.channel.assert_awaited_once()
        assert publisher._channel is None
        assert exchange._channel is channel


class TestListenerChannelUsage:
    """Listener setup should not open its own channel."""

    @pytest.mark.asyncio
    async def test_listener_setup_uses_queue_channel_only(self) -> None:
        """Listener setup delegates to the bound queue without a listener channel."""
        channel = MagicMock(is_closed=False)
        declared_exchange = MagicMock()
        declared_queue = MagicMock()
        channel.declare_exchange = AsyncMock(return_value=declared_exchange)
        channel.declare_queue = AsyncMock(return_value=declared_queue)
        declared_queue.bind = AsyncMock()
        connection = _robust_connection(channel=channel)

        exchange = Exchange(name=ExchangeName("test"), exchange_type=ExchangeType.TOPIC)
        queue = Queue(
            name=QueueName("test-queue"),
            exchange=exchange,
            routing_key=RoutingKey("test.key"),
        )
        queue.set_robust_connection(connection)
        exchange.set_robust_connection(connection)
        listener = _Listener(queue=queue)
        listener.set_robust_connection(connection)

        await listener.setup()

        connection.channel.assert_awaited_once()
        assert listener._channel is None
        assert queue._channel is channel
        assert exchange._channel is channel


class TestQueueExchangeChannelSharing:
    """Queue setup shares one channel with its nested exchange."""

    @pytest.mark.asyncio
    async def test_queue_setup_shares_channel_with_exchange(self) -> None:
        """Queue and nested exchange reuse the same channel handle."""
        channel = MagicMock(is_closed=False)
        declared_exchange = MagicMock()
        declared_queue = MagicMock()
        channel.declare_exchange = AsyncMock(return_value=declared_exchange)
        channel.declare_queue = AsyncMock(return_value=declared_queue)
        declared_queue.bind = AsyncMock()
        connection = _robust_connection(channel=channel)

        exchange = Exchange(name=ExchangeName("test"), exchange_type=ExchangeType.TOPIC)
        queue = Queue(
            name=QueueName("test-queue"),
            exchange=exchange,
            routing_key=RoutingKey("test.key"),
        )
        queue.set_robust_connection(connection)
        exchange.set_robust_connection(connection)

        await queue.setup()

        connection.channel.assert_awaited_once()
        assert queue._channel is channel
        assert exchange._channel is channel
