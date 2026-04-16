"""Provides the abstract class for the listener port for the Aiopika plugin."""

import json
from abc import abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, Generic, Self, TypeVar, cast, get_args

from aio_pika.abc import AbstractIncomingMessage, ConsumerTag, TimeoutType
from pydantic import ValidationError
from structlog.stdlib import BoundLogger, get_logger

from ..abstract import AbstractAiopikaResource
from ..message import GenericMessage
from ..queue import Queue

_logger: BoundLogger = get_logger(__package__)

GenericMessageType = TypeVar("GenericMessageType", bound=GenericMessage[Any])  # pylint: disable=invalid-name


class AbstractListener(AbstractAiopikaResource, Generic[GenericMessageType]):
    """Abstract class for the listener port for the Aiopika plugin."""

    DEFAULT_OPERATION_TIMEOUT: ClassVar[TimeoutType] = 10.0

    def __init__(self, queue: Queue, name: str | None = None, exclusive: bool | None = None) -> None:
        """Initialize the listener port."""
        super().__init__()
        self._name: str = name or self.__class__.__name__
        self._queue: Queue = queue
        self._consumer_tag: ConsumerTag | None = None
        self._exclusive: bool = queue.exclusive if exclusive is None else exclusive
        generic_args: tuple[Any, ...] = get_args(self.__orig_bases__[0])  # type: ignore
        self._message_type: type[GenericMessageType] = generic_args[0]

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
            exclusive=self._exclusive,
        )

    async def _on_message(self, incoming_message: AbstractIncomingMessage) -> None:
        """On message."""
        body: str
        json_body: dict[str, Any]
        message: GenericMessageType
        # Decode the message body from bytes to JSON
        try:
            body = incoming_message.body.decode("utf-8")
            json_body = json.loads(body)
        except json.JSONDecodeError as e:
            _logger.error("Failed to decode message", error=e, body=incoming_message.body)
            await incoming_message.reject(requeue=True)
            return
        except Exception as e:  # pylint: disable=broad-exception-caught
            _logger.error("Failed to decode message", error=e, body=incoming_message.body)
            await incoming_message.reject(requeue=True)
            return
        # Validate the message body to the message type
        try:
            message = self._message_type.model_validate(json_body)
        except ValidationError as e:
            _logger.error("Failed to validate message", error=e, body=body)
            await incoming_message.reject(requeue=True)
            return
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
    async def on_message(self, message: GenericMessageType) -> None:
        """On message.

        Args:
            message (GenericMessageType): The message.

        Returns:
            - None: The message is processed.
        """
        raise NotImplementedError
