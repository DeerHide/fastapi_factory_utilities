"""Provides the dependencies for the Aiohttp plugin."""

from fastapi_factory_utilities.core.plugins.aiohttp_plugin.exceptions import AioHttpClientResourceNotFoundError
from fastapi_factory_utilities.core.plugins.aiohttp_plugin.resources import AioHttpClientResource
from fastapi_factory_utilities.core.plugins.depends import NamedResourceDepends
from fastapi_factory_utilities.core.plugins.state import AIOHTTP_RESOURCE_PREFIX


class AioHttpResourceDepends(NamedResourceDepends[AioHttpClientResource]):
    """Aiohttp client depends."""

    prefix = AIOHTTP_RESOURCE_PREFIX
    not_found_error = AioHttpClientResourceNotFoundError
    not_found_message = "Aiohttp resource not found in the application state."
