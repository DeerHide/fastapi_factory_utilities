"""Provides the concrete application class."""

from typing import ClassVar

from beanie import Document

from fastapi_factory_utilities.core.app.application import ApplicationAbstract
from fastapi_factory_utilities.core.app.builder import ApplicationGenericBuilder
from fastapi_factory_utilities.core.app.config import RootConfig
from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.plugins.odm_plugin import ODMPlugin
from fastapi_factory_utilities.core.plugins.opentelemetry_plugin import OpenTelemetryPlugin
from fastapi_factory_utilities.example.models.books.document import BookDocument


class AppRootConfig(RootConfig):
    """Application configuration class."""

    pass


class App(ApplicationAbstract):
    """Concrete application class."""

    CONFIG_CLASS: ClassVar[type[RootConfig]] = AppRootConfig

    PACKAGE_NAME: ClassVar[str] = "fastapi_factory_utilities.example"

    ODM_DOCUMENT_MODELS: ClassVar[list[type[Document]]] = [BookDocument]

    def configure(self) -> None:
        """Configure the application."""
        # Prevent circular import
        from .api import api_router  # noqa: PLC0415

        self.get_asgi_app().include_router(router=api_router)

    async def on_startup(self) -> None:
        """Actions to perform on application startup."""
        pass

    async def on_shutdown(self) -> None:
        """Actions to perform on application shutdown."""
        pass


class AppBuilder(ApplicationGenericBuilder[App]):
    """Application builder for the App application."""

    def get_default_plugins(self) -> list[PluginAbstract]:
        """Get the default plugins."""
        return [ODMPlugin(), OpenTelemetryPlugin()]

    def __init__(self, plugins: list[PluginAbstract] | None = None) -> None:
        """Initialize the AppBuilder."""
        # If no plugins are provided, use the default plugins
        if plugins is None:
            plugins = self.get_default_plugins()
        super().__init__(plugins=plugins)
