"""Provides the ApplicationAbstract class."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, ClassVar

from beanie import Document
from fastapi import FastAPI
from fastapi_csrf_protect import CsrfProtect
from structlog.stdlib import BoundLogger, get_logger

from fastapi_factory_utilities.core.api import api
from fastapi_factory_utilities.core.plugins import PluginAbstract
from fastapi_factory_utilities.core.services.status.services import StatusService

from .config import RootConfig
from .csrf import DependsCsrfProtect
from .fastapi_builder import FastAPIBuilder

_logger: BoundLogger = get_logger(__name__)


class ApplicationAbstract(ABC):
    """Application abstract class."""

    PACKAGE_NAME: ClassVar[str]

    CONFIG_CLASS: ClassVar[type[RootConfig]] = RootConfig
    CONFIG_FILENAME: ClassVar[str] = "application.yaml"

    # TODO: Find a way to remove this from here
    ODM_DOCUMENT_MODELS: ClassVar[list[type[Document]]]

    def __init__(
        self,
        root_config: RootConfig,
        plugins: list[PluginAbstract],
        fastapi_builder: FastAPIBuilder,
    ) -> None:
        """Instantiate the application."""
        self.config: RootConfig = root_config
        self.fastapi_builder: FastAPIBuilder = fastapi_builder
        # Add the API router to the FastAPI application
        self.fastapi_builder.add_api_router(router=api, without_resource_path=True)
        self.plugins: list[PluginAbstract] = plugins
        self._add_to_state: dict[str, Any] = {}

    def load_plugins(self) -> None:
        """Load the plugins."""
        for plugin in self.plugins:
            plugin.set_application(application=self)
            plugin.on_load()

    async def startup_plugins(self) -> None:
        """Startup the plugins."""
        for plugin in self.plugins:
            await plugin.on_startup()

    async def shutdown_plugins(self) -> None:
        """Shutdown the plugins."""
        for plugin in self.plugins:
            await plugin.on_shutdown()

    def setup(self) -> None:
        """Initialize the application."""
        # Initialize FastAPI application
        self._asgi_app: FastAPI = self.fastapi_builder.build(lifespan=self.fastapi_lifespan)
        # Status service
        self.status_service: StatusService = StatusService()
        self.add_to_state(key="status_service", value=self.status_service)
        self.add_to_state(key="config", value=self.config)
        self.add_to_state(key="application", value=self)
        self._apply_states_to_fastapi_app()
        # Configure the application
        self.configure()
        self._apply_states_to_fastapi_app()
        # Initialize PluginManager
        self.load_plugins()

    def _apply_states_to_fastapi_app(self) -> None:
        # Add manually added states to the FastAPI app
        for key, value in self._add_to_state.items():
            if hasattr(self._asgi_app.state, key):
                _logger.warn(f"Key {key} already exists in the state. Don't set it outside of the application.")
            setattr(self._asgi_app.state, key, value)
        self._add_to_state.clear()

    def add_to_state(self, key: str, value: Any) -> None:
        """Add a value to the FastAPI app state."""
        if key in self._add_to_state:
            raise ValueError(f"Key {key} already exists in the state.")
        self._add_to_state[key] = value

    def configure_csrf(self) -> None:
        """Configure the CSRF protect.

        This method is an optional method to configure the CSRF protect.
        If you need CSRF protect, you must add it in your implementation of the configure method.

        Example:
        ```python
        def configure(self) -> None:
            self.configure_csrf()
        ```
        """
        config: RootConfig = self.get_config()
        csrf_config = config.csrf
        if csrf_config is None:
            raise ValueError("CSRF config not found in the root config.")
        CsrfProtect.load_config(
            settings=lambda: [
                ("secret_key", csrf_config.secret),
                ("cookie_samesite", csrf_config.cookie_samesite.lower()),
                ("cookie_secure", csrf_config.cookie_secure),
            ]
        )
        csrf_protect: CsrfProtect = CsrfProtect()
        DependsCsrfProtect.import_to_state(state=self.get_asgi_app().state, csrf_protect=csrf_protect)

    @abstractmethod
    def configure(self) -> None:
        """Configure the application.

        This method is the main method to configure the application.
        It is called by the setup method and must be implemented by the subclass.

        Example:
        ```python
        def configure(self) -> None:
            # Configure the CSRF protect through the helper method
            self.configure_csrf()
        ```
        """
        raise NotImplementedError

    @abstractmethod
    async def on_startup(self) -> None:
        """Startup the application."""
        raise NotImplementedError

    @abstractmethod
    async def on_shutdown(self) -> None:
        """Shutdown the application."""
        raise NotImplementedError

    @asynccontextmanager
    async def fastapi_lifespan(self, fastapi: FastAPI) -> AsyncGenerator[None, None]:  # pylint: disable=unused-argument
        """FastAPI lifespan context manager."""
        await self.startup_plugins()
        await self.on_startup()
        try:
            yield
        finally:
            await self.on_shutdown()
            await self.shutdown_plugins()

    def get_config(self) -> RootConfig:
        """Get the configuration."""
        return self.config

    def get_asgi_app(self) -> FastAPI:
        """Get the ASGI application."""
        return self._asgi_app

    def get_status_service(self) -> StatusService:
        """Get the status service."""
        return self.status_service

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        """Forward the call to the FastAPI app."""
        return await self._asgi_app.__call__(scope=scope, receive=receive, send=send)
