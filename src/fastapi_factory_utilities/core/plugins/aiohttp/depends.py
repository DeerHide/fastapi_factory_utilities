"""Provides the dependencies for the Aiohttp plugin."""

from fastapi import Request
from fastapi.datastructures import State

from .constants import STATE_PREFIX_KEY
from .exceptions import AioHttpClientResourceNotFoundError
from .resources import AioHttpClientResource


class AioHttpResourceDepends:
    """Aiohttp client depends."""

    def __init__(self, key: str) -> None:
        """Initialize the Aiohttp client depends."""
        self._key: str = key

    @classmethod
    def export_from_state(cls, state: State, key: str) -> AioHttpClientResource:
        """Export the Aiohttp resource from the state."""
        resource: AioHttpClientResource | None = getattr(state, f"{STATE_PREFIX_KEY}{key}", None)
        if resource is None:
            raise AioHttpClientResourceNotFoundError("Aiohttp resource not found in the application state.", key=key)
        return resource

    def __call__(self, request: Request) -> AioHttpClientResource:
        """Get the Aiohttp resource."""
        resource: AioHttpClientResource = self.export_from_state(state=request.app.state, key=self._key)
        return resource
