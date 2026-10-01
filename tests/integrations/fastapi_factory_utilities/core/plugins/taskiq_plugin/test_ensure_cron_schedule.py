"""Integration tests for idempotent cron schedule registration."""

import pytest
from fastapi import FastAPI

from fastapi_factory_utilities.core.plugins.taskiq_plugin.schedulers import SchedulerComponent
from tests.fixtures.redis import RedisFixture


class TestEnsureCronSchedule:
    """Integration tests for SchedulerComponent.ensure_cron_schedule."""

    @pytest.fixture
    def fastapi_app(self) -> FastAPI:
        """Create a FastAPI app for testing."""
        return FastAPI()

    async def test_ensure_cleans_legacy_and_updates_cron(
        self,
        scheduler_component: SchedulerComponent,
        redis_container: RedisFixture,
        fastapi_app: FastAPI,
    ) -> None:
        """Legacy random-id rows converge; a cron change replaces the row."""
        redis_url: str = redis_container.get_connection_url()
        scheduler_component.configure(redis_connection_string=redis_url, app=fastapi_app)

        async def reconcile() -> str:
            """Registered cron task under test."""
            return "ok"

        scheduler_component.register_task(task=reconcile, task_name="reconcile")
        task = scheduler_component.get_task("reconcile")
        await task.schedule_by_cron(
            source=scheduler_component.scheduler_source,
            cron="0 * * * *",
        )

        await scheduler_component.ensure_cron_schedule("reconcile", "0 * * * *")
        await scheduler_component.ensure_cron_schedule("reconcile", "0 * * * *")

        rows = [
            schedule
            for schedule in await scheduler_component.scheduler_source.get_schedules()
            if schedule.task_name == "reconcile"
        ]
        assert len(rows) == 1
        assert rows[0].schedule_id == "reconcile"
        assert rows[0].cron == "0 * * * *"

        await scheduler_component.ensure_cron_schedule("reconcile", "*/5 * * * *")
        rows = [
            schedule
            for schedule in await scheduler_component.scheduler_source.get_schedules()
            if schedule.task_name == "reconcile"
        ]
        assert len(rows) == 1
        assert rows[0].schedule_id == "reconcile"
        assert rows[0].cron == "*/5 * * * *"
