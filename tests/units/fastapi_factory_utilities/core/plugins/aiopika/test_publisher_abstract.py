"""Unit tests for AbstractPublisher.publish."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from aio_pika.message import Message
from pamqp.commands import Basic
from pydantic import BaseModel

from fastapi_factory_utilities.core.plugins.aiopika import AbstractPublisher, GenericMessage
from fastapi_factory_utilities.core.plugins.aiopika.exceptions import AiopikaPluginBaseError
from fastapi_factory_utilities.core.plugins.aiopika.types import RoutingKey


class Payload(BaseModel):
    """Minimal payload."""

    value: str


class BrokenGenericMessage(GenericMessage[Payload]):
    """Message whose serialization always fails."""

    def to_aiopika_message(self) -> Message:
        """Force conversion failure."""
        raise RuntimeError("cannot serialize")


class TestAbstractPublisherPublish:
    """Tests for publish error handling and success path."""

    @pytest.mark.asyncio
    async def test_publish_success(self) -> None:
        """Successful publish returns after confirmation object."""
        inner = MagicMock()
        inner.publish = AsyncMock(return_value=object())

        exchange_resource = MagicMock()
        exchange_resource.exchange = inner

        publisher = AbstractPublisher(exchange=exchange_resource)
        message = GenericMessage[Payload](data=Payload(value="ok"))
        routing_key = RoutingKey("one.two.three")

        await publisher.publish(message=message, routing_key=routing_key)

        inner.publish.assert_awaited_once()
        call_kw = inner.publish.await_args.kwargs
        assert call_kw["routing_key"] == routing_key
        assert call_kw["mandatory"] is True

    @pytest.mark.asyncio
    async def test_publish_wraps_to_aiopika_failure(self) -> None:
        """Conversion errors become AiopikaPluginBaseError."""
        inner = MagicMock()
        inner.publish = AsyncMock()

        exchange_resource = MagicMock()
        exchange_resource.exchange = inner

        publisher = AbstractPublisher(exchange=exchange_resource)
        broken = BrokenGenericMessage(data=Payload(value="x"))
        routing_key = RoutingKey("one.two.three")

        with pytest.raises(AiopikaPluginBaseError, match="convert"):
            await publisher.publish(message=broken, routing_key=routing_key)

        inner.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_publish_wraps_exchange_failure(self) -> None:
        """Underlying publish exception is wrapped."""
        inner = MagicMock()
        inner.publish = AsyncMock(side_effect=ConnectionError("boom"))

        exchange_resource = MagicMock()
        exchange_resource.exchange = inner

        publisher = AbstractPublisher(exchange=exchange_resource)
        message = GenericMessage[Payload](data=Payload(value="ok"))
        routing_key = RoutingKey("one.two.three")

        with pytest.raises(AiopikaPluginBaseError, match="publish"):
            await publisher.publish(message=message, routing_key=routing_key)

    @pytest.mark.asyncio
    async def test_publish_fails_on_none_confirmation(self) -> None:
        """None confirmation is treated as publish failure."""
        inner = MagicMock()
        inner.publish = AsyncMock(return_value=None)

        exchange_resource = MagicMock()
        exchange_resource.exchange = inner

        publisher = AbstractPublisher(exchange=exchange_resource)
        message = GenericMessage[Payload](data=Payload(value="ok"))
        routing_key = RoutingKey("one.two.three")

        with pytest.raises(AiopikaPluginBaseError, match="publish"):
            await publisher.publish(message=message, routing_key=routing_key)

    @pytest.mark.asyncio
    async def test_publish_fails_on_basic_return(self) -> None:
        """Basic.Return confirmation triggers publish failure."""
        inner = MagicMock()
        inner.publish = AsyncMock(return_value=Basic.Return())

        exchange_resource = MagicMock()
        exchange_resource.exchange = inner

        publisher = AbstractPublisher(exchange=exchange_resource)
        message = GenericMessage[Payload](data=Payload(value="ok"))
        routing_key = RoutingKey("one.two.three")

        with pytest.raises(AiopikaPluginBaseError, match="publish"):
            await publisher.publish(message=message, routing_key=routing_key)
