"""Aiopika Plugin Module."""

from .builders import EventRoutingKeyBuilder, ExchangeNameBuilder, ListenerRoutingKeyBuilder, QueueNameBuilder
from .depends import depends_aiopika_robust_connection
from .exceptions import AiopikaPluginBaseError, AiopikaPluginConfigError
from .exchange import Exchange
from .listener import AbstractListener
from .message import GenericMessage
from .plugins import AiopikaPlugin
from .publisher import AbstractPublisher
from .queue import Queue
from .types import ExchangeName, PartStr, QueueName, RoutingKey

__all__: list[str] = [
    "AbstractListener",
    "AbstractPublisher",
    "AiopikaPlugin",
    "AiopikaPluginBaseError",
    "AiopikaPluginConfigError",
    "EventRoutingKeyBuilder",
    "Exchange",
    "ExchangeName",
    "ExchangeNameBuilder",
    "GenericMessage",
    "ListenerRoutingKeyBuilder",
    "PartStr",
    "Queue",
    "QueueName",
    "QueueNameBuilder",
    "RoutingKey",
    "depends_aiopika_robust_connection",
]
