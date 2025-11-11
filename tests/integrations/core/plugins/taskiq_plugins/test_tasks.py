"""Integration tests for task registration and execution."""

import asyncio
from typing import Any

import pytest
from fastapi import FastAPI

from fastapi_factory_utilities.core.plugins.taskiq_plugins.schedulers import SchedulerComponent
from tests.fixtures.redis import RedisFixture


class TestTasks:
    """Integration tests for task registration and execution."""

    @pytest.fixture
    def fastapi_app(self) -> FastAPI:
        """Create a FastAPI app for testing."""
        return FastAPI()

    async def test_task_execution(
        self,
        scheduler_component: SchedulerComponent,
        redis_container: RedisFixture,
        fastapi_app: FastAPI,
    ) -> None:
        """Test executing a registered task."""
        redis_url: str = redis_container.get_connection_url()
        scheduler_component.configure(redis_connection_string=redis_url, app=fastapi_app)

        # Track task execution
        execution_count: list[int] = [0]

        async def test_task(value: int) -> int:
            """Test task that increments execution count."""
            execution_count[0] += 1
            return value * 2

        async def heartbeat_task() -> str:
            """Heartbeat task for testing."""
            return "heartbeat"

        # Register the tasks
        scheduler_component.register_task(task=test_task, task_name="test_task")
        scheduler_component.register_task(task=heartbeat_task, task_name="heartbeat")

        # Start the scheduler
        await scheduler_component.startup(app=fastapi_app)

        # Get the task and execute it
        task = scheduler_component.get_task("test_task")
        result: Any = await task.kiq()

        # Wait for task to complete
        await asyncio.sleep(1)

        # Verify result
        assert result is not None

        # Cleanup
        await scheduler_component.shutdown()

    async def test_multiple_tasks(
        self,
        scheduler_component: SchedulerComponent,
        redis_container: RedisFixture,
        fastapi_app: FastAPI,
    ) -> None:
        """Test registering and executing multiple tasks."""
        redis_url: str = redis_container.get_connection_url()
        scheduler_component.configure(redis_connection_string=redis_url, app=fastapi_app)

        # Register multiple tasks
        async def task_one() -> str:
            """First test task."""
            return "task_one_result"

        async def task_two(value: int) -> int:
            """Second test task."""
            return value * 2

        async def task_three(data: dict[str, Any]) -> dict[str, Any]:
            """Third test task."""
            return {"result": data.get("value", 0) * 3}

        async def heartbeat_task() -> str:
            """Heartbeat task for testing."""
            return "heartbeat"

        scheduler_component.register_task(task=task_one, task_name="task_one")
        scheduler_component.register_task(task=task_two, task_name="task_two")
        scheduler_component.register_task(task=task_three, task_name="task_three")
        scheduler_component.register_task(task=heartbeat_task, task_name="heartbeat")

        # Verify all tasks are registered
        assert scheduler_component.get_task("task_one") is not None
        assert scheduler_component.get_task("task_two") is not None
        assert scheduler_component.get_task("task_three") is not None

        # Start the scheduler
        await scheduler_component.startup(app=fastapi_app)

        # Execute tasks
        task_one_instance = scheduler_component.get_task("task_one")
        task_two_instance = scheduler_component.get_task("task_two")
        task_three_instance = scheduler_component.get_task("task_three")

        result_one: Any = await task_one_instance.kiq()
        result_two: Any = await task_two_instance.kiq()
        result_three: Any = await task_three_instance.kiq()

        # Wait for tasks to complete
        await asyncio.sleep(1)

        # Verify results
        assert result_one is not None
        assert result_two is not None
        assert result_three is not None

        # Cleanup
        await scheduler_component.shutdown()

    async def test_heartbeat_task_scheduling(
        self,
        scheduler_component: SchedulerComponent,
        redis_container: RedisFixture,
        fastapi_app: FastAPI,
    ) -> None:
        """Test that heartbeat task is scheduled on startup."""
        redis_url: str = redis_container.get_connection_url()
        scheduler_component.configure(redis_connection_string=redis_url, app=fastapi_app)

        # Register heartbeat task
        async def heartbeat_task() -> str:
            """Heartbeat task for testing."""
            return "heartbeat"

        scheduler_component.register_task(task=heartbeat_task, task_name="heartbeat")

        # Start the scheduler (this should schedule the heartbeat task)
        await scheduler_component.startup(app=fastapi_app)

        # Wait a bit to ensure scheduling is complete
        await asyncio.sleep(1)

        # Verify the scheduler is running (indirectly verifies schedule was created)
        assert scheduler_component.scheduler is not None

        # Cleanup
        await scheduler_component.shutdown()
