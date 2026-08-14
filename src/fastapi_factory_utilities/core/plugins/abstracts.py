"""Abstracts for the plugins."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Self

from fastapi_factory_utilities.core.plugins.state import PluginNotBoundError, StateKey

if TYPE_CHECKING:
    from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol


class PluginAbstract(ABC):
    """Abstract class for the plugins."""

    def __init__(self) -> None:
        """Initialize the plugin."""
        self._application: ApplicationAbstractProtocol | None = None

    def set_application(self, application: "ApplicationAbstractProtocol") -> Self:
        """Set the application."""
        self._application = application
        return self

    def _add_to_state(self, key: str | StateKey, value: Any) -> None:
        """Publish ``value`` on application state under the registry key.

        Args:
            key: Registry entry or its attribute string.
            value: The value to publish.

        Raises:
            PluginNotBoundError: If ``set_application`` has not been called.
        """
        if self._application is None:
            raise PluginNotBoundError("Plugin used before set_application.")
        attr: str = key.attr if isinstance(key, StateKey) else key
        setattr(self._application.get_asgi_app().state, attr, value)

    @abstractmethod
    def on_load(self) -> None:
        """On load."""
        raise NotImplementedError

    @abstractmethod
    async def on_startup(self) -> None:
        """On startup."""
        raise NotImplementedError

    @abstractmethod
    async def on_shutdown(self) -> None:
        """On shutdown."""
        raise NotImplementedError
