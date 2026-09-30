"""Unit tests for SchedulerComponent without a Redis broker."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from fastapi_factory_utilities.core.plugins.taskiq_plugin.schedulers import (
    SchedulerComponent,
    SingleFlightTaskiqScheduler,
)


class TestSchedulerComponentUnits:
    """Value-error and mock-driven paths for ``SchedulerComponent``."""

    def test_register_task_requires_broker(self) -> None:
        """register_task before configure raises."""
        component = SchedulerComponent(name_suffix="svc")
        with pytest.raises(ValueError, match="Stream broker"):
            component.register_task(MagicMock(), task_name="heartbeat")

    def test_register_task_rejects_duplicate_name(self) -> None:
        """A second register of the same name raises."""
        component = SchedulerComponent(name_suffix="svc")
        broker = MagicMock()
        broker.register_task.return_value = MagicMock()
        component._stream_broker = broker

        component.register_task(MagicMock(), task_name="heartbeat")
        with pytest.raises(ValueError, match="already registered"):
            component.register_task(MagicMock(), task_name="heartbeat")

    def test_get_task_missing_raises(self) -> None:
        """get_task on an unknown name raises."""
        component = SchedulerComponent(name_suffix="svc")
        with pytest.raises(ValueError, match="not registered"):
            component.get_task("missing")

    def test_get_task_returns_registered(self) -> None:
        """get_task returns the decorated task after register."""
        component = SchedulerComponent(name_suffix="svc")
        decorated = MagicMock()
        broker = MagicMock()
        broker.register_task.return_value = decorated
        component._stream_broker = broker

        component.register_task(MagicMock(), task_name="heartbeat")
        assert component.get_task("heartbeat") is decorated

    @pytest.mark.asyncio
    async def test_prune_requires_scheduler_source(self) -> None:
        """prune_unregistered_schedules before configure raises."""
        component = SchedulerComponent(name_suffix="svc")
        with pytest.raises(ValueError, match="Scheduler source"):
            await component.prune_unregistered_schedules()

    @pytest.mark.asyncio
    async def test_prune_deletes_unregistered_schedules(self) -> None:
        """Schedules whose task is gone are deleted."""
        component = SchedulerComponent(name_suffix="svc")
        keep = MagicMock(task_name="keep", schedule_id="1")
        stale = MagicMock(task_name="stale", schedule_id="2")
        source = AsyncMock()
        source.get_schedules.return_value = [keep, stale]
        component._scheduler_source = source

        component._schedulers_tasks["keep"] = MagicMock()

        removed = await component.prune_unregistered_schedules()
        assert removed == 1
        source.delete_schedule.assert_awaited_once_with("2")

    @pytest.mark.asyncio
    async def test_startup_requires_configure(self) -> None:
        """Startup before configure raises for the missing result backend."""
        component = SchedulerComponent(name_suffix="svc")
        with pytest.raises(ValueError, match="Result backend"):
            await component.startup(FastAPI())

    def test_configure_passes_stream_maxlen_to_broker(self) -> None:
        """Configure wires RedisStreamBroker with maxlen to cap stream growth."""
        component = SchedulerComponent(name_suffix="review")
        with patch(
            "fastapi_factory_utilities.core.plugins.taskiq_plugin.schedulers.RedisStreamBroker",
        ) as broker_cls:
            broker_cls.return_value.with_result_backend.return_value = MagicMock()
            component.configure("redis://localhost:6379/0", FastAPI(), stream_maxlen=10_000)
        broker_cls.assert_called_once_with(
            url="redis://localhost:6379/0",
            queue_name="review:taskiq:stream",
            consumer_group_name="review:taskiq:consumers",
            maxlen=10_000,
            approximate=True,
        )
        assert isinstance(component.scheduler, SingleFlightTaskiqScheduler)

    @pytest.mark.asyncio
    async def test_startup_and_shutdown_with_mocks(self) -> None:
        """Startup wires worker/scheduler tasks; shutdown cancels them."""
        component = SchedulerComponent(name_suffix="svc")
        component._result_backend = AsyncMock()

        component._stream_broker = AsyncMock()

        component._scheduler = AsyncMock()

        component._scheduler_source = AsyncMock()

        async def _hang(*_args: object) -> None:
            await asyncio.sleep(60)

        with (
            patch(
                "fastapi_factory_utilities.core.plugins.taskiq_plugin.schedulers.run_receiver_task",
                _hang,
            ),
            patch(
                "fastapi_factory_utilities.core.plugins.taskiq_plugin.schedulers.run_scheduler_task",
                _hang,
            ),
            patch("taskiq_fastapi.populate_dependency_context"),
        ):
            await component.startup(FastAPI())
            assert component.broker is component._stream_broker

            assert component.scheduler is component._scheduler

            assert component.scheduler_source is component._scheduler_source

            await component.shutdown()


class TestSingleFlightTaskiqScheduler:
    """Redis SET NX gate before kicking a scheduled task."""

    def _scheduler(self) -> SingleFlightTaskiqScheduler:
        """Build a scheduler with a mock broker and no live Redis."""
        broker = MagicMock()
        return SingleFlightTaskiqScheduler(
            broker=broker,
            sources=[],
            redis_url="redis://localhost:6379/0",
            lock_prefix="youtube-integration",
        )

    def test_cron_lock_key_uses_task_name_and_utc_minute(self) -> None:
        """Lock key is per task_name and UTC minute, not schedule_id."""
        now = datetime(2026, 9, 30, 16, 0, 42, tzinfo=timezone.utc)
        key = SingleFlightTaskiqScheduler.cron_lock_key(
            "youtube-integration",
            "system_synchronization_dispatch",
            now,
        )
        assert key == "youtube-integration:taskiq:cron-lock:system_synchronization_dispatch:202609301600"

    @pytest.mark.asyncio
    async def test_on_ready_skips_kick_when_lock_lost(self) -> None:
        """A lost SET NX must not enqueue the task."""
        scheduler = self._scheduler()
        redis = AsyncMock()
        redis.set = AsyncMock(return_value=None)
        scheduler._redis = redis

        source = AsyncMock()
        source.pre_send = AsyncMock()
        source.post_send = AsyncMock()
        task = MagicMock(
            task_name="system_synchronization_dispatch",
            schedule_id="sched-1",
            task_id=None,
            labels={},
            args=(),
            kwargs={},
        )

        with patch("taskiq.scheduler.scheduler.AsyncKicker") as kicker_cls:
            await scheduler.on_ready(source, task)

        kicker_cls.assert_not_called()
        redis.set.assert_awaited_once()
        set_kwargs = redis.set.await_args
        assert set_kwargs.kwargs["nx"] is True
        assert set_kwargs.kwargs["ex"] == SingleFlightTaskiqScheduler._LOCK_TTL_SECONDS

    @pytest.mark.asyncio
    async def test_on_ready_kicks_when_lock_won(self) -> None:
        """A won SET NX enqueues the task once via AsyncKicker."""
        scheduler = self._scheduler()
        redis = AsyncMock()
        redis.set = AsyncMock(return_value=True)
        scheduler._redis = redis

        source = AsyncMock()
        source.pre_send = AsyncMock()
        source.post_send = AsyncMock()
        task = MagicMock(
            task_name="system_synchronization_dispatch",
            schedule_id="sched-1",
            task_id=None,
            labels={},
            args=(),
            kwargs={},
        )

        kicker = MagicMock()
        kicker.with_labels.return_value = kicker
        kicker.with_task_id.return_value = kicker
        kicker.kiq = AsyncMock()

        with patch("taskiq.scheduler.scheduler.AsyncKicker", return_value=kicker) as kicker_cls:
            await scheduler.on_ready(source, task)

        kicker_cls.assert_called_once()
        kicker.kiq.assert_awaited_once()
        redis.set.assert_awaited_once()
