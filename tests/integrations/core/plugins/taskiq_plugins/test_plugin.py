"""Integration tests for the Taskiq plugin."""

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI

from fastapi_factory_utilities.core.app.config import BaseApplicationConfig, RootConfig
from fastapi_factory_utilities.core.app.enums import EnvironmentEnum
from fastapi_factory_utilities.core.plugins.taskiq_plugins.depends import DEPENDS_SCHEDULER_COMPONENT_KEY
from fastapi_factory_utilities.core.plugins.taskiq_plugins.plugin import TaskiqPlugin
from fastapi_factory_utilities.core.plugins.taskiq_plugins.schedulers import SchedulerComponent
from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol
from fastapi_factory_utilities.core.services.status.services import StatusService


class TestTaskiqPlugin:
    """Integration tests for the Taskiq plugin."""

    @pytest.fixture
    def mock_application(self) -> MagicMock:
        """Create a mock application."""
        app: MagicMock = MagicMock(spec=ApplicationAbstractProtocol)
        app.get_config.return_value = RootConfig(
            application=BaseApplicationConfig(
                environment=EnvironmentEnum.DEVELOPMENT,
                service_name="test",
                service_namespace="test",
                description="test",
                version="0.0.0",
            )
        )
        fastapi_app: FastAPI = FastAPI()
        app.get_asgi_app.return_value = fastapi_app
        app.get_status_service.return_value = MagicMock(spec=StatusService)
        return app

    async def test_plugin_lifecycle(
        self,
        taskiq_plugin_factory: Callable[[Callable[[SchedulerComponent], None] | None], TaskiqPlugin],
        mock_application: MagicMock,
    ) -> None:
        """Test the plugin lifecycle (load, startup, shutdown)."""

        # Define heartbeat task
        async def heartbeat_task() -> str:
            """Heartbeat task for testing."""
            return "heartbeat"

        # Create plugin with register hook to register heartbeat task
        def register_hook(scheduler: SchedulerComponent) -> None:
            """Register hook to register heartbeat task."""
            scheduler.register_task(task=heartbeat_task, task_name="heartbeat")

        taskiq_plugin: TaskiqPlugin = taskiq_plugin_factory(register_hook)
        # Set the application
        taskiq_plugin.set_application(application=mock_application)

        # Test on_load
        taskiq_plugin.on_load()
        # Verify scheduler component is configured by checking if it's in state
        assert hasattr(mock_application.get_asgi_app().state, DEPENDS_SCHEDULER_COMPONENT_KEY)

        # Test on_startup
        await taskiq_plugin.on_startup()
        # Verify components are initialized by checking properties
        scheduler = getattr(mock_application.get_asgi_app().state, DEPENDS_SCHEDULER_COMPONENT_KEY)
        assert scheduler.scheduler is not None
        assert scheduler.broker is not None
        assert scheduler.scheduler_source is not None

        # Test on_shutdown
        await taskiq_plugin.on_shutdown()

    async def test_plugin_with_register_hook(
        self,
        taskiq_plugin_factory: Callable[[Callable[[SchedulerComponent], None] | None], TaskiqPlugin],
        mock_application: MagicMock,
    ) -> None:
        """Test the plugin with a register hook."""
        hook_called: list[SchedulerComponent] = []

        # Define heartbeat task
        async def heartbeat_task() -> str:
            """Heartbeat task for testing."""
            return "heartbeat"

        def register_hook(scheduler: SchedulerComponent) -> None:
            """Register hook for testing."""
            hook_called.append(scheduler)
            scheduler.register_task(task=heartbeat_task, task_name="heartbeat")

        plugin: TaskiqPlugin = taskiq_plugin_factory(register_hook)
        plugin.set_application(application=mock_application)

        # Test on_load should call the hook
        plugin.on_load()
        assert len(hook_called) == 1
        # Verify the hook was called with the scheduler component from state
        scheduler_from_state = getattr(mock_application.get_asgi_app().state, DEPENDS_SCHEDULER_COMPONENT_KEY)
        assert hook_called[0] is scheduler_from_state

        # Cleanup
        await plugin.on_startup()
        await plugin.on_shutdown()

    async def test_plugin_scheduler_component_in_state(
        self,
        taskiq_plugin_factory: Callable[[Callable[[SchedulerComponent], None] | None], TaskiqPlugin],
        mock_application: MagicMock,
    ) -> None:
        """Test that the scheduler component is added to the application state."""

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

        # Verify the scheduler component is in the state
        scheduler_component: SchedulerComponent = getattr(
            mock_application.get_asgi_app().state, DEPENDS_SCHEDULER_COMPONENT_KEY
        )
        assert scheduler_component is not None
        assert isinstance(scheduler_component, SchedulerComponent)

        # Cleanup
        await taskiq_plugin.on_startup()
        await taskiq_plugin.on_shutdown()
