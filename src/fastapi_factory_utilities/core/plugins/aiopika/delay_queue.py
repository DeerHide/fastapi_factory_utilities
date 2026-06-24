"""Dead-letter delay retry queue topology helpers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import aiormq.exceptions
from structlog.stdlib import BoundLogger, get_logger

_logger: BoundLogger = get_logger(__package__)

ChannelFactory = Callable[[], Awaitable[Any]]
ChannelReset = Callable[[], None]

_DEFAULT_DEAD_LETTER_EXCHANGE: str = ""


async def declare_queue_with_optional_recreate(  # noqa: PLR0913
    acquire_channel: ChannelFactory,
    *,
    reset_channel: ChannelReset | None = None,
    queue_name: str,
    durable: bool,
    exclusive: bool,
    arguments: dict[str, Any] | None,
    force_recreate_on_conflict: bool,
    timeout: float | None = None,
) -> Any:
    """Declare a queue, optionally deleting and recreating it on argument mismatch.

    RabbitMQ closes the channel on ``PRECONDITION_FAILED``; pass ``reset_channel`` to
    clear any cached channel handle before delete/redeclare.

    Args:
        acquire_channel: Async callable returning an open aio-pika channel.
        reset_channel: Optional callable that clears a cached channel after it was closed.
        queue_name: Queue to declare.
        durable: Durable flag passed to ``queue_declare``.
        exclusive: Exclusive flag passed to ``queue_declare``.
        arguments: Optional queue arguments (DLX, TTL, etc.).
        force_recreate_on_conflict: When true, delete and redeclare on mismatch.
        timeout: Optional declare timeout.

    Returns:
        Declared aio-pika queue instance.

    Raises:
        aiormq.exceptions.ChannelPreconditionFailed: When arguments differ and force is disabled.
    """
    declare_kwargs: dict[str, Any] = {
        "name": queue_name,
        "durable": durable,
        "exclusive": exclusive,
    }
    if arguments:
        declare_kwargs["arguments"] = arguments
    if timeout is not None:
        declare_kwargs["timeout"] = timeout

    channel = await acquire_channel()
    try:
        return await channel.declare_queue(**declare_kwargs)
    except aiormq.exceptions.ChannelPreconditionFailed as exc:
        if not force_recreate_on_conflict:
            _logger.error(
                "Queue declaration failed due to argument mismatch; delete the queue or enable "
                "force_recreate_on_conflict.",
                queue=queue_name,
                error=str(exc),
            )
            raise
        _logger.warning(
            "Queue arguments mismatch; deleting queue when empty and recreating.",
            queue=queue_name,
            error=str(exc),
        )
        if reset_channel is not None:
            reset_channel()
        channel = await acquire_channel()
        try:
            await channel.queue_delete(queue_name, if_empty=True)
        except Exception as delete_exc:
            _logger.error(
                "Queue arguments mismatch and queue could not be deleted (may still contain messages).",
                queue=queue_name,
                error=str(delete_exc),
            )
            raise exc from delete_exc
        return await channel.declare_queue(**declare_kwargs)


def build_main_queue_dead_letter_arguments(*, retry_queue_name: str) -> dict[str, Any]:
    """Build queue arguments routing rejected messages to a delayed retry queue.

    Args:
        retry_queue_name: Name of the TTL retry queue used as dead-letter target.

    Returns:
        RabbitMQ queue arguments for ``x-dead-letter-exchange`` routing.
    """
    return {
        "x-dead-letter-exchange": _DEFAULT_DEAD_LETTER_EXCHANGE,
        "x-dead-letter-routing-key": retry_queue_name,
    }


def build_retry_queue_arguments(*, main_queue_name: str, retry_delay_ms: int) -> dict[str, Any]:
    """Build queue arguments for a TTL retry queue that dead-letters back to the main queue.

    Args:
        main_queue_name: Primary consumer queue name.
        retry_delay_ms: Message TTL in milliseconds before redelivery to the main queue.

    Returns:
        RabbitMQ queue arguments for delayed retry topology.
    """
    return {
        "x-message-ttl": retry_delay_ms,
        "x-dead-letter-exchange": _DEFAULT_DEAD_LETTER_EXCHANGE,
        "x-dead-letter-routing-key": main_queue_name,
    }


async def declare_delay_retry_topology(  # noqa: PLR0913
    acquire_channel: ChannelFactory,
    *,
    main_queue_name: str,
    retry_queue_name: str,
    retry_delay_ms: int,
    reset_channel: ChannelReset | None = None,
    force_recreate_on_conflict: bool = True,
    durable: bool = True,
    exclusive: bool = False,
    timeout: float | None = None,
) -> None:
    """Declare the delayed retry queue used with ``MessageDeliveryOutcome.REQUEUE_DELAYED``.

    The main queue must be declared separately with :func:`build_main_queue_dead_letter_arguments`.
    Rejected messages (``requeue=False``) route to ``retry_queue_name``, expire after
    ``retry_delay_ms``, then dead-letter back to ``main_queue_name``.

    Args:
        acquire_channel: Async callable returning an open aio-pika channel.
        main_queue_name: Primary consumer queue name.
        retry_queue_name: Delayed retry queue name.
        retry_delay_ms: Retry delay in milliseconds.
        reset_channel: Optional callable clearing a cached channel after broker closes it.
        force_recreate_on_conflict: Delete and recreate retry queue on argument mismatch.
        durable: Durable flag for the retry queue declaration.
        exclusive: Exclusive flag for the retry queue declaration.
        timeout: Optional declare timeout.
    """
    await declare_queue_with_optional_recreate(
        acquire_channel,
        reset_channel=reset_channel,
        queue_name=retry_queue_name,
        durable=durable,
        exclusive=exclusive,
        arguments=build_retry_queue_arguments(
            main_queue_name=main_queue_name,
            retry_delay_ms=retry_delay_ms,
        ),
        force_recreate_on_conflict=force_recreate_on_conflict,
        timeout=timeout,
    )
