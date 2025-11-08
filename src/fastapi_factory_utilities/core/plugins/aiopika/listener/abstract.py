"""Provides the abstract class for the listener port for the Aiopika plugin."""

from abc import abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, Generic, Self, TypeVar, cast, get_args

from aio_pika.abc import AbstractIncomingMessage, ConsumerTag, TimeoutType

from ..abstract import AbstractAiopikaResource
from ..message import AbstractMessage
from ..queue import Queue

GenericMessage = TypeVar("GenericMessage", bound=AbstractMessage[Any])


class AbstractListener(AbstractAiopikaResource, Generic[GenericMessage]):
    """Abstract class for the listener port for the Aiopika plugin."""

    DEFAULT_OPERATION_TIMEOUT: ClassVar[TimeoutType] = 10.0

    def __init__(self, queue: Queue, name: str | None = None) -> None:
        """Initialize the listener port."""
        super().__init__()
        self._name: str = name or self.__class__.__name__
        self._queue: Queue = queue
        self._consumer_tag: ConsumerTag | None = None
        generic_args: tuple[Any, ...] = get_args(self.__orig_bases__[0])  # type: ignore
        self._message_type: type[GenericMessage] = generic_args[0]

    async def setup(self) -> Self:
        """Setup the listener."""
        await super().setup()
        await self._queue.setup()
        return self

    async def listen(self) -> None:
        """Listen for messages."""
        assert self._queue.queue is not None
        self._consumer_tag = await self._queue.queue.consume(  # pyright: ignore
            callback=cast(Callable[[AbstractIncomingMessage], Awaitable[Any]], self._on_message),  # pyright: ignore
            exclusive=True,
        )

    async def _on_message(self, incoming_message: AbstractIncomingMessage) -> None:
        """On message."""
        message: GenericMessage = self._message_type.model_validate_json(incoming_message.body)
        message.set_incoming_message(incoming_message=incoming_message)
        await self.on_message(message=message)

    async def close(self) -> None:
        """Close the listener.

        Returns:
            - None: The listener is closed.

        Raises:
            - AiopikaPluginBaseException: If the listener cannot be closed.
        """
        if self._consumer_tag is not None:
            await self._queue.queue.cancel(consumer_tag=self._consumer_tag)

    @abstractmethod
    async def on_message(self, message: GenericMessage) -> None:
        """On message.

        Args:
            message (GenericMessage): The message.

        Returns:
            - None: The message is processed.
        """
        raise NotImplementedError
