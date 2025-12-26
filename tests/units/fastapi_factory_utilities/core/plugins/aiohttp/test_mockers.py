"""Tests for aiohttp plugin mockers."""

from http import HTTPStatus
from typing import Any
from unittest.mock import MagicMock

import aiohttp
import pytest

from fastapi_factory_utilities.core.plugins.aiohttp.mockers import (
    build_mocked_aiohttp_resource,
    build_mocked_aiohttp_response,
)

# Test constants
SECOND_CALL: int = 2
SECOND_PAGE: int = 2


class TestBuildMockedAiohttpResponse:
    """Test cases for build_mocked_aiohttp_response function."""

    def test_basic_response_with_status(self) -> None:
        """Test creating a basic response with status code."""
        response = build_mocked_aiohttp_response(status=HTTPStatus.OK)

        assert response.status == HTTPStatus.OK
        assert response.reason == "OK"
        assert response.ok is True

    def test_response_with_error_status(self) -> None:
        """Test creating a response with error status code."""
        response = build_mocked_aiohttp_response(status=HTTPStatus.NOT_FOUND)

        assert response.status == HTTPStatus.NOT_FOUND
        assert response.reason == "Not Found"
        assert response.ok is False

    def test_response_with_custom_reason(self) -> None:
        """Test creating a response with custom reason."""
        response = build_mocked_aiohttp_response(status=HTTPStatus.OK, reason="Custom Reason")

        assert response.reason == "Custom Reason"

    async def test_response_with_json_dict(self) -> None:
        """Test response with JSON dict data."""
        json_data = {"message": "Success", "data": {"id": 123}}
        response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json=json_data)

        result = await response.json()

        assert result == json_data

    async def test_response_with_json_list(self) -> None:
        """Test response with JSON list data."""
        json_data = [{"id": 1}, {"id": 2}]
        response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json=json_data)

        result = await response.json()

        assert result == json_data

    async def test_response_with_json_string(self) -> None:
        """Test response with JSON string data."""
        json_data = "simple string"
        response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json=json_data)

        result = await response.json()

        assert result == json_data

    async def test_response_with_text(self) -> None:
        """Test response with text data."""
        text_data = "Plain text response"
        response = build_mocked_aiohttp_response(status=HTTPStatus.OK, text=text_data)

        result = await response.text()

        assert result == text_data

    async def test_response_with_binary_read(self) -> None:
        """Test response with binary data via read()."""
        binary_data = b"binary content"
        response = build_mocked_aiohttp_response(status=HTTPStatus.OK, read=binary_data)

        result = await response.read()

        assert result == binary_data

    async def test_response_with_binary_content_read(self) -> None:
        """Test response with binary data via content.read()."""
        binary_data = b"binary content"
        response = build_mocked_aiohttp_response(status=HTTPStatus.OK, read=binary_data)

        result = await response.content.read()

        assert result == binary_data

    def test_response_with_headers(self) -> None:
        """Test response with custom headers."""
        headers = {"Content-Type": "application/json", "X-Custom-Header": "value"}
        response = build_mocked_aiohttp_response(status=HTTPStatus.OK, headers=headers)

        assert response.headers == headers

    def test_response_with_cookies(self) -> None:
        """Test response with cookies."""
        cookies = {"session_id": "abc123", "user_token": "xyz789"}
        response = build_mocked_aiohttp_response(status=HTTPStatus.OK, cookies=cookies)

        assert response.cookies is not None
        assert response.cookies["session_id"].value == "abc123"
        assert response.cookies["user_token"].value == "xyz789"

    def test_response_with_url(self) -> None:
        """Test response with URL."""
        url = "https://api.example.com/resource"
        response = build_mocked_aiohttp_response(status=HTTPStatus.OK, url=url)

        assert response.url == url

    def test_response_with_method(self) -> None:
        """Test response with HTTP method."""
        method = "POST"
        response = build_mocked_aiohttp_response(status=HTTPStatus.OK, method=method)

        assert response.method == method

    def test_raise_for_status_success(self) -> None:
        """Test raise_for_status does not raise for success status."""
        response = build_mocked_aiohttp_response(status=HTTPStatus.OK)

        # Should not raise
        response.raise_for_status()

    def test_raise_for_status_error(self) -> None:
        """Test raise_for_status raises for error status."""
        response = build_mocked_aiohttp_response(status=HTTPStatus.NOT_FOUND)

        with pytest.raises(aiohttp.ClientResponseError) as exc_info:
            response.raise_for_status()

        assert exc_info.value.status == HTTPStatus.NOT_FOUND

    def test_raise_for_status_custom_error_message(self) -> None:
        """Test raise_for_status with custom error message."""
        custom_message = "Custom error occurred"
        response = build_mocked_aiohttp_response(status=HTTPStatus.BAD_REQUEST, error_message=custom_message)

        with pytest.raises(aiohttp.ClientResponseError) as exc_info:
            response.raise_for_status()

        assert custom_message in str(exc_info.value.message)

    async def test_async_context_manager_support(self) -> None:
        """Test response supports async context manager."""
        response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"success": True})

        async with response as r:
            assert r.status == HTTPStatus.OK
            data = await r.json()
            assert data == {"success": True}

    @pytest.mark.parametrize(
        "status,expected_ok",
        [
            (HTTPStatus.OK, True),
            (HTTPStatus.CREATED, True),
            (HTTPStatus.NO_CONTENT, True),
            (HTTPStatus.MOVED_PERMANENTLY, True),
            (HTTPStatus.BAD_REQUEST, False),
            (HTTPStatus.UNAUTHORIZED, False),
            (HTTPStatus.FORBIDDEN, False),
            (HTTPStatus.NOT_FOUND, False),
            (HTTPStatus.INTERNAL_SERVER_ERROR, False),
        ],
    )
    def test_ok_property_various_statuses(self, status: HTTPStatus, expected_ok: bool) -> None:
        """Test ok property for various status codes."""
        response = build_mocked_aiohttp_response(status=status)

        assert response.ok == expected_ok

    def test_full_response_configuration(self) -> None:
        """Test response with all options configured."""
        response = build_mocked_aiohttp_response(
            status=HTTPStatus.OK,
            json={"data": "value"},
            text="text content",
            headers={"X-Custom": "header"},
            read=b"binary",
            cookies={"session": "token"},
            reason="Custom OK",
            url="https://example.com",
            method="GET",
        )

        assert response.status == HTTPStatus.OK
        assert response.reason == "Custom OK"
        assert response.headers == {"X-Custom": "header"}
        assert response.url == "https://example.com"
        assert response.method == "GET"


