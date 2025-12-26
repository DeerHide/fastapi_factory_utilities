"""Mocker Utilities for the Aiohttp plugin."""

import types
from collections.abc import Callable
from http import HTTPStatus
from http.cookies import SimpleCookie
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import aiohttp

from fastapi_factory_utilities.core.plugins.aiohttp.resources import AioHttpClientResource


def build_mocked_aiohttp_response(  # noqa: PLR0913
    status: HTTPStatus,
    json: dict[str, Any] | list[Any] | str | None = None,
    text: str | None = None,
    headers: dict[str, str] | None = None,
    read: bytes | None = None,
    cookies: dict[str, str] | None = None,
    error_message: str | None = None,
    reason: str | None = None,
    url: str | None = None,
    method: str | None = None,
) -> aiohttp.ClientResponse:
    """Build the mocked Aiohttp response.

    Creates a mock aiohttp.ClientResponse object with configurable status code,
    response body (JSON, text, or binary content), headers, and cookies. The mock will
    raise ClientResponseError when raise_for_status() is called if the status
    code indicates an error (>= 400).

    The response supports both usage patterns:
    - Direct await: `response = await session.get(url)`
    - Context manager: `async with session.get(url) as response:`

    Args:
        status: HTTP status code for the response.
        json: JSON data to return from response.json(). Can be a dict, list, or string.
        text: Text data to return from response.text().
        headers: HTTP headers to return from response.headers. Note: In context manager
            pattern, headers is accessed as a property, not a method.
        read: Binary content to return from response.read(). This is the proper aiohttp
            method for reading binary content.
        cookies: Cookies to set in the response. Can be a dict of cookie name-value pairs.
            The cookies will be accessible via response.cookies property.
        error_message: Custom error message for ClientResponseError. If None,
            defaults to a descriptive message based on the status code.
        reason: HTTP reason phrase (e.g., "OK", "Not Found"). If None,
            defaults to the standard phrase for the status code.
        url: The URL of the response (e.g., the final URL after redirects).
        method: The HTTP method used for the request (e.g., "GET", "POST").

    Returns:
        aiohttp.ClientResponse: A mocked ClientResponse object configured with
            the specified parameters. Supports async context manager protocol.

    Example:
        Direct await pattern:
        >>> response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"message": "Success"})
        >>> # response = await session.get(url)
        >>> assert response.status == HTTPStatus.OK
        >>> assert await response.json() == {"message": "Success"}

        Context manager pattern:
        >>> response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"message": "Success"})
        >>> # async with session.get(url) as response:
        >>> assert response.status == HTTPStatus.OK

        Binary content:
        >>> response = build_mocked_aiohttp_response(status=HTTPStatus.OK, read=b"binary data")
        >>> data = await response.read()
        >>> assert data == b"binary data"
    """
    mock_response = MagicMock(spec=aiohttp.ClientResponse)
    mock_response.status = status
    mock_response.reason = reason or status.phrase

    # Configure ok property based on status code (True if status < 400)
    mock_response.ok = status < HTTPStatus.BAD_REQUEST

    # Configure async context manager support for `async with session.get() as response:` pattern
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    # Configure raise_for_status based on status code
    if status >= HTTPStatus.BAD_REQUEST:
        message = error_message or f"HTTP {status.value} {status.phrase}"
        mock_response.raise_for_status = MagicMock(
            side_effect=aiohttp.ClientResponseError(
                status=status,
                request_info=MagicMock(spec=aiohttp.RequestInfo),
                history=(),
                message=message,
            )
        )
    else:
        mock_response.raise_for_status = MagicMock()

    # Configure response body methods
    if json is not None:
        mock_response.json = AsyncMock(return_value=json)
    if text is not None:
        mock_response.text = AsyncMock(return_value=text)

    # Configure binary content reading - response.read() is the proper aiohttp method
    # response.content in aiohttp is a StreamReader property, not a callable
    if read is not None:
        mock_response.read = AsyncMock(return_value=read)
        # Also set up content as a mock StreamReader with a read() method for compatibility
        mock_content = MagicMock()
        mock_content.read = AsyncMock(return_value=read)
        mock_response.content = mock_content

    # Configure headers - as a dict property for context manager pattern
    if headers is not None:
        mock_response.headers = headers

    # Configure cookies
    if cookies is not None:
        cookie_obj = SimpleCookie()
        for name, value in cookies.items():
            cookie_obj[name] = value
        mock_response.cookies = cookie_obj

    # Configure optional response metadata
    if url is not None:
        mock_response.url = url
    if method is not None:
        mock_response.method = method

    return mock_response


