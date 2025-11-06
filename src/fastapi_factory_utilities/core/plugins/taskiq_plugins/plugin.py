"""Provides the Taskiq plugin."""

from collections.abc import Callable

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract

from .configs import RedisCredentialsConfig
from .depends import DEPENDS_SCHEDULER_COMPONENT_KEY
from .schedulers import SchedulerComponent


class TaskiqPlugin(PluginAbstract):
    """Taskiq plugin."""

    def __init__(
        self, redis_credentials_config: RedisCredentialsConfig, register_hook: Callable[[SchedulerComponent], None]
    ) -> None:
        """Initialize the Taskiq plugin."""
        super().__init__()
        self._redis_credentials_config: RedisCredentialsConfig = redis_credentials_config
        self._register_hook: Callable[[SchedulerComponent], None] = register_hook
        self._scheduler_component: SchedulerComponent = SchedulerComponent()

    def on_load(self) -> None:
        """On load."""
        assert self._application is not None
        self._scheduler_component.configure(
            redis_connection_string=self._redis_credentials_config.url, app=self._application.get_asgi_app()
        )
        self._add_to_state(key=DEPENDS_SCHEDULER_COMPONENT_KEY, value=self._scheduler_component)
        self._register_hook(self._scheduler_component)

    async def on_startup(self) -> None:
        """On startup."""
        assert self._application is not None
        await self._scheduler_component.startup(app=self._application.get_asgi_app())

    async def on_shutdown(self) -> None:
        """On shutdown."""
        assert self._application is not None
        await self._scheduler_component.shutdown()
