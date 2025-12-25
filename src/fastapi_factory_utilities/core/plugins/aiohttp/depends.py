"""Provides the dependencies for the Aiohttp plugin."""

from fastapi import Request

from .constants import STATE_PREFIX_KEY
from .exceptions import AioHttpClientResourceNotFoundError
from .resources import AioHttpClientResource


class AioHttpResourceDepends:
    """Aiohttp client depends."""

    def __init__(self, key: str) -> None:
        """Initialize the Aiohttp client depends."""
        self._key: str = key

    def __call__(self, request: Request) -> AioHttpClientResource:
        """Get the Aiohttp resource."""
        resource: AioHttpClientResource | None = getattr(request.app.state, f"{STATE_PREFIX_KEY}{self._key}", None)
        if resource is None:
            raise AioHttpClientResourceNotFoundError(
                "Aiohttp resource not found in the application state.", key=self._key
            )
        return resource
