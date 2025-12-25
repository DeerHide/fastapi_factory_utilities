"""Mocker Utilities for the Aiohttp plugin."""

from http import HTTPStatus
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import aiohttp

from fastapi_factory_utilities.core.plugins.aiohttp.resources import AioHttpClientResource


def build_mocked_aiohttp_response(
    status: HTTPStatus,
    json: Any = None,
    text: str | None = None,
    headers: dict[str, str] | None = None,
    content: bytes | None = None,
) -> aiohttp.ClientResponse:
    """Build the mocked Aiohttp response."""
    mock_response = AsyncMock(spec=aiohttp.ClientResponse)
    mock_response.status = status
    if status >= HTTPStatus.BAD_REQUEST:
        mock_response.raise_for_status = AsyncMock(
            side_effect=aiohttp.ClientResponseError(
                status=status,
                request_info=MagicMock(spec=aiohttp.RequestInfo),
                history=(),
                message="Error",
            )
        )
    else:
        mock_response.raise_for_status = AsyncMock()
    if json is not None:
        mock_response.json = AsyncMock(return_value=json)
    if text is not None:
        mock_response.text = AsyncMock(return_value=text)
    if headers is not None:
        mock_response.headers = AsyncMock(return_value=headers)
    if content is not None:
        mock_response.content = AsyncMock(return_value=content)
    return mock_response


def build_mocked_aiohttp_resource(
    get: aiohttp.ClientResponse | None = None,
    post: aiohttp.ClientResponse | None = None,
    put: aiohttp.ClientResponse | None = None,
    patch: aiohttp.ClientResponse | None = None,
    delete: aiohttp.ClientResponse | None = None,
) -> AioHttpClientResource:
    """Build the mocked Aiohttp resource."""
    mock_resource = AsyncMock(spec=AioHttpClientResource)
    session = AsyncMock(spec=aiohttp.ClientSession)
    session.get = AsyncMock(return_value=get)
    session.post = AsyncMock(return_value=post)
    session.put = AsyncMock(return_value=put)
    session.patch = AsyncMock(return_value=patch)
    session.delete = AsyncMock(return_value=delete)
    mock_resource.acquire_client_session.__aenter__ = AsyncMock(return_value=session)
    mock_resource.acquire_client_session.__aexit__ = AsyncMock(return_value=None)
    return mock_resource
