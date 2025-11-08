"""Test the RabbitMQ listener."""

import asyncio
from uuid import uuid4

from aio_pika import ExchangeType
from pydantic import BaseModel, Field

from fastapi_factory_utilities.core.plugins.aiopika import (
    AbstractListener,
    AbstractMessage,
    AbstractPublisher,
    AiopikaPlugin,
    Exchange,
    Queue,
    SenderModel,
)


class BodyMessageForTest(BaseModel):
    """Test body message."""

    message: str = Field(description="The message.")


class MessageForTest(AbstractMessage[BodyMessageForTest]):
    """Test message."""


class PublisherForTest(AbstractPublisher[MessageForTest]):
    """Publisher for test."""


class ListenerForTest(AbstractListener[MessageForTest]):
    """Listener for test."""

    def __init__(self, queue: Queue, name: str | None = None) -> None:
        """Initialize the listener."""
        super().__init__(queue=queue, name=name)
        self._message_count: int = 0

    @property
    def message_count(self) -> int:
        """Get the message count."""
        return self._message_count

    async def on_message(self, message: MessageForTest) -> None:
        """On message."""
        self._message_count += 1
        await message.ack()


class TestListenerRabbitMQ:
    """Test the RabbitMQ listener."""

    async def test_listener(self, aiopika_plugin: AiopikaPlugin) -> None:
        """Test the RabbitMQ listener."""
        assert aiopika_plugin is not None
        # Prepare the exchange
        exchange: Exchange = Exchange(name="test_exchange", exchange_type=ExchangeType.FANOUT)
        exchange.set_robust_connection(robust_connection=aiopika_plugin.robust_connection)
        # Prepare the queue
        queue: Queue = Queue(name="test_queue", exchange=exchange, routing_key="test_routing_key")
        queue.set_robust_connection(robust_connection=aiopika_plugin.robust_connection)
        # Prepare the publisher
        publisher: PublisherForTest = PublisherForTest(exchange=exchange)
        publisher.set_robust_connection(robust_connection=aiopika_plugin.robust_connection)
        # Prepare the listener
        listener: ListenerForTest = ListenerForTest(queue=queue)
        listener.set_robust_connection(robust_connection=aiopika_plugin.robust_connection)
        # Setup the resources
        await exchange.setup()
        await queue.setup()
        await publisher.setup()
        await listener.setup()
        # Start listening BEFORE publishing the message
        await listener.listen()
        await asyncio.sleep(1)  # Give listener time to start
        # Publish the message
        await publisher.publish(
            message=MessageForTest(
                sender=SenderModel(name="test_sender"), data=BodyMessageForTest(message=str(uuid4()))
            ),
            routing_key="test_routing_key",
        )
        # Wait for the message to be received
        for _ in range(10):
            await asyncio.sleep(1)
            if listener.message_count > 0:
                break
        # Close the listener
        await listener.close()
        assert listener.message_count == 1
