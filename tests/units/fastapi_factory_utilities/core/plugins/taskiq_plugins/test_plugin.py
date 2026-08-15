"""Unit tests for TaskiqPlugin status registration."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI

from fastapi_factory_utilities.core.plugins.redis_plugin.configs import RedisCredentialsConfig
from fastapi_factory_utilities.core.plugins.taskiq_plugins.plugin import TaskiqPlugin
from fastapi_factory_utilities.core.services.status.enums import (
    ComponentTypeEnum,
    HealthStatusEnum,
    ReadinessStatusEnum,
)
from fastapi_factory_utilities.core.services.status.services import StatusService


class TestTaskiqPluginStatus:
    """TaskiqPlugin registers TASK_QUEUE status for its Redis backend."""

    def _bind(self, plugin: TaskiqPlugin) -> StatusService:
        fastapi_app: FastAPI = FastAPI()
        status_service: StatusService = StatusService()
        mock_app: MagicMock = MagicMock()
        mock_app.get_asgi_app.return_value = fastapi_app
        mock_app.get_status_service.return_value = status_service
        plugin._application = mock_app  # pylint: disable=protected-access
        plugin._scheduler_component.startup = AsyncMock()  # pylint: disable=protected-access
        plugin._scheduler_component.shutdown = AsyncMock()  # pylint: disable=protected-access
        return status_service

    async def test_startup_marks_task_queue_ready(self) -> None:
        """Successful scheduler startup marks TASK_QUEUE ready."""
        plugin: TaskiqPlugin = TaskiqPlugin(
            name_suffix="svc",
            redis_credentials_config=RedisCredentialsConfig(url="redis://localhost:6379"),
        )
        status_service: StatusService = self._bind(plugin)
        await plugin.on_startup()
        statuses = list(status_service.get_components_status_by_type()[ComponentTypeEnum.TASK_QUEUE].values())
        assert statuses[0]["health"] == HealthStatusEnum.HEALTHY
        assert statuses[0]["readiness"] == ReadinessStatusEnum.READY
        await plugin.on_shutdown()

    async def test_startup_failure_marks_task_queue_unhealthy(self) -> None:
        """Redis/broker failure at startup marks TASK_QUEUE unhealthy."""
        plugin: TaskiqPlugin = TaskiqPlugin(
            name_suffix="svc",
            redis_credentials_config=RedisCredentialsConfig(url="redis://localhost:6379"),
        )
        status_service: StatusService = self._bind(plugin)
        plugin._scheduler_component.startup = AsyncMock(side_effect=ConnectionError("down"))  # pylint: disable=protected-access
        with pytest.raises(ConnectionError):
            await plugin.on_startup()
        statuses = list(status_service.get_components_status_by_type()[ComponentTypeEnum.TASK_QUEUE].values())
        assert statuses[0]["health"] == HealthStatusEnum.UNHEALTHY
        assert statuses[0]["readiness"] == ReadinessStatusEnum.NOT_READY