class TestBuildMockedAiohttpResource:
    """Test cases for build_mocked_aiohttp_resource function."""

    def test_resource_is_aiohttp_client_resource_spec(self) -> None:
        """Test resource has AioHttpClientResource spec."""
        resource = build_mocked_aiohttp_resource()

        assert isinstance(resource, MagicMock)

    async def test_acquire_client_session_context_manager(self) -> None:
        """Test acquire_client_session returns async context manager."""
        get_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"result": "success"})
        resource = build_mocked_aiohttp_resource(get=get_response)

        async with resource.acquire_client_session() as session:
            response = session.get(url="https://example.com")
            assert response == get_response

    async def test_get_method_response(self) -> None:
        """Test GET method returns configured response."""
        get_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"method": "GET"})
        resource = build_mocked_aiohttp_resource(get=get_response)

        async with resource.acquire_client_session() as session:
            response = session.get(url="https://example.com")
            assert response.status == HTTPStatus.OK
            data = await response.json()
            assert data == {"method": "GET"}

    async def test_post_method_response(self) -> None:
        """Test POST method returns configured response."""
        post_response = build_mocked_aiohttp_response(status=HTTPStatus.CREATED, json={"id": 123})
        resource = build_mocked_aiohttp_resource(post=post_response)

        async with resource.acquire_client_session() as session:
            response = session.post(url="https://example.com", json={"data": "test"})
            assert response.status == HTTPStatus.CREATED
            data = await response.json()
            assert data == {"id": 123}

    async def test_put_method_response(self) -> None:
        """Test PUT method returns configured response."""
        put_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"updated": True})
        resource = build_mocked_aiohttp_resource(put=put_response)

        async with resource.acquire_client_session() as session:
            response = session.put(url="https://example.com/1", json={"data": "test"})
            assert response.status == HTTPStatus.OK

    async def test_patch_method_response(self) -> None:
        """Test PATCH method returns configured response."""
        patch_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"patched": True})
        resource = build_mocked_aiohttp_resource(patch=patch_response)

        async with resource.acquire_client_session() as session:
            response = session.patch(url="https://example.com/1", json={"field": "value"})
            assert response.status == HTTPStatus.OK

    async def test_delete_method_response(self) -> None:
        """Test DELETE method returns configured response."""
        delete_response = build_mocked_aiohttp_response(status=HTTPStatus.NO_CONTENT)
        resource = build_mocked_aiohttp_resource(delete=delete_response)

        async with resource.acquire_client_session() as session:
            response = session.delete(url="https://example.com/1")
            assert response.status == HTTPStatus.NO_CONTENT

    async def test_head_method_response(self) -> None:
        """Test HEAD method returns configured response."""
        head_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, headers={"Content-Length": "1024"})
        resource = build_mocked_aiohttp_resource(head=head_response)

        async with resource.acquire_client_session() as session:
            response = session.head(url="https://example.com")
            assert response.status == HTTPStatus.OK

    async def test_options_method_response(self) -> None:
        """Test OPTIONS method returns configured response."""
        options_response = build_mocked_aiohttp_response(
            status=HTTPStatus.OK, headers={"Allow": "GET, POST, PUT, DELETE"}
        )
        resource = build_mocked_aiohttp_resource(options=options_response)

        async with resource.acquire_client_session() as session:
            response = session.options(url="https://example.com")
            assert response.status == HTTPStatus.OK

    async def test_callable_response(self) -> None:
        """Test callable response for dynamic responses."""
        call_count = 0

        def dynamic_get_response(**kwargs: Any) -> aiohttp.ClientResponse:  # pylint: disable=unused-argument
            nonlocal call_count
            call_count += 1
            return build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"call": call_count})

        resource = build_mocked_aiohttp_resource(get=dynamic_get_response)

        async with resource.acquire_client_session() as session:
            response1 = session.get(url="https://example.com")
            assert (await response1.json())["call"] == 1

            response2 = session.get(url="https://example.com")
            assert (await response2.json())["call"] == SECOND_CALL

    async def test_callable_response_with_url_based_logic(self) -> None:
        """Test callable response with URL-based logic."""

        def url_based_response(url: str = "", **kwargs: Any) -> aiohttp.ClientResponse:  # pylint: disable=unused-argument
            if "page=1" in url:
                return build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"page": 1, "items": [1, 2, 3]})
            elif "page=2" in url:
                return build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"page": 2, "items": [4, 5, 6]})
            return build_mocked_aiohttp_response(status=HTTPStatus.NOT_FOUND)

        resource = build_mocked_aiohttp_resource(get=url_based_response)

        async with resource.acquire_client_session() as session:
            response1 = session.get(url="https://api.com?page=1")
            data1 = await response1.json()
            assert data1["page"] == 1

            response2 = session.get(url="https://api.com?page=2")
            data2 = await response2.json()
            assert data2["page"] == SECOND_PAGE

            response3 = session.get(url="https://api.com?page=99")
            assert response3.status == HTTPStatus.NOT_FOUND

    async def test_multiple_methods_configured(self) -> None:
        """Test resource with multiple HTTP methods configured."""
        resource = build_mocked_aiohttp_resource(
            get=build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"method": "GET"}),
            post=build_mocked_aiohttp_response(status=HTTPStatus.CREATED, json={"method": "POST"}),
            delete=build_mocked_aiohttp_response(status=HTTPStatus.NO_CONTENT),
        )

        async with resource.acquire_client_session() as session:
            get_response = session.get(url="https://example.com")
            assert get_response.status == HTTPStatus.OK

            post_response = session.post(url="https://example.com")
            assert post_response.status == HTTPStatus.CREATED

            delete_response = session.delete(url="https://example.com")
            assert delete_response.status == HTTPStatus.NO_CONTENT

    def test_none_response(self) -> None:
        """Test method with None response."""
        resource = build_mocked_aiohttp_resource(get=None)

        # acquire_client_session is synchronous, returns context manager
        context_manager = resource.acquire_client_session()
        assert context_manager is not None

    async def test_context_manager_pattern(self) -> None:
        """Test the full context manager pattern used by services."""
        get_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"data": "value"})
        resource = build_mocked_aiohttp_resource(get=get_response)

        async with resource.acquire_client_session() as session:
            response = session.get(url="https://api.example.com")
            async with response as r:
                assert r.status == HTTPStatus.OK
                data = await r.json()
                assert data == {"data": "value"}


