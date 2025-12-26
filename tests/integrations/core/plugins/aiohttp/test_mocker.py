"""Tests for the Aiohttp mocker."""

from http import HTTPStatus
from typing import Any

import pytest
from aiohttp import ClientResponse, ClientResponseError

from fastapi_factory_utilities.core.plugins.aiohttp.mockers import (
    build_mocked_aiohttp_resource,
    build_mocked_aiohttp_response,
)
from fastapi_factory_utilities.core.plugins.aiohttp.resources import AioHttpClientResource


class TestBuildMockedAiohttpResponse:
    """Various tests for the build_mocked_aiohttp_response function."""

    @pytest.mark.parametrize(
        "status",
        [
            HTTPStatus.OK,
            HTTPStatus.CREATED,
            HTTPStatus.NO_CONTENT,
        ],
    )
    @pytest.mark.asyncio
    async def test_success_status_codes(self, status: HTTPStatus) -> None:
        """Test that success status codes do not raise on raise_for_status."""
        response: ClientResponse = build_mocked_aiohttp_response(status=status)
        assert response.status == status
        await response.raise_for_status()  # type: ignore[func-returns-value] # Should not raise

    @pytest.mark.parametrize(
        "status",
        [
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.UNAUTHORIZED,
            HTTPStatus.FORBIDDEN,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.INTERNAL_SERVER_ERROR,
        ],
    )
    @pytest.mark.asyncio
    async def test_error_status_codes_raise(self, status: HTTPStatus) -> None:
        """Test that error status codes raise ClientResponseError on raise_for_status."""
        response: ClientResponse = build_mocked_aiohttp_response(status=status)
        assert response.status == status
        with pytest.raises(ClientResponseError) as exc_info:
            await response.raise_for_status()  # type: ignore[func-returns-value]
        assert exc_info.value.status == status

    @pytest.mark.asyncio
    async def test_with_json(self) -> None:
        """Test response with JSON data."""
        json_data = {"message": "Hello, world!", "count": 42}
        response: ClientResponse = build_mocked_aiohttp_response(status=HTTPStatus.OK, json=json_data)
        assert response.status == HTTPStatus.OK
        assert await response.json() == json_data

    @pytest.mark.asyncio
    async def test_with_text(self) -> None:
        """Test response with text data."""
        text_data = "Hello, world!"
        response: ClientResponse = build_mocked_aiohttp_response(status=HTTPStatus.OK, text=text_data)
        assert response.status == HTTPStatus.OK
        assert await response.text() == text_data

    @pytest.mark.asyncio
    async def test_with_headers(self) -> None:
        """Test response with headers."""
        headers = {"Content-Type": "application/json", "X-Custom-Header": "custom-value"}
        response: ClientResponse = build_mocked_aiohttp_response(status=HTTPStatus.OK, headers=headers)
        assert response.status == HTTPStatus.OK
        assert await response.headers() == headers  # type: ignore[operator]

    @pytest.mark.asyncio
    async def test_with_content(self) -> None:
        """Test response with binary content."""
        content = b"binary data"
        response: ClientResponse = build_mocked_aiohttp_response(status=HTTPStatus.OK, content=content)
        assert response.status == HTTPStatus.OK
        assert await response.content() == content  # type: ignore[operator]

    @pytest.mark.asyncio
    async def test_with_json_and_text(self) -> None:
        """Test response with both JSON and text (JSON should take precedence)."""
        json_data = {"message": "Hello, world!"}
        text_data = "Hello, world!"
        response: ClientResponse = build_mocked_aiohttp_response(status=HTTPStatus.OK, json=json_data, text=text_data)
        assert response.status == HTTPStatus.OK
        assert await response.json() == json_data
        assert await response.text() == text_data

    @pytest.mark.asyncio
    async def test_with_all_parameters(self) -> None:
        """Test response with all parameters."""
        json_data = {"message": "Hello, world!"}
        text_data = "Hello, world!"
        headers = {"Content-Type": "application/json"}
        content = b"binary data"
        cookies = {"session_id": "abc123"}
        response: ClientResponse = build_mocked_aiohttp_response(
            status=HTTPStatus.OK,
            json=json_data,
            text=text_data,
            headers=headers,
            content=content,
            cookies=cookies,
        )
        assert response.status == HTTPStatus.OK
        assert await response.json() == json_data
        assert await response.text() == text_data
        assert await response.headers() == headers  # type: ignore[operator]
        assert await response.content() == content  # type: ignore[operator]
        assert response.cookies is not None
        assert "session_id" in response.cookies
        assert response.cookies["session_id"].value == "abc123"

    @pytest.mark.asyncio
    async def test_error_status_with_json(self) -> None:
        """Test error response with JSON data."""
        json_data = {"error": "Bad Request"}
        response: ClientResponse = build_mocked_aiohttp_response(status=HTTPStatus.BAD_REQUEST, json=json_data)
        assert response.status == HTTPStatus.BAD_REQUEST
        assert await response.json() == json_data
        with pytest.raises(ClientResponseError):
            await response.raise_for_status()  # type: ignore[func-returns-value]

    @pytest.mark.asyncio
    async def test_with_cookies(self) -> None:
        """Test response with cookies."""
        cookies = {"session_id": "abc123", "csrf_token": "xyz789"}
        response: ClientResponse = build_mocked_aiohttp_response(status=HTTPStatus.OK, cookies=cookies)
        assert response.status == HTTPStatus.OK
        assert response.cookies is not None
        assert "session_id" in response.cookies
        assert response.cookies["session_id"].value == "abc123"
        assert "csrf_token" in response.cookies
        assert response.cookies["csrf_token"].value == "xyz789"

    @pytest.mark.asyncio
    async def test_with_cookies_and_other_parameters(self) -> None:
        """Test response with cookies and other parameters."""
        cookies = {"session_id": "abc123"}
        json_data = {"message": "Success"}
        headers = {"Content-Type": "application/json"}
        response: ClientResponse = build_mocked_aiohttp_response(
            status=HTTPStatus.OK, json=json_data, headers=headers, cookies=cookies
        )
        assert response.status == HTTPStatus.OK
        assert await response.json() == json_data
        assert await response.headers() == headers  # type: ignore[operator]
        assert response.cookies is not None
        assert "session_id" in response.cookies
        assert response.cookies["session_id"].value == "abc123"


