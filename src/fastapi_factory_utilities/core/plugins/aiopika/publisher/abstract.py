"""Provides the abstract class for the publisher port for the Aiopika plugin."""

from typing import Any, ClassVar, Generic, Self, TypeVar

from aio_pika.abc import TimeoutType
from aio_pika.message import Message
from aiormq.abc import ConfirmationFrameType, DeliveredMessage
from pamqp.commands import Basic

from ..abstract import AbstractAiopikaResource
from ..exceptions import AiopikaPluginBaseError
from ..exchange import Exchange
from ..message import GenericMessage

GenericMessageType = TypeVar("GenericMessageType", bound=GenericMessage[Any])  # pylint: disable=invalid-name


class AbstractPublisher(AbstractAiopikaResource, Generic[GenericMessageType]):
    """Abstract class for the publisher port for the Aiopika plugin."""

    DEFAULT_OPERATION_TIMEOUT: ClassVar[TimeoutType] = 10.0

    def __init__(self, exchange: Exchange, name: str | None = None) -> None:
        """Initialize the publisher port."""
        super().__init__()
        self._name: str = name or self.__class__.__name__
        self._exchange: Exchange = exchange

    async def setup(self) -> Self:
        """Setup the publisher."""
        await super().setup()
        await self._exchange.setup()
        return self

    async def publish(self, message: GenericMessageType, routing_key: str) -> None:
        """Publish a message."""
        # Transform the message to an Aiopika message
        aiopika_message: Message
        try:
            aiopika_message = message.to_aiopika_message()
        except Exception as exception:
            raise AiopikaPluginBaseError(
                message="Failed to convert the message to an Aiopika message.",
            ) from exception
        # Publish the message
        confirmation: ConfirmationFrameType | DeliveredMessage | None
        try:
            confirmation = await self._exchange.exchange.publish(  # pyright: ignore
                message=aiopika_message,
                routing_key=routing_key,
                mandatory=True,
                timeout=self.DEFAULT_OPERATION_TIMEOUT,
            )
        except Exception as exception:
            raise AiopikaPluginBaseError(
                message="Failed to publish the message.",
            ) from exception

        if confirmation is None:
            raise AiopikaPluginBaseError(
                message="Failed to publish the message.",
            )
        if isinstance(confirmation, Basic.Return):
            raise AiopikaPluginBaseError(
                message="Failed to publish the message.",
            )
