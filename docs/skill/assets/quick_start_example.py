"""Quick start example for fastapi_factory_utilities."""

from fastapi_factory_utilities.core.app import (
    ApplicationAbstract,
    ApplicationGenericBuilder,
)
from fastapi_factory_utilities.core.plugins.odm_plugin import ODMPlugin


class MyApp(ApplicationAbstract):
    """Example application."""

    PACKAGE_NAME = "my_app"
    ODM_DOCUMENT_MODELS = []

    def configure(self) -> None:
        """Configure routes and middleware."""
        pass

    async def on_startup(self) -> None:
        """Custom startup logic."""
        pass

    async def on_shutdown(self) -> None:
        """Custom shutdown logic."""
        pass


class MyAppBuilder(ApplicationGenericBuilder[MyApp]):
    """Builder for MyApp."""

    def get_default_plugins(self) -> list:
        """Return default plugins."""
        return [ODMPlugin()]


if __name__ == "__main__":
    MyAppBuilder().build_and_serve()