class TestBuildMockedAiohttpResource:
    """Various tests for the build_mocked_aiohttp_resource function."""

    @pytest.mark.parametrize(
        "method_name,status,expected_json",
        [
            ("get", HTTPStatus.OK, {"method": "GET"}),
            ("post", HTTPStatus.CREATED, {"method": "POST"}),
            ("put", HTTPStatus.OK, {"method": "PUT"}),
            ("patch", HTTPStatus.OK, {"method": "PATCH"}),
            ("delete", HTTPStatus.NO_CONTENT, {"method": "DELETE"}),
        ],
    )
    @pytest.mark.asyncio
    async def test_http_methods(self, method_name: str, status: HTTPStatus, expected_json: dict[str, str]) -> None:
        """Test HTTP methods return the correct response."""
        method_response = build_mocked_aiohttp_response(status=status, json=expected_json)
        resource: AioHttpClientResource = build_mocked_aiohttp_resource(**{method_name: method_response})
        async with resource.acquire_client_session() as session:
            method = getattr(session, method_name)
            response: ClientResponse = await method(url="https://example.com")
            assert response.status == status
            assert await response.json() == expected_json

    @pytest.mark.asyncio
    async def test_all_methods(self) -> None:
        """Test all HTTP methods at once."""
        get_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"method": "GET"})
        post_response = build_mocked_aiohttp_response(status=HTTPStatus.CREATED, json={"method": "POST"})
        put_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"method": "PUT"})
        patch_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"method": "PATCH"})
        delete_response = build_mocked_aiohttp_response(status=HTTPStatus.NO_CONTENT, json={"method": "DELETE"})
        resource: AioHttpClientResource = build_mocked_aiohttp_resource(
            get=get_response, post=post_response, put=put_response, patch=patch_response, delete=delete_response
        )
        async with resource.acquire_client_session() as session:
            get_resp: ClientResponse = await session.get(url="https://example.com")
            assert await get_resp.json() == {"method": "GET"}
            post_resp: ClientResponse = await session.post(url="https://example.com")
            assert await post_resp.json() == {"method": "POST"}
            put_resp: ClientResponse = await session.put(url="https://example.com")
            assert await put_resp.json() == {"method": "PUT"}
            patch_resp: ClientResponse = await session.patch(url="https://example.com")
            assert await patch_resp.json() == {"method": "PATCH"}
            delete_resp: ClientResponse = await session.delete(url="https://example.com")
            assert await delete_resp.json() == {"method": "DELETE"}

    @pytest.mark.asyncio
    async def test_none_methods(self) -> None:
        """Test that None methods return None."""
        resource: AioHttpClientResource = build_mocked_aiohttp_resource()
        async with resource.acquire_client_session() as session:
            get_resp: ClientResponse | None = await session.get(url="https://example.com")
            assert get_resp is None
            post_resp: ClientResponse | None = await session.post(url="https://example.com")
            assert post_resp is None

    @pytest.mark.asyncio
    async def test_mixed_methods(self) -> None:
        """Test resource with some methods set and others None."""
        get_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"method": "GET"})
        post_response = build_mocked_aiohttp_response(status=HTTPStatus.CREATED, json={"method": "POST"})
        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=get_response, post=post_response)
        async with resource.acquire_client_session() as session:
            get_resp: ClientResponse = await session.get(url="https://example.com")
            assert await get_resp.json() == {"method": "GET"}
            post_resp: ClientResponse = await session.post(url="https://example.com")
            assert await post_resp.json() == {"method": "POST"}
            put_resp: ClientResponse | None = await session.put(url="https://example.com")
            assert put_resp is None

    @pytest.mark.asyncio
    async def test_context_manager_behavior(self) -> None:
        """Test that the context manager works correctly."""
        get_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"test": "data"})
        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=get_response)
        async with resource.acquire_client_session() as session:
            assert session is not None
            response: ClientResponse = await session.get(url="https://example.com")
            assert response.status == HTTPStatus.OK

    @pytest.mark.asyncio
    async def test_multiple_context_managers(self) -> None:
        """Test multiple context manager usages."""
        get_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"test": "data"})
        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=get_response)
        async with resource.acquire_client_session() as session1:
            response1: ClientResponse = await session1.get(url="https://example.com")
            assert response1.status == HTTPStatus.OK
        async with resource.acquire_client_session() as session2:
            response2: ClientResponse = await session2.get(url="https://example.com")
            assert response2.status == HTTPStatus.OK

    @pytest.mark.asyncio
    async def test_error_response_in_resource(self) -> None:
        """Test resource with error response."""
        error_response = build_mocked_aiohttp_response(
            status=HTTPStatus.INTERNAL_SERVER_ERROR, json={"error": "Internal Server Error"}
        )
        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=error_response)
        async with resource.acquire_client_session() as session:
            response: ClientResponse = await session.get(url="https://example.com")
            assert response.status == HTTPStatus.INTERNAL_SERVER_ERROR
            assert await response.json() == {"error": "Internal Server Error"}
            with pytest.raises(ClientResponseError):
                await response.raise_for_status()  # type: ignore[func-returns-value]

    @pytest.mark.asyncio
    async def test_parametric_responses_callable(self) -> None:
        """Test parametric responses with a callable function."""
        call_count = 0

        def get_response(*args: Any, url: str = "", **kwargs: Any) -> ClientResponse | None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"call": 1})
            if call_count == 2:
                return build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"call": 2})
            return build_mocked_aiohttp_response(status=HTTPStatus.NOT_FOUND)

        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=get_response)
        async with resource.acquire_client_session() as session:
            resp1: ClientResponse = await session.get(url="https://example.com")
            resp2: ClientResponse = await session.get(url="https://example.com")
            resp3: ClientResponse = await session.get(url="https://example.com")
            assert await resp1.json() == {"call": 1}
            assert await resp2.json() == {"call": 2}
            assert resp3.status == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_parametric_responses_callable_with_url(self) -> None:
        """Test parametric responses with a callable that uses URL."""

        def get_response(*args: Any, url: str = "", **kwargs: Any) -> ClientResponse | None:
            if "page=1" in url:
                return build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"page": 1})
            if "page=2" in url:
                return build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"page": 2})
            return build_mocked_aiohttp_response(status=HTTPStatus.NOT_FOUND)

        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=get_response)
        async with resource.acquire_client_session() as session:
            resp1: ClientResponse = await session.get(url="https://example.com?page=1")
            resp2: ClientResponse = await session.get(url="https://example.com?page=2")
            resp3: ClientResponse = await session.get(url="https://example.com?page=3")
            assert await resp1.json() == {"page": 1}
            assert await resp2.json() == {"page": 2}
            assert resp3.status == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_parametric_responses_backward_compatibility(self) -> None:
        """Test that single response still works (backward compatibility)."""
        get_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"message": "Success"})
        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=get_response)
        async with resource.acquire_client_session() as session:
            # Multiple calls should return the same response
            resp1: ClientResponse = await session.get(url="https://example.com")
            resp2: ClientResponse = await session.get(url="https://example.com")
            assert await resp1.json() == {"message": "Success"}
            assert await resp2.json() == {"message": "Success"}
            assert resp1.status == HTTPStatus.OK
            assert resp2.status == HTTPStatus.OK

    @pytest.mark.asyncio
    async def test_parametric_responses_multiple_methods(self) -> None:
        """Test parametric responses with multiple HTTP methods using callables."""
        get_call_count = 0
        post_call_count = 0

        def get_response(*args: Any, url: str = "", **kwargs: Any) -> ClientResponse:
            nonlocal get_call_count
            get_call_count += 1
            return build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"method": "GET", "call": get_call_count})

        def post_response(*args: Any, url: str = "", **kwargs: Any) -> ClientResponse:
            nonlocal post_call_count
            post_call_count += 1
            return build_mocked_aiohttp_response(
                status=HTTPStatus.CREATED, json={"method": "POST", "call": post_call_count}
            )

        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=get_response, post=post_response)
        async with resource.acquire_client_session() as session:
            get_resp1: ClientResponse = await session.get(url="https://example.com")
            get_resp2: ClientResponse = await session.get(url="https://example.com")
            post_resp1: ClientResponse = await session.post(url="https://example.com")
            post_resp2: ClientResponse = await session.post(url="https://example.com")
            assert await get_resp1.json() == {"method": "GET", "call": 1}
            assert await get_resp2.json() == {"method": "GET", "call": 2}
            assert await post_resp1.json() == {"method": "POST", "call": 1}
            assert await post_resp2.json() == {"method": "POST", "call": 2}
