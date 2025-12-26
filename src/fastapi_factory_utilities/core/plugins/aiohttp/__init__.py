"""Aiohttp plugin."""

from importlib.util import find_spec

from .depends import AioHttpResourceDepends
from .exceptions import AioHttpClientError, AioHttpClientResourceNotFoundError, UnableToReadHttpDependencyConfigError
from .plugins import AioHttpClientPlugin
from .resources import AioHttpClientResource

__all__: list[str] = []  # pylint: disable=invalid-name

# Add mockers helpers only if pytest is installed
if find_spec(name="pytest"):
    from .mockers import build_mocked_aiohttp_resource, build_mocked_aiohttp_response

    __all__ += [
        "build_mocked_aiohttp_resource",
        "build_mocked_aiohttp_response",
    ]

__all__ += [
    "AioHttpClientError",
    "AioHttpClientPlugin",
    "AioHttpClientResource",
    "AioHttpClientResourceNotFoundError",
    "AioHttpResourceDepends",
    "UnableToReadHttpDependencyConfigError",
]
