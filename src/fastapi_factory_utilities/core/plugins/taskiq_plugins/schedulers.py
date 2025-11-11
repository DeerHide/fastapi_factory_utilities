"""Scheduler module for fastapi_factory_utilities.

This module provides components and utilities for scheduling tasks using Taskiq, FastAPI, and Redis.
It enables registration, configuration, and management of scheduled tasks in FastAPI applications.
"""

import asyncio
from collections.abc import Coroutine
from typing import Any, Self, cast

import taskiq_fastapi
from fastapi import FastAPI
from structlog.stdlib import get_logger
from taskiq import (
    AsyncBroker,
    AsyncTaskiqDecoratedTask,
    ScheduleSource,
    TaskiqScheduler,
)
from taskiq.api import run_receiver_task, run_scheduler_task
from taskiq.scheduler.created_schedule import CreatedSchedule
from taskiq.scheduler.scheduled_task import ScheduledTask
from taskiq_redis import (
    ListRedisScheduleSource,
    RedisAsyncResultBackend,
    RedisStreamBroker,
)

_logger = get_logger(__package__)


class SchedulerComponent:
    """Scheduler component."""

    def __init__(self, name_suffix: str) -> None:
        """Initialize the scheduler component."""
        self._result_backend: RedisAsyncResultBackend[Any] | None = None
        self._stream_broker: RedisStreamBroker | None = None
        self._scheduler: TaskiqScheduler | None = None
        self._scheduler_source: ListRedisScheduleSource | None = None
        self._dyn_task: AsyncTaskiqDecoratedTask[Any, Any] | None = None
        self._schedule_cron: ScheduledTask | None = None
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

    def configure(self, redis_connection_string: str, app: FastAPI) -> Self:
        """Configure the scheduler component."""
        self._result_backend = RedisAsyncResultBackend(
            redis_url=redis_connection_string,
            prefix_str=f"taskiq_result_backend_{self._name_suffix}",
            result_ex_time=120,
        )
        self._stream_broker = RedisStreamBroker(
            url=redis_connection_string,
            queue_name=f"taskiq_stream_broker_{self._name_suffix}",
            consumer_group_name=f"taskiq_consumer_group_{self._name_suffix}",
        ).with_result_backend(self._result_backend)

        taskiq_fastapi.populate_dependency_context(self._stream_broker, app)

        self._scheduler_source = ListRedisScheduleSource(
            url=redis_connection_string,
            prefix=f"taskiq_schedule_source_{self._name_suffix}",
        )

        self._scheduler = TaskiqScheduler(
            broker=self._stream_broker,
            sources=[self._scheduler_source],
        )

        return self

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
        _logger.info("Scheduling task")
        schedules: list[ScheduledTask] = await self._scheduler_source.get_schedules()
        _logger.info("Schedules retrieved", schedules=schedules)

        self._schedule_cron = next(filter(lambda x: x.task_name == "heartbeat", schedules), None)

        if self._schedule_cron is None:
            _logger.info("No schedules found, scheduling task")
            self._dyn_task = self.get_task("heartbeat")
            task_created: CreatedSchedule[Any] = await self._dyn_task.schedule_by_cron(
                source=self._scheduler_source, cron="* * * * *", msg="every minute"
            )
            self._schedule_cron = task_created.task
            _logger.info("Task scheduled")
        else:
            _logger.info("Schedules found, skipping scheduling")

        _logger.info("Starting worker and scheduler tasks")
        taskiq_fastapi.populate_dependency_context(self._stream_broker, app, app.state)  # type: ignore
        self._worker_task: asyncio.Task[None] = asyncio.create_task(run_receiver_task(self._stream_broker))
        self._scheduler_task: asyncio.Task[None] = asyncio.create_task(run_scheduler_task(self._scheduler))
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
