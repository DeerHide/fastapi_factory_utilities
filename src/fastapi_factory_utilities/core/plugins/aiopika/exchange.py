"""Provides the abstract class for the exchange port for the Aiopika plugin."""

from typing import ClassVar, Self

from aio_pika.abc import AbstractExchange, ExchangeType, TimeoutType

from .abstract import AbstractAiopikaResource
from .exceptions import AiopikaPluginBaseError, AiopikaPluginExchangeNotDeclaredError
from .types import ExchangeName


class Exchange(AbstractAiopikaResource):
    """Abstract class for the exchange port for the Aiopika plugin."""

    DEFAULT_OPERATION_TIMEOUT: ClassVar[TimeoutType] = 10.0

    def __init__(  # pylint: disable=too-many-arguments # noqa: PLR0913
        self,
        name: ExchangeName,
        exchange_type: ExchangeType,
        durable: bool = True,
        auto_delete: bool = False,
        internal: bool = False,
        passive: bool = False,
        timeout: TimeoutType = DEFAULT_OPERATION_TIMEOUT,
    ) -> None:
        """Initialize the exchange port."""
        super().__init__()
        self._name: ExchangeName = name
        self._exchange_type: ExchangeType = exchange_type
        self._durable: bool = durable
        self._auto_delete: bool = auto_delete
        self._internal: bool = internal
        self._passive: bool = passive
        self._timeout: TimeoutType = timeout
        self._aiopika_exchange: AbstractExchange | None = None
        self._is_declared: bool = False

    @property
    def exchange(self) -> AbstractExchange:
        """Get the Aiopika exchange."""
        if self._aiopika_exchange is None:
            raise AiopikaPluginExchangeNotDeclaredError(message="Exchange not declared.", exchange=self._name)
        return self._aiopika_exchange

    async def _declare(self) -> Self:
        """Declare the exchange."""
        assert self._channel is not None
        try:
            self._aiopika_exchange = await self._channel.declare_exchange(  # pyright: ignore
                name=self._name,
                type=self._exchange_type,
                durable=self._durable,
                auto_delete=self._auto_delete,
                internal=self._internal,
                passive=self._passive,
                timeout=self._timeout,
            )
        except Exception as exception:
            raise AiopikaPluginBaseError(
                message="Failed to declare the exchange.",
            ) from exception
        return self

    async def setup(self) -> Self:
        """Setup the exchange."""
        await super().setup()
        if self._aiopika_exchange is None:
            await self._declare()
        return self
