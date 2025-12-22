"""Aiopika Plugin Module."""

from .depends import depends_aiopika_robust_connection
from .exceptions import AiopikaPluginBaseError, AiopikaPluginConfigError
from .exchange import Exchange
from .listener import AbstractListener
from .message import GenericMessage
from .plugins import AiopikaPlugin
from .publisher import AbstractPublisher
from .queue import Queue
from .types import ExchangeName, QueueName, RoutingKey

__all__: list[str] = [
    "AbstractListener",
    "AbstractPublisher",
    "AiopikaPlugin",
    "AiopikaPluginBaseError",
    "AiopikaPluginConfigError",
    "Exchange",
    "ExchangeName",
    "GenericMessage",
    "Queue",
    "QueueName",
    "RoutingKey",
    "depends_aiopika_robust_connection",
]
