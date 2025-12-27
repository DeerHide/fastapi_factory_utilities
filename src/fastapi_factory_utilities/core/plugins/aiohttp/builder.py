"""Builder for the Aiohttp client."""

from typing import Self

from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol

from .configs import HttpServiceDependencyConfig
from .factories import build_http_dependency_config
from .resources import AioHttpClientResource


class AioHttpClientBuilder:
    """Builder for the Aiohttp client."""

    def __init__(
        self,
        keys: list[str],
        application: ApplicationAbstractProtocol,
    ) -> None:
        """Initialize the Aiohttp client builder."""
        self._application: ApplicationAbstractProtocol = application
        self._keys: list[str] = keys
        self._configs: dict[str, HttpServiceDependencyConfig] = {}
        self._resources: dict[str, AioHttpClientResource] = {}

    def build_configs(self) -> Self:
        """Build the HTTP dependency configs."""
        if self._application.PACKAGE_NAME == "":
            raise ValueError("The application package name is not set")

        for key in self._keys:
            self._configs[key] = build_http_dependency_config(
                key=key, application_package=self._application.PACKAGE_NAME
            )
        return self

    def build_resources(self) -> Self:
        """Build the Aiohttp client."""
        for key, config in self._configs.items():
            self._resources[key] = AioHttpClientResource(dependency_config=config)
        return self

    @property
    def resources(self) -> dict[str, AioHttpClientResource]:
        """Get the Aiohttp client resources."""
        return self._resources
