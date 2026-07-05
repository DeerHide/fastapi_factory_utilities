"""Integration tests for pruning stale Taskiq schedules."""

import pytest
from fastapi import FastAPI

from fastapi_factory_utilities.core.plugins.taskiq_plugins.schedulers import SchedulerComponent
from tests.fixtures.redis import RedisFixture


class TestPruneUnregisteredSchedules:
    """Integration tests for SchedulerComponent.prune_unregistered_schedules."""

    @pytest.fixture
    def fastapi_app(self) -> FastAPI:
        """Create a FastAPI app for testing."""
        return FastAPI()

    async def test_prune_unregistered_schedules(
        self,
        scheduler_component: SchedulerComponent,
        redis_container: RedisFixture,
        fastapi_app: FastAPI,
    ) -> None:
        """Remove persisted schedules for tasks that are no longer registered."""
        redis_url: str = redis_container.get_connection_url()
        scheduler_component.configure(redis_connection_string=redis_url, app=fastapi_app)

        async def known_task() -> str:
            """Registered task kept after pruning."""
            return "known"

        async def heartbeat_task() -> str:
            """Legacy task removed from registry but schedule left in Redis."""
            return "heartbeat"

        scheduler_component.register_task(task=known_task, task_name="known_task")
        scheduler_component.register_task(task=heartbeat_task, task_name="heartbeat")

        known = scheduler_component.get_task("known_task")
        await known.schedule_by_cron(
            source=scheduler_component.scheduler_source,
            cron="0 * * * *",
        )
        stale = scheduler_component.get_task("heartbeat")
        await stale.schedule_by_cron(
            source=scheduler_component.scheduler_source,
            cron="* * * * *",
        )

        # Simulate legacy deploy: heartbeat task removed from code but cron remains in Redis.
        del scheduler_component._schedulers_tasks["heartbeat"]  # pylint: disable=protected-access

        removed = await scheduler_component.prune_unregistered_schedules()

        assert removed == 1
        remaining = await scheduler_component.scheduler_source.get_schedules()
        remaining_task_names = {schedule.task_name for schedule in remaining}
        assert "heartbeat" not in remaining_task_names
        assert "known_task" in remaining_task_names