class TestMockerIntegration:
    """Integration tests for mocker utilities."""

    async def test_service_pattern_simulation(self) -> None:
        """Test simulation of typical service usage pattern."""
        # Arrange
        expected_data = {"users": [{"id": 1, "name": "Alice"}]}
        get_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json=expected_data)
        resource = build_mocked_aiohttp_resource(get=get_response)

        # Act - simulating a service method
        async with resource.acquire_client_session() as session:
            async with session.get(url="https://api.example.com/users") as response:
                response.raise_for_status()
                data = await response.json()

        # Assert
        assert data == expected_data

    async def test_error_handling_simulation(self) -> None:
        """Test simulation of error handling pattern."""
        # Arrange
        error_response = build_mocked_aiohttp_response(
            status=HTTPStatus.NOT_FOUND,
            json={"error": "Resource not found"},
            error_message="The requested resource was not found",
        )
        resource = build_mocked_aiohttp_resource(get=error_response)

        # Act & Assert
        async with resource.acquire_client_session() as session:
            async with session.get(url="https://api.example.com/nonexistent") as response:
                assert response.ok is False

                with pytest.raises(aiohttp.ClientResponseError):
                    response.raise_for_status()

    async def test_post_with_body_simulation(self) -> None:
        """Test simulation of POST request with body."""
        # Arrange
        created_resource = {"id": 123, "name": "New Item", "status": "created"}
        post_response = build_mocked_aiohttp_response(
            status=HTTPStatus.CREATED,
            json=created_resource,
            headers={"Location": "https://api.example.com/items/123"},
        )
        resource = build_mocked_aiohttp_resource(post=post_response)

        # Act
        async with resource.acquire_client_session() as session:
            async with session.post(url="https://api.example.com/items", json={"name": "New Item"}) as response:
                response.raise_for_status()
                data = await response.json()

        # Assert
        assert data == created_resource
        assert response.status == HTTPStatus.CREATED
