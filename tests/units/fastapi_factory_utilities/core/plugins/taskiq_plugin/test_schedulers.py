"""Unit tests for SchedulerComponent without a Redis broker."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from fastapi_factory_utilities.core.plugins.taskiq_plugin.schedulers import SchedulerComponent


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
