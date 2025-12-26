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
    def test_success_status_codes(self, status: HTTPStatus) -> None:
        """Test that success status codes do not raise on raise_for_status."""
        response: ClientResponse = build_mocked_aiohttp_response(status=status)
        assert response.status == status
        response.raise_for_status()  # Should not raise

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
    def test_error_status_codes_raise(self, status: HTTPStatus) -> None:
        """Test that error status codes raise ClientResponseError on raise_for_status."""
        response: ClientResponse = build_mocked_aiohttp_response(status=status)
        assert response.status == status
        with pytest.raises(ClientResponseError) as exc_info:
            response.raise_for_status()
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

    def test_with_headers(self) -> None:
        """Test response with headers as a dict property."""
        headers = {"Content-Type": "application/json", "X-Custom-Header": "custom-value"}
        response: ClientResponse = build_mocked_aiohttp_response(status=HTTPStatus.OK, headers=headers)
        assert response.status == HTTPStatus.OK
        assert response.headers == headers

    @pytest.mark.asyncio
    async def test_with_read(self) -> None:
        """Test response with binary content using response.read()."""
        binary_data = b"binary data"
        response: ClientResponse = build_mocked_aiohttp_response(status=HTTPStatus.OK, read=binary_data)
        assert response.status == HTTPStatus.OK
        assert await response.read() == binary_data

    @pytest.mark.asyncio
    async def test_with_content_stream_reader(self) -> None:
        """Test response.content as StreamReader-like object with read() method."""
        binary_data = b"binary data"
        response: ClientResponse = build_mocked_aiohttp_response(status=HTTPStatus.OK, read=binary_data)
        assert response.status == HTTPStatus.OK
        # response.content should be a mock StreamReader with a read() method
        assert await response.content.read() == binary_data

    @pytest.mark.asyncio
    async def test_with_json_and_text(self) -> None:
        """Test response with both JSON and text."""
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
        binary_data = b"binary data"
        cookies = {"session_id": "abc123"}
        response: ClientResponse = build_mocked_aiohttp_response(
            status=HTTPStatus.OK,
            json=json_data,
            text=text_data,
            headers=headers,
            read=binary_data,
            cookies=cookies,
            url="https://example.com/resource",
            method="GET",
        )
        assert response.status == HTTPStatus.OK
        assert await response.json() == json_data
        assert await response.text() == text_data
        assert response.headers == headers
        assert await response.read() == binary_data
        assert await response.content.read() == binary_data
        assert response.cookies is not None
        assert "session_id" in response.cookies
        assert response.cookies["session_id"].value == "abc123"
        assert response.url == "https://example.com/resource"
        assert response.method == "GET"

    @pytest.mark.asyncio
    async def test_error_status_with_json(self) -> None:
        """Test error response with JSON data."""
        json_data = {"error": "Bad Request"}
        response: ClientResponse = build_mocked_aiohttp_response(status=HTTPStatus.BAD_REQUEST, json=json_data)
        assert response.status == HTTPStatus.BAD_REQUEST
        assert await response.json() == json_data
        with pytest.raises(ClientResponseError):
            response.raise_for_status()

    def test_with_cookies(self) -> None:
        """Test response with cookies."""
        cookies = {"session_id": "abc123", "csrf_token": "xyz789"}
        response: ClientResponse = build_mocked_aiohttp_response(status=HTTPStatus.OK, cookies=cookies)
        assert response.status == HTTPStatus.OK
        assert response.cookies is not None
        assert "session_id" in response.cookies
        assert response.cookies["session_id"].value == "abc123"
        assert "csrf_token" in response.cookies
        assert response.cookies["csrf_token"].value == "xyz789"

    def test_with_cookies_and_other_parameters(self) -> None:
        """Test response with cookies and other parameters."""
        cookies = {"session_id": "abc123"}
        json_data = {"message": "Success"}
        headers = {"Content-Type": "application/json"}
        response: ClientResponse = build_mocked_aiohttp_response(
            status=HTTPStatus.OK, json=json_data, headers=headers, cookies=cookies
        )
        assert response.status == HTTPStatus.OK
        assert response.headers == headers
        assert response.cookies is not None
        assert "session_id" in response.cookies
        assert response.cookies["session_id"].value == "abc123"

    @pytest.mark.asyncio
    async def test_context_manager_support(self) -> None:
        """Test that response supports async context manager protocol."""
        response: ClientResponse = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"message": "Success"})
        # Test async context manager
        async with response as ctx_response:
            assert ctx_response is response
            assert ctx_response.status == HTTPStatus.OK
            assert await ctx_response.json() == {"message": "Success"}

    def test_reason_default(self) -> None:
        """Test that reason defaults to status phrase."""
        response: ClientResponse = build_mocked_aiohttp_response(status=HTTPStatus.OK)
        assert response.reason == "OK"

        response_error: ClientResponse = build_mocked_aiohttp_response(status=HTTPStatus.NOT_FOUND)
        assert response_error.reason == "Not Found"

    def test_reason_custom(self) -> None:
        """Test that custom reason can be set."""
        response: ClientResponse = build_mocked_aiohttp_response(status=HTTPStatus.OK, reason="Custom Reason")
        assert response.reason == "Custom Reason"

    @pytest.mark.parametrize(
        "status,expected_ok",
        [
            (HTTPStatus.OK, True),
            (HTTPStatus.CREATED, True),
            (HTTPStatus.NO_CONTENT, True),
            (HTTPStatus.MOVED_PERMANENTLY, True),
            (HTTPStatus.BAD_REQUEST, False),
            (HTTPStatus.UNAUTHORIZED, False),
            (HTTPStatus.NOT_FOUND, False),
            (HTTPStatus.INTERNAL_SERVER_ERROR, False),
        ],
    )
    def test_ok_property(self, status: HTTPStatus, expected_ok: bool) -> None:
        """Test that ok property is True for status < 400 and False otherwise."""
        response: ClientResponse = build_mocked_aiohttp_response(status=status)
        assert response.ok == expected_ok

    def test_url_property(self) -> None:
        """Test that url property can be set."""
        response: ClientResponse = build_mocked_aiohttp_response(
            status=HTTPStatus.OK, url="https://example.com/final-url"
        )
        assert response.url == "https://example.com/final-url"

    def test_method_property(self) -> None:
        """Test that method property can be set."""
        response: ClientResponse = build_mocked_aiohttp_response(status=HTTPStatus.OK, method="POST")
        assert response.method == "POST"


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
            ("head", HTTPStatus.OK, {"method": "HEAD"}),
            ("options", HTTPStatus.OK, {"method": "OPTIONS"}),
        ],
    )
    @pytest.mark.asyncio
    async def test_http_methods_context_manager(
        self, method_name: str, status: HTTPStatus, expected_json: dict[str, str]
    ) -> None:
        """Test HTTP methods with context manager pattern (used by services)."""
        method_response = build_mocked_aiohttp_response(status=status, json=expected_json)
        resource: AioHttpClientResource = build_mocked_aiohttp_resource(**{method_name: method_response})
        async with resource.acquire_client_session() as session:
            method = getattr(session, method_name)
            async with method(url="https://example.com") as response:
                assert response.status == status
                assert await response.json() == expected_json

    @pytest.mark.asyncio
    async def test_all_methods_context_manager(self) -> None:
        """Test all HTTP methods at once with context manager pattern."""
        get_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"method": "GET"})
        post_response = build_mocked_aiohttp_response(status=HTTPStatus.CREATED, json={"method": "POST"})
        put_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"method": "PUT"})
        patch_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"method": "PATCH"})
        delete_response = build_mocked_aiohttp_response(status=HTTPStatus.NO_CONTENT, json={"method": "DELETE"})
        head_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"method": "HEAD"})
        options_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"method": "OPTIONS"})
        resource: AioHttpClientResource = build_mocked_aiohttp_resource(
            get=get_response,
            post=post_response,
            put=put_response,
            patch=patch_response,
            delete=delete_response,
            head=head_response,
            options=options_response,
        )
        async with resource.acquire_client_session() as session:
            async with session.get(url="https://example.com") as get_resp:
                assert await get_resp.json() == {"method": "GET"}
            async with session.post(url="https://example.com") as post_resp:
                assert await post_resp.json() == {"method": "POST"}
            async with session.put(url="https://example.com") as put_resp:
                assert await put_resp.json() == {"method": "PUT"}
            async with session.patch(url="https://example.com") as patch_resp:
                assert await patch_resp.json() == {"method": "PATCH"}
            async with session.delete(url="https://example.com") as delete_resp:
                assert await delete_resp.json() == {"method": "DELETE"}
            async with session.head(url="https://example.com") as head_resp:
                assert await head_resp.json() == {"method": "HEAD"}
            async with session.options(url="https://example.com") as options_resp:
                assert await options_resp.json() == {"method": "OPTIONS"}

    @pytest.mark.asyncio
    async def test_none_methods(self) -> None:
        """Test that None methods return None."""
        resource: AioHttpClientResource = build_mocked_aiohttp_resource()
        async with resource.acquire_client_session() as session:
            get_resp = session.get(url="https://example.com")
            assert get_resp is None
            post_resp = session.post(url="https://example.com")
            assert post_resp is None

    @pytest.mark.asyncio
    async def test_mixed_methods_context_manager(self) -> None:
        """Test resource with some methods set and others None using context manager."""
        get_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"method": "GET"})
        post_response = build_mocked_aiohttp_response(status=HTTPStatus.CREATED, json={"method": "POST"})
        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=get_response, post=post_response)
        async with resource.acquire_client_session() as session:
            async with session.get(url="https://example.com") as get_resp:
                assert await get_resp.json() == {"method": "GET"}
            async with session.post(url="https://example.com") as post_resp:
                assert await post_resp.json() == {"method": "POST"}
            put_resp = session.put(url="https://example.com")
            assert put_resp is None

    @pytest.mark.asyncio
    async def test_context_manager_behavior(self) -> None:
        """Test that the context manager works correctly with nested context managers."""
        get_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"test": "data"})
        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=get_response)
        async with resource.acquire_client_session() as session:
            assert session is not None
            async with session.get(url="https://example.com") as response:
                assert response.status == HTTPStatus.OK
                assert await response.json() == {"test": "data"}

    @pytest.mark.asyncio
    async def test_multiple_context_managers(self) -> None:
        """Test multiple context manager usages."""
        get_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"test": "data"})
        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=get_response)
        async with resource.acquire_client_session() as session1:
            async with session1.get(url="https://example.com") as response1:
                assert response1.status == HTTPStatus.OK
        async with resource.acquire_client_session() as session2:
            async with session2.get(url="https://example.com") as response2:
                assert response2.status == HTTPStatus.OK

    @pytest.mark.asyncio
    async def test_error_response_in_resource(self) -> None:
        """Test resource with error response."""
        error_response = build_mocked_aiohttp_response(
            status=HTTPStatus.INTERNAL_SERVER_ERROR, json={"error": "Internal Server Error"}
        )
        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=error_response)
        async with resource.acquire_client_session() as session:
            async with session.get(url="https://example.com") as response:
                assert response.status == HTTPStatus.INTERNAL_SERVER_ERROR
                assert await response.json() == {"error": "Internal Server Error"}
                with pytest.raises(ClientResponseError):
                    response.raise_for_status()

    @pytest.mark.asyncio
    async def test_parametric_responses_callable(self) -> None:
        """Test parametric responses with a callable function."""
        call_count = 0
        first_call = 1
        second_call = 2

        def get_response(
            *_args: Any,
            _url: str = "",
            **_kwargs: Any,
        ) -> ClientResponse | None:
            nonlocal call_count
            call_count += 1
            if call_count == first_call:
                return build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"call": 1})
            if call_count == second_call:
                return build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"call": 2})
            return build_mocked_aiohttp_response(status=HTTPStatus.NOT_FOUND)

        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=get_response)
        async with resource.acquire_client_session() as session:
            async with session.get(url="https://example.com") as resp1:
                assert await resp1.json() == {"call": 1}
            async with session.get(url="https://example.com") as resp2:
                assert await resp2.json() == {"call": 2}
            async with session.get(url="https://example.com") as resp3:
                assert resp3.status == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_parametric_responses_callable_with_url(self) -> None:
        """Test parametric responses with a callable that uses URL."""

        def get_response(*_args: Any, url: str = "", **_kwargs: Any) -> ClientResponse | None:
            if "page=1" in url:
                return build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"page": 1})
            if "page=2" in url:
                return build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"page": 2})
            return build_mocked_aiohttp_response(status=HTTPStatus.NOT_FOUND)

        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=get_response)
        async with resource.acquire_client_session() as session:
            async with session.get(url="https://example.com?page=1") as resp1:
                assert await resp1.json() == {"page": 1}
            async with session.get(url="https://example.com?page=2") as resp2:
                assert await resp2.json() == {"page": 2}
            async with session.get(url="https://example.com?page=3") as resp3:
                assert resp3.status == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_parametric_responses_backward_compatibility(self) -> None:
        """Test that single response still works with context manager pattern."""
        get_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"message": "Success"})
        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=get_response)
        async with resource.acquire_client_session() as session:
            # Multiple calls should return the same response
            async with session.get(url="https://example.com") as resp1:
                assert await resp1.json() == {"message": "Success"}
                assert resp1.status == HTTPStatus.OK
            async with session.get(url="https://example.com") as resp2:
                assert await resp2.json() == {"message": "Success"}
                assert resp2.status == HTTPStatus.OK

    @pytest.mark.asyncio
    async def test_parametric_responses_multiple_methods(self) -> None:
        """Test parametric responses with multiple HTTP methods using callables."""
        get_call_count = 0
        post_call_count = 0

        def get_response(*_args: Any, _url: str = "", **_kwargs: Any) -> ClientResponse:
            nonlocal get_call_count
            get_call_count += 1
            return build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"method": "GET", "call": get_call_count})

        def post_response(*_args: Any, _url: str = "", **_kwargs: Any) -> ClientResponse:
            nonlocal post_call_count
            post_call_count += 1
            return build_mocked_aiohttp_response(
                status=HTTPStatus.CREATED, json={"method": "POST", "call": post_call_count}
            )

        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=get_response, post=post_response)
        async with resource.acquire_client_session() as session:
            async with session.get(url="https://example.com") as get_resp1:
                assert await get_resp1.json() == {"method": "GET", "call": 1}
            async with session.get(url="https://example.com") as get_resp2:
                assert await get_resp2.json() == {"method": "GET", "call": 2}
            async with session.post(url="https://example.com") as post_resp1:
                assert await post_resp1.json() == {"method": "POST", "call": 1}
            async with session.post(url="https://example.com") as post_resp2:
                assert await post_resp2.json() == {"method": "POST", "call": 2}

    @pytest.mark.asyncio
    async def test_service_like_pattern(self) -> None:
        """Test the exact pattern used by Kratos/Hydra services."""
        mock_data = {"id": "123", "name": "test"}
        get_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json=mock_data)
        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=get_response)

        # This mimics the actual service pattern
        async with resource.acquire_client_session() as session:
            async with session.get(url="/api/resource/123") as response:
                response.raise_for_status()
                data = await response.json()
                assert data == mock_data

    @pytest.mark.asyncio
    async def test_service_like_pattern_with_error(self) -> None:
        """Test error handling pattern used by services."""
        error_response = build_mocked_aiohttp_response(
            status=HTTPStatus.NOT_FOUND,
            json={"error": "Not Found"},
            error_message="Resource not found",
        )
        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=error_response)

        async with resource.acquire_client_session() as session:
            async with session.get(url="/api/resource/999") as response:
                with pytest.raises(ClientResponseError) as exc_info:
                    response.raise_for_status()
                assert exc_info.value.status == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_post_with_data(self) -> None:
        """Test POST request with data parameter."""
        post_response = build_mocked_aiohttp_response(status=HTTPStatus.CREATED, json={"created": True})
        resource: AioHttpClientResource = build_mocked_aiohttp_resource(post=post_response)

        async with resource.acquire_client_session() as session:
            async with session.post(url="/api/resource", data={"key": "value"}) as response:
                response.raise_for_status()
                assert response.status == HTTPStatus.CREATED
                assert await response.json() == {"created": True}

    @pytest.mark.asyncio
    async def test_headers_in_response(self) -> None:
        """Test that headers are accessible in response."""
        get_response = build_mocked_aiohttp_response(
            status=HTTPStatus.OK,
            json={"data": "test"},
            headers={"Link": '<https://example.com/next>; rel="next"'},
        )
        resource: AioHttpClientResource = build_mocked_aiohttp_resource(get=get_response)

        async with resource.acquire_client_session() as session:
            async with session.get(url="/api/resources") as response:
                response.raise_for_status()
                # Headers are accessed as a dict property
                assert "Link" in response.headers
                assert response.headers["Link"] == '<https://example.com/next>; rel="next"'
