"""Scheduler module for fastapi_factory_utilities.

This module provides components and utilities for scheduling tasks using Taskiq, FastAPI, and Redis.
It enables registration, configuration, and management of scheduled tasks in FastAPI applications.
"""

import asyncio
from collections.abc import Coroutine
from datetime import datetime, timezone
from typing import Any, ClassVar, Self, cast

import taskiq_fastapi
from fastapi import FastAPI
from redis.asyncio import Redis
from structlog.stdlib import get_logger
from taskiq import (
    AsyncBroker,
    AsyncTaskiqDecoratedTask,
    ScheduleSource,
    TaskiqScheduler,
)
from taskiq.api import run_receiver_task
from taskiq.cli.scheduler.run import SchedulerLoop
from taskiq.scheduler.scheduled_task import ScheduledTask
from taskiq_redis import (
    ListRedisScheduleSource,
    RedisAsyncResultBackend,
    RedisStreamBroker,
)

_logger = get_logger(__package__)

_CRON_LOCK_TTL_SECONDS: int = 70


def _utc_minute_bucket(dt: datetime) -> datetime:
    """Floor ``dt`` to the UTC minute (seconds and microseconds cleared)."""
    return dt.astimezone(timezone.utc).replace(second=0, microsecond=0)


class MinuteGuardSchedulerLoop(SchedulerLoop):
    """SchedulerLoop that refuses a second cron kick in the same UTC minute."""

    # ponytail: Taskiq's ``is_cron_task_now`` uses
    # ``round((now - last_run).total_seconds()) < 60``, so a wake at
    # ``hh:00:59.995`` after a kick at ``hh:00:00.009`` passes the guard while
    # ``pycron.is_now`` still sees minute 0 and re-fires (stream message lands at
    # ``hh:01:00.00x``). Delete this subclass once Taskiq compares UTC minutes
    # instead of rounded seconds.

    def _is_schedule_ready_to_send(
        self,
        task: ScheduledTask,
        now: datetime,
    ) -> bool:
        """Skip cron tasks already kicked in the current UTC minute.

        Args:
            task: Scheduled task under consideration.
            now: Current wall clock from the scheduler loop.

        Returns:
            ``False`` when a cron task already ran this UTC minute; otherwise
            Taskiq's own readiness result.
        """
        last: datetime | None = self.cron_tasks_last_run.get(task.schedule_id)
        if task.cron is not None and last is not None and _utc_minute_bucket(last) == _utc_minute_bucket(now):
            return False
        return super()._is_schedule_ready_to_send(task, now)


async def run_minute_guard_scheduler_task(scheduler: TaskiqScheduler) -> None:
    """Run the scheduler loop with per-minute cron dedup (replaces ``run_scheduler_task``).

    Starts each schedule source once, then runs
    :class:`MinuteGuardSchedulerLoop` forever — the same shape as Taskiq's
    ``run_scheduler_task``, but with the end-of-minute double-kick guard.

    Args:
        scheduler: Configured Taskiq scheduler (broker + sources).
    """
    for source in scheduler.sources:
        await source.startup()
    while True:
        await MinuteGuardSchedulerLoop(scheduler).run()


