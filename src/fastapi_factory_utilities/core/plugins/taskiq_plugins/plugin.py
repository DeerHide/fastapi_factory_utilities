"""Provides the Taskiq plugin."""

from collections.abc import Callable
from typing import TYPE_CHECKING

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.plugins.taskiq_plugins.exceptions import TaskiqPluginConfigError
from fastapi_factory_utilities.core.utils.redis_configs import (
    RedisCredentialsConfig,
    RedisCredentialsConfigError,
    build_redis_credentials_config,
)

from .depends import DEPENDS_SCHEDULER_COMPONENT_KEY
from .schedulers import SchedulerComponent

if TYPE_CHECKING:
    pass


class TaskiqPlugin(PluginAbstract):
    """Taskiq plugin."""

    def __init__(
        self,
        name_suffix: str,
        redis_credentials_config: RedisCredentialsConfig | None = None,
        register_hook: Callable[[SchedulerComponent], None] | None = None,
    ) -> None:
        """Initialize the Taskiq plugin."""
        super().__init__()
        self._redis_credentials_config: RedisCredentialsConfig | None = redis_credentials_config
        self._register_hook: Callable[[SchedulerComponent], None] | None = register_hook
        self._scheduler_component: SchedulerComponent = SchedulerComponent(name_suffix=name_suffix)

    def on_load(self) -> None:
        """On load."""
        assert self._application is not None
        # Build the Redis credentials configuration if not provided
        if self._redis_credentials_config is None:
            try:
                self._redis_credentials_config = build_redis_credentials_config(application=self._application)
            except RedisCredentialsConfigError as exception:
                raise TaskiqPluginConfigError("Unable to build the Redis credentials configuration.") from exception
        # Configure the scheduler component
        self._scheduler_component.configure(
            redis_connection_string=self._redis_credentials_config.url, app=self._application.get_asgi_app()
        )
        self._add_to_state(key=DEPENDS_SCHEDULER_COMPONENT_KEY, value=self._scheduler_component)
        # Register the hook if provided
        if self._register_hook is not None:
            self._register_hook(self._scheduler_component)

    async def on_startup(self) -> None:
        """On startup."""
        assert self._application is not None
        await self._scheduler_component.startup(app=self._application.get_asgi_app())

    async def on_shutdown(self) -> None:
        """On shutdown."""
        assert self._application is not None
        await self._scheduler_component.shutdown()