# Type alias for parametric response types
ParametricResponse = aiohttp.ClientResponse | None | Callable[..., aiohttp.ClientResponse | None]


def build_mocked_aiohttp_resource(  # noqa: PLR0913
    get: ParametricResponse = None,
    post: ParametricResponse = None,
    put: ParametricResponse = None,
    patch: ParametricResponse = None,
    delete: ParametricResponse = None,
    head: ParametricResponse = None,
    options: ParametricResponse = None,
) -> AioHttpClientResource:
    """Build the mocked Aiohttp resource.

    Creates a mock AioHttpClientResource object with configurable HTTP method responses.
    The mock resource provides an async context manager via `acquire_client_session()` that
    returns a mock ClientSession with the specified method responses configured.

    The resource supports the context manager pattern used by services:
    ```python
    async with resource.acquire_client_session() as session:
        async with session.get(url="...") as response:
            data = await response.json()
    ```

    Supports parametric responses for multiple calls:
    - Single response: Returns the same response for all calls
    - Callable: Calls the function for each request to generate dynamic responses

    Args:
        get: Mock response to return for GET requests. Can be:
            - A single ClientResponse or None
            - A callable that takes request arguments and returns a response
        post: Mock response to return for POST requests. Same format as get.
        put: Mock response to return for PUT requests. Same format as get.
        patch: Mock response to return for PATCH requests. Same format as get.
        delete: Mock response to return for DELETE requests. Same format as get.
        head: Mock response to return for HEAD requests. Same format as get.
        options: Mock response to return for OPTIONS requests. Same format as get.

    Returns:
        AioHttpClientResource: A mocked AioHttpClientResource object configured with
            the specified HTTP method responses.

    Example:
        Context manager pattern (used by services):
        >>> get_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"message": "Success"})
        >>> resource = build_mocked_aiohttp_resource(get=get_response)
        >>> async with resource.acquire_client_session() as session:
        ...     async with session.get(url="https://example.com") as response:
        ...         assert response.status == HTTPStatus.OK
        ...         data = await response.json()

        Dynamic response (callable):
        >>> def get_response(url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        ...     if "page=1" in url:
        ...         return build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"page": 1})
        ...     return build_mocked_aiohttp_response(status=HTTPStatus.NOT_FOUND)
        >>> resource = build_mocked_aiohttp_resource(get=get_response)
        >>> async with resource.acquire_client_session() as session:
        ...     async with session.get(url="https://example.com?page=1") as response:
        ...         assert response.status == HTTPStatus.OK
    """
    mock_resource = MagicMock(spec=AioHttpClientResource)
    session = MagicMock()

    # Configure HTTP methods dynamically to reduce repetition
    # HTTP methods return context managers (the response), not awaitables
    # This supports the pattern: `async with session.get(url) as response:`
    http_methods: dict[str, ParametricResponse] = {
        "get": get,
        "post": post,
        "put": put,
        "patch": patch,
        "delete": delete,
        "head": head,
        "options": options,
    }
    for method_name, response in http_methods.items():
        if isinstance(response, types.FunctionType):
            # Callable response: call the function to generate responses dynamically
            mock_method = MagicMock(side_effect=response)
        else:
            # Static response: return the same response for all calls
            mock_method = MagicMock(return_value=response)
        setattr(session, method_name, mock_method)

    # Configure async context manager for acquire_client_session
    # acquire_client_session() is an @asynccontextmanager, so it returns an async context manager
    # We need to create a context manager object that yields the session
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=session)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    # acquire_client_session is not async itself, it returns an async context manager
    mock_resource.acquire_client_session = MagicMock(return_value=context_manager)

    return mock_resource
