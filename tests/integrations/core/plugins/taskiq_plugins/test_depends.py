"""Integration tests for dependency injection."""

from collections.abc import Callable
from http import HTTPStatus
from unittest.mock import MagicMock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from fastapi_factory_utilities.core.app.config import BaseApplicationConfig, RootConfig
from fastapi_factory_utilities.core.app.enums import EnvironmentEnum
from fastapi_factory_utilities.core.plugins.taskiq_plugins.depends import (
    DEPENDS_SCHEDULER_COMPONENT_KEY,
    depends_scheduler_component,
)
from fastapi_factory_utilities.core.plugins.taskiq_plugins.plugin import TaskiqPlugin
from fastapi_factory_utilities.core.plugins.taskiq_plugins.schedulers import SchedulerComponent
from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol
from fastapi_factory_utilities.core.services.status.services import StatusService


class TestDepends:
    """Integration tests for dependency injection."""

    @pytest.fixture
    def mock_application(self) -> ApplicationAbstractProtocol:
        """Create a mock application."""
        app: ApplicationAbstractProtocol = MagicMock(spec=ApplicationAbstractProtocol)
        app.get_config.return_value = RootConfig(
            application=BaseApplicationConfig(
                environment=EnvironmentEnum.DEVELOPMENT,
                service_name="test",
                service_namespace="test",
                description="test",
                version="0.0.0",
                audience="test",
            )
        )
        fastapi_app: FastAPI = FastAPI()
        app.get_asgi_app.return_value = fastapi_app
        app.get_status_service.return_value = MagicMock(spec=StatusService)
        return app

    async def test_depends_scheduler_component(
        self,
        taskiq_plugin_factory: Callable[[Callable[[SchedulerComponent], None] | None], TaskiqPlugin],
        mock_application: ApplicationAbstractProtocol,
    ) -> None:
        """Test the depends_scheduler_component dependency."""

        # Define heartbeat task
        async def heartbeat_task() -> str:
            """Heartbeat task for testing."""
            return "heartbeat"

        # Create plugin with register hook to register heartbeat task
        def register_hook(scheduler: SchedulerComponent) -> None:
            """Register hook to register heartbeat task."""
            scheduler.register_task(task=heartbeat_task, task_name="heartbeat")

        taskiq_plugin: TaskiqPlugin = taskiq_plugin_factory(register_hook)
        taskiq_plugin.set_application(application=mock_application)
        taskiq_plugin.on_load()

        fastapi_app: FastAPI = mock_application.get_asgi_app()

        # Create a test endpoint that uses the dependency
        @fastapi_app.get("/test-scheduler")
        async def test_endpoint(scheduler: SchedulerComponent = Depends(depends_scheduler_component)) -> dict[str, str]:
            """Test endpoint that uses scheduler component dependency."""
            # Verify scheduler is configured by accessing broker property
            _ = scheduler.broker
            return {"status": "ok", "scheduler_configured": "True"}

        # Start the plugin
        await taskiq_plugin.on_startup()

        # Test the dependency injection
        with TestClient(fastapi_app) as client:
            response = client.get("/test-scheduler")
            assert response.status_code == HTTPStatus.OK
            assert response.json()["status"] == "ok"
            assert response.json()["scheduler_configured"] == "True"

        # Cleanup
        await taskiq_plugin.on_shutdown()

    async def test_depends_scheduler_component_from_state(
        self,
        taskiq_plugin_factory: Callable[[Callable[[SchedulerComponent], None] | None], TaskiqPlugin],
        mock_application: ApplicationAbstractProtocol,
    ) -> None:
        """Test that depends_scheduler_component retrieves from app state."""

        # Define heartbeat task
        async def heartbeat_task() -> str:
            """Heartbeat task for testing."""
            return "heartbeat"

        # Create plugin with register hook to register heartbeat task
        def register_hook(scheduler: SchedulerComponent) -> None:
            """Register hook to register heartbeat task."""
            scheduler.register_task(task=heartbeat_task, task_name="heartbeat")

        taskiq_plugin: TaskiqPlugin = taskiq_plugin_factory(register_hook)
        taskiq_plugin.set_application(application=mock_application)
        taskiq_plugin.on_load()

        fastapi_app: FastAPI = mock_application.get_asgi_app()

        # Verify the scheduler component is in the state
        scheduler_from_state: SchedulerComponent = getattr(fastapi_app.state, DEPENDS_SCHEDULER_COMPONENT_KEY)
        assert scheduler_from_state is not None
        assert isinstance(scheduler_from_state, SchedulerComponent)

        # Test dependency injection using TestClient
        @fastapi_app.get("/test-scheduler-state")
        async def test_endpoint_state(
            scheduler: SchedulerComponent = Depends(depends_scheduler_component),
        ) -> dict[str, str]:
            """Test endpoint that verifies scheduler from state."""
            # Verify scheduler matches the one from state
            is_same = scheduler is scheduler_from_state
            return {"status": "ok", "scheduler_from_state": str(is_same)}

        # Start the plugin
        await taskiq_plugin.on_startup()

        # Test the dependency injection
        with TestClient(fastapi_app) as client:
            response = client.get("/test-scheduler-state")
            assert response.status_code == HTTPStatus.OK
            assert response.json()["status"] == "ok"
            assert response.json()["scheduler_from_state"] == "True"

        # Cleanup
        await taskiq_plugin.on_shutdown()
