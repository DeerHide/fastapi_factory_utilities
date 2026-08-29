"""Unit tests for TaskiqPlugin status registration."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI

from fastapi_factory_utilities.core.plugins.redis_plugin.configs import RedisCredentialsConfig
from fastapi_factory_utilities.core.plugins.taskiq_plugin.plugins import TaskiqPlugin
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
        plugin._application = mock_app

        plugin._scheduler_component.startup = AsyncMock()

        plugin._scheduler_component.shutdown = AsyncMock()

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

    async def test_startup_wires_scheduler_done_callback(self) -> None:
        """Both receiver and cron loops arm not-ready when they die."""
        plugin: TaskiqPlugin = TaskiqPlugin(
            name_suffix="svc",
            redis_credentials_config=RedisCredentialsConfig(url="redis://localhost:6379"),
        )
        self._bind(plugin)

        worker = asyncio.create_task(asyncio.sleep(60))
        scheduler = asyncio.create_task(asyncio.sleep(60))
        captured: list[object] = []

        def _capture(cb: object) -> None:
            captured.append(cb)

        worker.add_done_callback = _capture  # type: ignore[method-assign]
        scheduler.add_done_callback = _capture  # type: ignore[method-assign]

        async def _noop_startup(*, app: FastAPI) -> None:
            del app
            plugin._scheduler_component._worker_task = worker
            plugin._scheduler_component._scheduler_task = scheduler

        plugin._scheduler_component.startup = _noop_startup  # type: ignore[method-assign]
        await plugin.on_startup()

        assert captured == [plugin._on_background_task_done, plugin._on_background_task_done]
        worker.cancel()
        scheduler.cancel()
        with pytest.raises(asyncio.CancelledError):
            await worker
        with pytest.raises(asyncio.CancelledError):
            await scheduler
        await plugin.on_shutdown()

    async def test_background_task_done_arms_unhealthy(self) -> None:
        """A dead cron/receiver loop schedules TASK_QUEUE not-ready (grace=0)."""
        plugin: TaskiqPlugin = TaskiqPlugin(
            name_suffix="svc",
            redis_credentials_config=RedisCredentialsConfig(url="redis://localhost:6379"),
        )
        status_service: StatusService = self._bind(plugin)
        plugin._setup_status(component_type=ComponentTypeEnum.TASK_QUEUE, identifier="Redis")
        plugin._report_healthy()
        plugin._shutting_down = False
        plugin.DISCONNECT_GRACE_S = 0

        done = MagicMock()
        done.cancelled.return_value = False
        plugin._on_background_task_done(done)
        await asyncio.sleep(0.05)

        statuses = list(status_service.get_components_status_by_type()[ComponentTypeEnum.TASK_QUEUE].values())
        assert statuses[0]["health"] == HealthStatusEnum.UNHEALTHY
        assert statuses[0]["readiness"] == ReadinessStatusEnum.NOT_READY

    async def test_startup_failure_marks_task_queue_unhealthy(self) -> None:
        """Redis/broker failure at startup marks TASK_QUEUE unhealthy."""
        plugin: TaskiqPlugin = TaskiqPlugin(
            name_suffix="svc",
            redis_credentials_config=RedisCredentialsConfig(url="redis://localhost:6379"),
        )
        status_service: StatusService = self._bind(plugin)
        plugin._scheduler_component.startup = AsyncMock(side_effect=ConnectionError("down"))

        with pytest.raises(ConnectionError):
            await plugin.on_startup()
        statuses = list(status_service.get_components_status_by_type()[ComponentTypeEnum.TASK_QUEUE].values())
        assert statuses[0]["health"] == HealthStatusEnum.UNHEALTHY
        assert statuses[0]["readiness"] == ReadinessStatusEnum.NOT_READY