class SingleFlightTaskiqScheduler(TaskiqScheduler):
    """TaskiqScheduler that single-flights kicks across processes via Redis SET NX.

    Every process that loads ``TaskiqPlugin`` runs a scheduler loop. Cron
    last-run state is in-memory, so API and worker (and multi-replica) pods
    would each kick the same cron within the matching minute. Before kicking,
    we claim ``<lock_prefix>:taskiq:cron-lock:<task_name>:<YYYYMMDDHHMM>`` with
    ``SET NX EX 70``; losers skip the kick. Keyed by ``task_name`` so a
    duplicate Redis schedule row still sends once.
    """

    _LOCK_TTL_SECONDS: ClassVar[int] = _CRON_LOCK_TTL_SECONDS

    def __init__(
        self,
        broker: AsyncBroker,
        sources: list[ScheduleSource],
        *,
        redis_url: str,
        lock_prefix: str,
    ) -> None:
        """Initialize the single-flight scheduler.

        Args:
            broker: Taskiq broker used to enqueue ready tasks.
            sources: Schedule sources consulted by the scheduler loop.
            redis_url: Redis URL for the cron lock client (same backend as
                the schedule source).
            lock_prefix: Service key prefix (``name_suffix``) so Valkey ACL
                grants ``~<svc>:*`` cover the lock keys.
        """
        super().__init__(broker=broker, sources=sources)
        self._redis_url: str = redis_url
        self._lock_prefix: str = lock_prefix
        self._redis: Redis | None = None

    async def startup(self) -> None:
        """Open the Redis lock client, then start the broker."""
        self._redis = Redis.from_url(self._redis_url)
        await super().startup()

    async def shutdown(self) -> None:
        """Shut down the broker, then close the Redis lock client."""
        await super().shutdown()
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    @classmethod
    def cron_lock_key(cls, lock_prefix: str, task_name: str, now: datetime) -> str:
        """Build the Redis key for a cron kick lock.

        Args:
            lock_prefix: Service key prefix.
            task_name: Registered Taskiq task name.
            now: Wall clock used for the minute bucket.

        Returns:
            Redis key unique per ``(task_name, UTC minute)``.
        """
        minute: str = now.astimezone(timezone.utc).strftime("%Y%m%d%H%M")
        return f"{lock_prefix}:taskiq:cron-lock:{task_name}:{minute}"

    async def _try_acquire_cron_lock(self, task_name: str) -> bool:
        """Claim the per-minute cron lock for ``task_name``.

        Args:
            task_name: Registered Taskiq task name.

        Returns:
            ``True`` when this process won the lock (or Redis is unavailable
            and we fail open); ``False`` when another scheduler already claimed
            this minute.
        """
        if self._redis is None:
            _logger.warning(
                "Cron lock Redis client missing; allowing kick.",
                task_name=task_name,
            )
            return True
        key: str = self.cron_lock_key(
            self._lock_prefix,
            task_name,
            datetime.now(timezone.utc),
        )
        acquired = await self._redis.set(
            key,
            "1",
            nx=True,
            ex=self._LOCK_TTL_SECONDS,
        )
        return bool(acquired)

    async def on_ready(self, source: ScheduleSource, task: ScheduledTask) -> None:
        """Enqueue ``task`` only when this process wins the Redis cron lock.

        Args:
            source: Schedule source that marked the task ready.
            task: Scheduled task to kick.
        """
        if not await self._try_acquire_cron_lock(task.task_name):
            _logger.info(
                "Skipping duplicate scheduled kick; another scheduler won the cron lock.",
                task_name=task.task_name,
                schedule_id=task.schedule_id,
            )
            return
        await super().on_ready(source, task)


