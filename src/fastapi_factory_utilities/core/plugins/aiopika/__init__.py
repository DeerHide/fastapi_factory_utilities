"""Aiopika Plugin Module."""

from .builders import EventRoutingKeyBuilder, ExchangeNameBuilder, ListenerRoutingKeyBuilder, QueueNameBuilder
from .concurrency import (
    ConcurrencyGate,
    LocalConcurrencyGate,
    get_concurrency_gate,
    reset_concurrency_gate_for_tests,
    set_concurrency_gate,
)
from .delay_queue import (
    build_main_queue_dead_letter_arguments,
    build_retry_queue_arguments,
    declare_delay_retry_topology,
    declare_queue_with_optional_recreate,
)
from .delivery import MessageDeliveryOutcome, settle_message
from .depends import depends_aiopika_robust_connection
from .exceptions import AiopikaPluginBaseError, AiopikaPluginConfigError
from .exchange import Exchange
from .listener import AbstractListener, AbstractManagedListener
from .message import GenericMessage
from .plugins import AiopikaPlugin
from .publisher import AbstractPublisher
from .queue import Queue
from .telemetry import (
    ConsumerTelemetry,
    NoOpConsumerTelemetry,
    OpenTelemetryConsumerTelemetry,
)
from .types import ExchangeName, PartStr, QueueName, RoutingKey

__all__: list[str] = [
    "AbstractListener",
    "AbstractManagedListener",
    "AbstractPublisher",
    "AiopikaPlugin",
    "AiopikaPluginBaseError",
    "AiopikaPluginConfigError",
    "ConcurrencyGate",
    "ConsumerTelemetry",
    "EventRoutingKeyBuilder",
    "Exchange",
    "ExchangeName",
    "ExchangeNameBuilder",
    "GenericMessage",
    "ListenerRoutingKeyBuilder",
    "LocalConcurrencyGate",
    "MessageDeliveryOutcome",
    "NoOpConsumerTelemetry",
    "OpenTelemetryConsumerTelemetry",
    "PartStr",
    "Queue",
    "QueueName",
    "QueueNameBuilder",
    "RoutingKey",
    "build_main_queue_dead_letter_arguments",
    "build_retry_queue_arguments",
    "declare_delay_retry_topology",
    "declare_queue_with_optional_recreate",
    "depends_aiopika_robust_connection",
    "get_concurrency_gate",
    "reset_concurrency_gate_for_tests",
    "set_concurrency_gate",
    "settle_message",
]
