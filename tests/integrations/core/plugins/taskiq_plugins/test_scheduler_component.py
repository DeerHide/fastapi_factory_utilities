"""Integration tests for the SchedulerComponent."""

import asyncio

import pytest
from fastapi import FastAPI

from fastapi_factory_utilities.core.plugins.taskiq_plugins.schedulers import SchedulerComponent
from tests.fixtures.redis import RedisFixture


class TestSchedulerComponent:
    """Integration tests for the SchedulerComponent."""

    @pytest.fixture
    def fastapi_app(self) -> FastAPI:
        """Create a FastAPI app for testing."""
        return FastAPI()

    async def test_configure(
        self,
        scheduler_component: SchedulerComponent,
        redis_container: RedisFixture,
        fastapi_app: FastAPI,
    ) -> None:
        """Test configuring the scheduler component."""
        redis_url: str = redis_container.get_connection_url()
        scheduler_component.configure(redis_connection_string=redis_url, app=fastapi_app)

        assert scheduler_component.scheduler is not None
        assert scheduler_component.broker is not None
        assert scheduler_component.scheduler_source is not None

    async def test_startup_and_shutdown(
        self,
        scheduler_component: SchedulerComponent,
        redis_container: RedisFixture,
        fastapi_app: FastAPI,
    ) -> None:
        """Test starting and shutting down the scheduler component."""
        redis_url: str = redis_container.get_connection_url()
        scheduler_component.configure(redis_connection_string=redis_url, app=fastapi_app)

        # Register a heartbeat task before startup
        async def heartbeat_task() -> str:
            """Heartbeat task for testing."""
            return "heartbeat"

        scheduler_component.register_task(task=heartbeat_task, task_name="heartbeat")

        # Test startup
        await scheduler_component.startup(app=fastapi_app)
        assert scheduler_component.scheduler is not None
        assert scheduler_component.broker is not None

        # Wait a bit to ensure tasks are running
        await asyncio.sleep(0.5)

        # Test shutdown
        await scheduler_component.shutdown()

    async def test_register_task(
        self,
        scheduler_component: SchedulerComponent,
        redis_container: RedisFixture,
        fastapi_app: FastAPI,
    ) -> None:
        """Test registering a task."""
        redis_url: str = redis_container.get_connection_url()
        scheduler_component.configure(redis_connection_string=redis_url, app=fastapi_app)

        async def test_task() -> str:
            """Test task."""
            return "test_result"

        scheduler_component.register_task(task=test_task, task_name="test_task")

        # Verify the task is registered
        task = scheduler_component.get_task("test_task")
        assert task is not None

    async def test_register_duplicate_task_raises_error(
        self,
        scheduler_component: SchedulerComponent,
        redis_container: RedisFixture,
        fastapi_app: FastAPI,
    ) -> None:
        """Test that registering a duplicate task raises an error."""
        redis_url: str = redis_container.get_connection_url()
        scheduler_component.configure(redis_connection_string=redis_url, app=fastapi_app)

        async def test_task() -> str:
            """Test task."""
            return "test_result"

        scheduler_component.register_task(task=test_task, task_name="test_task")

        # Try to register the same task again
        with pytest.raises(ValueError, match="Task test_task already registered"):
            scheduler_component.register_task(task=test_task, task_name="test_task")

    async def test_get_nonexistent_task_raises_error(
        self,
        scheduler_component: SchedulerComponent,
        redis_container: RedisFixture,
        fastapi_app: FastAPI,
    ) -> None:
        """Test that getting a nonexistent task raises an error."""
        redis_url: str = redis_container.get_connection_url()
        scheduler_component.configure(redis_connection_string=redis_url, app=fastapi_app)

        with pytest.raises(ValueError, match="Task nonexistent_task not registered"):
            scheduler_component.get_task("nonexistent_task")

    async def test_register_task_before_configure_raises_error(self, scheduler_component: SchedulerComponent) -> None:
        """Test that registering a task before configuration raises an error."""

        async def test_task() -> str:
            """Test task."""
            return "test_result"

        with pytest.raises(ValueError, match="Stream broker is not initialized"):
            scheduler_component.register_task(task=test_task, task_name="test_task")

    async def test_startup_before_configure_raises_error(
        self, scheduler_component: SchedulerComponent, fastapi_app: FastAPI
    ) -> None:
        """Test that starting before configuration raises an error."""
        with pytest.raises(ValueError, match="Result backend is not initialized"):
            await scheduler_component.startup(app=fastapi_app)

    async def test_properties(
        self,
        scheduler_component: SchedulerComponent,
        redis_container: RedisFixture,
        fastapi_app: FastAPI,
    ) -> None:
        """Test the scheduler component properties."""
        redis_url: str = redis_container.get_connection_url()
        scheduler_component.configure(redis_connection_string=redis_url, app=fastapi_app)

        # Test properties
        assert scheduler_component.scheduler is not None
        assert scheduler_component.broker is not None
        assert scheduler_component.scheduler_source is not None