class SchedulerComponent:
    """Scheduler component."""

    def __init__(self, name_suffix: str) -> None:
        """Initialize the scheduler component."""
        self._result_backend: RedisAsyncResultBackend[Any] | None = None
        self._stream_broker: RedisStreamBroker | None = None
        self._scheduler: TaskiqScheduler | None = None
        self._scheduler_source: ListRedisScheduleSource | None = None
        self._schedulers_tasks: dict[str, AsyncTaskiqDecoratedTask[Any, Any]] = {}
        self._name_suffix: str = name_suffix

    def register_task(self, task: Coroutine[Any, Any, Any], task_name: str) -> None:
        """Register a task.

        Args:
            task: The task to register.
            task_name: The name of the task.

        Raises:
            ValueError: If the task is already registered.
            ValueError: If the stream broker is not initialized.
        """
        if self._stream_broker is None:
            raise ValueError("Stream broker is not initialized")

        if task_name in self._schedulers_tasks:
            raise ValueError(f"Task {task_name} already registered")

        self._schedulers_tasks[task_name] = self._stream_broker.register_task(task, task_name)  # type: ignore

    def get_task(self, task_name: str) -> AsyncTaskiqDecoratedTask[Any, Any]:
        """Get a task.

        Args:
            task_name: The name of the task.

        Returns:
            AsyncTaskiqDecoratedTask: The task.

        Raises:
            ValueError: If the task is not registered.
        """
        if task_name not in self._schedulers_tasks:
            raise ValueError(f"Task {task_name} not registered")
        return self._schedulers_tasks[task_name]

    def configure(
        self,
        redis_connection_string: str,
        app: FastAPI,
        *,
        stream_maxlen: int = 10_000,
    ) -> Self:
        """Configure the scheduler component."""
        # ponytail: keys must start with ``<name_suffix>:`` so per-service Valkey ACL
        # grants (~<svc>:*) cover stream, result, and schedule prefixes.
        key_prefix = self._name_suffix
        self._result_backend = RedisAsyncResultBackend(
            redis_url=redis_connection_string,
            prefix_str=f"{key_prefix}:taskiq:result",
            result_ex_time=120,
        )
        self._stream_broker = RedisStreamBroker(
            url=redis_connection_string,
            queue_name=f"{key_prefix}:taskiq:stream",
            consumer_group_name=f"{key_prefix}:taskiq:consumers",
            maxlen=stream_maxlen,
            approximate=True,
        ).with_result_backend(self._result_backend)

        taskiq_fastapi.populate_dependency_context(self._stream_broker, app)

        self._scheduler_source = ListRedisScheduleSource(
            url=redis_connection_string,
            prefix=f"{key_prefix}:taskiq:schedule",
        )

        self._scheduler = SingleFlightTaskiqScheduler(
            broker=self._stream_broker,
            sources=[self._scheduler_source],
            redis_url=redis_connection_string,
            lock_prefix=key_prefix,
        )

        return self

    async def prune_unregistered_schedules(self) -> int:
        """Delete persisted schedules whose task is no longer registered.

        Returns:
            int: Number of stale schedules removed.

        Raises:
            ValueError: If the scheduler source is not initialized.
        """
        if self._scheduler_source is None:
            raise ValueError("Scheduler source is not initialized")
        removed = 0
        for schedule in await self._scheduler_source.get_schedules():
            if schedule.task_name not in self._schedulers_tasks:
                await self._scheduler_source.delete_schedule(schedule.schedule_id)
                _logger.warning(
                    "Pruned stale schedule for unregistered task",
                    task_name=schedule.task_name,
                    schedule_id=schedule.schedule_id,
                )
                removed += 1
        return removed

    async def startup(self, app: FastAPI) -> None:
        """Start the scheduler."""
        if self._result_backend is None:
            raise ValueError("Result backend is not initialized")
        if self._stream_broker is None:
            raise ValueError("Stream broker is not initialized")
        if self._scheduler is None:
            raise ValueError("Scheduler is not initialized")
        if self._scheduler_source is None:
            raise ValueError("Scheduler source is not initialized")

        _logger.info("Starting scheduler")
        await self._result_backend.startup()
        await self._stream_broker.startup()
        await self._scheduler.startup()
        _logger.info("Scheduler started")
        _logger.info("Starting worker and scheduler tasks")
        # Depends resolve via request.app.state (scope["app"]); do not pass Starlette
        # State here — taskiq_fastapi does copy.copy(asgi_state) and State recurses.
        taskiq_fastapi.populate_dependency_context(self._stream_broker, app)
        self._worker_task: asyncio.Task[None] = asyncio.create_task(run_receiver_task(self._stream_broker))
        self._scheduler_task: asyncio.Task[None] = asyncio.create_task(
            run_minute_guard_scheduler_task(self._scheduler),
        )
        _logger.info("Worker and scheduler tasks started")

    async def shutdown(self) -> None:
        """Stop the scheduler."""
        _logger.info("Stopping worker")
        self._worker_task.cancel()
        self._scheduler_task.cancel()
        try:
            await self._worker_task
        except (asyncio.CancelledError, RuntimeError) as e:
            _logger.info("Worker task cancelled", error=e)
        try:
            await self._scheduler_task
        except (asyncio.CancelledError, RuntimeError) as e:
            _logger.info("Scheduler task cancelled", error=e)

        while not self._worker_task.done() or not self._scheduler_task.done():
            await asyncio.sleep(0.1)

        _logger.info("Stopping scheduler")
        if self._scheduler is not None:
            await self._scheduler.shutdown()
        if self._stream_broker is not None:
            await self._stream_broker.shutdown()
        if self._result_backend is not None:
            await self._result_backend.shutdown()
        _logger.info("Scheduler stopped")

    @property
    def scheduler(self) -> TaskiqScheduler:
        """Get the scheduler."""
        return cast(TaskiqScheduler, self._scheduler)

    @property
    def broker(self) -> AsyncBroker:
        """Get the broker."""
        return cast(AsyncBroker, self._stream_broker)

    @property
    def scheduler_source(self) -> ScheduleSource:
        """Get the scheduler source."""
        return cast(ScheduleSource, self._scheduler_source)
