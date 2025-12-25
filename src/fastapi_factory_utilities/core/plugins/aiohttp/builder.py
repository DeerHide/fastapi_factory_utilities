"""Builder for the Aiohttp client."""

from typing import Self

from .configs import HttpServiceDependencyConfig
from .factories import build_http_dependency_config
from .resources import AioHttpClientResource


class AioHttpClientBuilder:
    """Builder for the Aiohttp client."""

    def __init__(self, keys: list[str]) -> None:
        """Initialize the Aiohttp client builder."""
        self._keys: list[str] = keys
        self._configs: dict[str, HttpServiceDependencyConfig] = {}
        self._resources: dict[str, AioHttpClientResource] = {}

    def build_configs(self) -> Self:
        """Build the HTTP dependency configs."""
        return [build_http_dependency_config(key=key) for key in self._keys]

    def build_resources(self) -> Self:
        """Build the Aiohttp client."""
        for key, config in self._configs.items():
            self._resources[key] = AioHttpClientResource(dependency_config=config)
        return list(self._resources.values())

    @property
    def resources(self) -> dict[str, AioHttpClientResource]:
        """Get the Aiohttp client resources."""
        return self._resources
