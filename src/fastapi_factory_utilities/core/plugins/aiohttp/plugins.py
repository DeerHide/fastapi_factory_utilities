"""Aiohttp client plugin."""

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract

from .builder import AioHttpClientBuilder
from .constants import STATE_PREFIX_KEY


class AioHttpClientPlugin(PluginAbstract):
    """Aiohttp client plugin."""

    def __init__(self, keys: list[str]) -> None:
        """Initialize the Aiohttp client plugin.

        Args:
            keys (list[str]): The keys of the dependencies configurations.
        """
        super().__init__()
        self._builder: AioHttpClientBuilder = AioHttpClientBuilder(keys=keys)
        self._builder.build_configs()

    def on_load(self) -> None:
        """On load."""

    async def on_startup(self) -> None:
        """On startup."""
        self._builder.build_resources()
        for key, resource in self._builder.resources.items():
            await resource.on_startup()
            self._add_to_state(key=f"{STATE_PREFIX_KEY}{key}", value=resource)

    async def on_shutdown(self) -> None:
        """On shutdown."""
        for _, resource in self._builder.resources.items():
            await resource.on_shutdown()
