"""Provides the Taskiq plugin."""

import asyncio
from collections.abc import Callable

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.plugins.state import SCHEDULER_COMPONENT
from fastapi_factory_utilities.core.plugins.status import PluginStatusMixin
from fastapi_factory_utilities.core.plugins.taskiq_plugin.builder import build_taskiq_redis_config
from fastapi_factory_utilities.core.plugins.taskiq_plugin.configs import RedisCredentialsConfig
from fastapi_factory_utilities.core.services.status.enums import ComponentTypeEnum

from .schedulers import SchedulerComponent


class TaskiqPlugin(PluginStatusMixin, PluginAbstract):
    """Taskiq plugin."""

    def __init__(
        self,
        name_suffix: str,
        redis_credentials_config: RedisCredentialsConfig | None = None,
        register_hook: Callable[[SchedulerComponent], None] | None = None,
        stream_maxlen: int = 10_000,
    ) -> None:
        """Initialize the Taskiq plugin."""
        super().__init__()
        self._redis_credentials_config: RedisCredentialsConfig | None = redis_credentials_config
        self._register_hook: Callable[[SchedulerComponent], None] | None = register_hook
        self._stream_maxlen: int = stream_maxlen
        self._scheduler_component: SchedulerComponent = SchedulerComponent(name_suffix=name_suffix)

    def on_load(self) -> None:
        """On load."""
        assert self._application is not None
        # Build the Redis credentials configuration if not provided
        if self._redis_credentials_config is None:
            self._redis_credentials_config = build_taskiq_redis_config(application=self._application)
        # Configure the scheduler component
        self._scheduler_component.configure(
            redis_connection_string=self._redis_credentials_config.url,
            app=self._application.get_asgi_app(),
            stream_maxlen=self._stream_maxlen,
        )
        self._add_to_state(key=SCHEDULER_COMPONENT, value=self._scheduler_component)
        # Register the hook if provided
        if self._register_hook is not None:
            self._register_hook(self._scheduler_component)

    async def on_startup(self) -> None:
        """Start the scheduler and register Redis-backend readiness."""
        assert self._application is not None
        self._setup_status(component_type=ComponentTypeEnum.TASK_QUEUE, identifier="Redis")
        try:
            await self._scheduler_component.startup(app=self._application.get_asgi_app())
        except Exception:
            self._report_unhealthy()
            raise
        worker_task = getattr(self._scheduler_component, "_worker_task", None)
        if isinstance(worker_task, asyncio.Task):
            worker_task.add_done_callback(self._on_worker_done)
        self._report_healthy()

    def _on_worker_done(self, task: asyncio.Task[None]) -> None:
        """Arm not-ready if the worker dies for a reason other than shutdown."""
        if self._shutting_down or task.cancelled():
            return
        self._arm_unhealthy()

    async def on_shutdown(self) -> None:
        """On shutdown."""
        self._shutting_down = True
        self._disarm_unhealthy()
        assert self._application is not None
        await self._scheduler_component.shutdown()
