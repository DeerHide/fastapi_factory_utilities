"""Test the RabbitMQ publisher."""

from uuid import uuid4

from aio_pika import ExchangeType
from pydantic import BaseModel, Field

from fastapi_factory_utilities.core.plugins.aiopika import (
    AbstractMessage,
    AbstractPublisher,
    AiopikaPlugin,
    Exchange,
    SenderModel,
)
from fastapi_factory_utilities.core.plugins.aiopika.queue import Queue


class BodyMessageForTest(BaseModel):
    """Test body message."""

    message: str = Field(description="The message.")


class MessageForTest(AbstractMessage[BodyMessageForTest]):
    """Test message."""


class PublisherForTest(AbstractPublisher[MessageForTest]):
    """Test publisher."""


class TestPublisherRabbitMQ:
    """Test the RabbitMQ publisher."""

    async def test_publisher(self, aiopika_plugin: AiopikaPlugin) -> None:
        """Test the RabbitMQ publisher."""
        assert aiopika_plugin is not None
        # Prepare the exchange
        exchange: Exchange = Exchange(name="test_exchange", exchange_type=ExchangeType.FANOUT)
        exchange.set_robust_connection(robust_connection=aiopika_plugin.robust_connection)
        # Prepare the publisher
        publisher: PublisherForTest = PublisherForTest(exchange=exchange)
        publisher.set_robust_connection(robust_connection=aiopika_plugin.robust_connection)
        # Prepare the queue (this is required to be able to receive a delivery acknowledgement)
        queue: Queue = Queue(name="test_queue", exchange=exchange, routing_key="test_routing_key")
        queue.set_robust_connection(robust_connection=aiopika_plugin.robust_connection)
        # Setup the resources
        await exchange.setup()
        await queue.setup()
        await publisher.setup()
        # Prepare the message
        sender: SenderModel = SenderModel(name="test_sender")
        message: MessageForTest = MessageForTest(sender=sender, data=BodyMessageForTest(message=str(uuid4())))
        # Publish the message
        await publisher.publish(message=message, routing_key="test_routing_key")
