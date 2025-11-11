"""Aiopika Plugin Module."""

from .depends import depends_aiopika_robust_connection
from .exceptions import AiopikaPluginBaseError, AiopikaPluginConfigError
from .exchange import Exchange
from .listener import AbstractListener
from .message import AbstractMessage, SenderModel
from .plugins import AiopikaPlugin
from .publisher import AbstractPublisher
from .queue import Queue

__all__: list[str] = [
    "AbstractListener",
    "AbstractMessage",
    "AbstractPublisher",
    "AiopikaPlugin",
    "AiopikaPluginBaseError",
    "AiopikaPluginConfigError",
    "Exchange",
    "Queue",
    "SenderModel",
    "depends_aiopika_robust_connection",
]
