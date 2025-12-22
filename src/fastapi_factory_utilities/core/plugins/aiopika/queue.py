"""Provides the queue for the Aiopika plugin."""

from typing import ClassVar, Self

from aio_pika.abc import AbstractQueue, TimeoutType

from .abstract import AbstractAiopikaResource
from .exceptions import AiopikaPluginBaseError, AiopikaPluginQueueNotDeclaredError
from .exchange import Exchange
from .types import QueueName, RoutingKey


class Queue(AbstractAiopikaResource):
    """Queue."""

    DEFAULT_OPERATION_TIMEOUT: ClassVar[TimeoutType] = 10.0

    def __init__(  # pylint: disable=too-many-arguments # noqa: PLR0913
        self,
        name: QueueName,
        exchange: Exchange,
        routing_key: RoutingKey,
        durable: bool = True,
        auto_delete: bool = False,
        exclusive: bool = True,
        timeout: TimeoutType = DEFAULT_OPERATION_TIMEOUT,
    ) -> None:
        """Initialize the queue."""
        super().__init__()
        # Initialize the queue properties
        self._name: QueueName = name
        self._routing_key: RoutingKey = routing_key
        self._durable: bool = durable
        self._auto_delete: bool = auto_delete
        self._exclusive: bool = exclusive
        self._timeout: TimeoutType = timeout
        # Behavior properties
        self._exchange: Exchange = exchange
        self._queue: AbstractQueue | None = None

    @property
    def queue(self) -> AbstractQueue:
        """Get the Aiopika queue."""
        if self._queue is None:
            raise AiopikaPluginQueueNotDeclaredError(
                message="Queue not declared.",
                queue=self._name,
            )
        return self._queue

    async def _declare(self) -> Self:
        """Declare the queue."""
        assert self._channel is not None
        try:
            self._queue = await self._channel.declare_queue(  # pyright: ignore
                name=self._name,
                durable=self._durable,
                auto_delete=self._auto_delete,
                exclusive=self._exclusive,
                timeout=self._timeout,
            )
        except Exception as exception:
            raise AiopikaPluginBaseError(
                message="Failed to declare the queue.",
            ) from exception
        return self

    async def _bind(self) -> Self:
        """Bind the queue to the exchange."""
        assert self._queue is not None
        try:
            await self._queue.bind(  # pyright: ignore
                exchange=self._exchange.exchange,
                routing_key=self._routing_key,
                timeout=self._timeout,
            )
        except Exception as exception:
            raise AiopikaPluginBaseError(
                message="Failed to bind the queue to the exchange.",
            ) from exception
        return self

    async def setup(self) -> Self:
        """Setup the queue."""
        await super().setup()
        if self._queue is None:
            await self._declare()
        await self._bind()
        return self
