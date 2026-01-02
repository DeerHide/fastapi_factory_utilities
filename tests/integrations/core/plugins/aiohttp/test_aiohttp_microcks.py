"""Integration tests for aiohttp plugin using Microcks.

This module contains integration tests for the AioHttpClientResource class
using Microcks as an API mocking service.
"""
# pylint: disable=redefined-outer-name,protected-access

import asyncio
from collections.abc import AsyncGenerator
from http import HTTPStatus
from pathlib import Path
from typing import Any

import aiohttp
import pytest
from pydantic import HttpUrl

from fastapi_factory_utilities.core.plugins.aiohttp import (
    AioHttpClientError,
    AioHttpClientResource,
    HttpServiceDependencyConfig,
)
from tests.fixtures.microcks import MicrocksFixture

# Constants for the sample API
SAMPLE_API_NAME: str = "Sample API"
SAMPLE_API_VERSION: str = "1.0"
OPENAPI_SPEC_PATH: Path = Path(__file__).parent.parent.parent.parent.parent / "fixtures" / "openapi" / "sample_api.yaml"

# Connection pool constants
DEFAULT_CONNECTOR_LIMIT: int = 50
DEFAULT_CONNECTOR_LIMIT_PER_HOST: int = 20


@pytest.fixture(scope="module")
def microcks_with_sample_api(microcks_container: MicrocksFixture) -> MicrocksFixture:
    """Upload the sample API to Microcks.

    Args:
        microcks_container: The Microcks fixture.

    Returns:
        MicrocksFixture: The Microcks fixture with the sample API uploaded.
    """
    microcks_container.upload_artifact(OPENAPI_SPEC_PATH)
    return microcks_container


@pytest.fixture(scope="function")
def aiohttp_config() -> HttpServiceDependencyConfig:
    """Create an aiohttp configuration for testing.

    Returns:
        HttpServiceDependencyConfig: The aiohttp configuration.
    """
    return HttpServiceDependencyConfig(
        limit=10,
        limit_per_host=5,
        use_dns_cache=True,
        ttl_dns_cache=300,
        verify_ssl=False,  # Microcks doesn't use HTTPS by default
        graceful_shutdown_timeout=5,
    )


@pytest.fixture(scope="function")
async def aiohttp_resource(
    aiohttp_config: HttpServiceDependencyConfig,
) -> AsyncGenerator[AioHttpClientResource, None]:
    """Create an aiohttp resource for testing.

    Args:
        aiohttp_config: The aiohttp configuration.

    Yields:
        AioHttpClientResource: The aiohttp resource.
    """
    resource = AioHttpClientResource(dependency_config=aiohttp_config)
    await resource.on_startup()
    yield resource
    await resource.on_shutdown()


class TestAioHttpBasicHttpMethods:
    """Tests for basic HTTP methods using Microcks."""

    async def test_get_user_by_id(
        self,
        microcks_with_sample_api: MicrocksFixture,
        aiohttp_resource: AioHttpClientResource,
    ) -> None:
        """Test GET request to retrieve a user by ID."""
        url = microcks_with_sample_api.get_mock_url(SAMPLE_API_NAME, SAMPLE_API_VERSION, "/api/users/1")

        async with aiohttp_resource.acquire_client_session() as session:
            async with session.get(url) as response:
                assert response.status == HTTPStatus.OK
                data: dict[str, Any] = await response.json()
                assert "id" in data
                assert "name" in data
                assert "email" in data
                assert data["id"] == "1"

    async def test_get_all_users(
        self,
        microcks_with_sample_api: MicrocksFixture,
        aiohttp_resource: AioHttpClientResource,
    ) -> None:
        """Test GET request to retrieve all users."""
        url = microcks_with_sample_api.get_mock_url(SAMPLE_API_NAME, SAMPLE_API_VERSION, "/api/users")

        async with aiohttp_resource.acquire_client_session() as session:
            async with session.get(url) as response:
                assert response.status == HTTPStatus.OK
                data: list[dict[str, Any]] = await response.json()
                assert isinstance(data, list)
                assert len(data) >= 1

    async def test_post_create_user(
        self,
        microcks_with_sample_api: MicrocksFixture,
        aiohttp_resource: AioHttpClientResource,
    ) -> None:
        """Test POST request to create a new user."""
        url = microcks_with_sample_api.get_mock_url(SAMPLE_API_NAME, SAMPLE_API_VERSION, "/api/users")
        payload = {"name": "New User", "email": "new.user@example.com"}

        async with aiohttp_resource.acquire_client_session() as session:
            async with session.post(url, json=payload) as response:
                assert response.status == HTTPStatus.CREATED
                data: dict[str, Any] = await response.json()
                assert "id" in data
                assert data["name"] == "New User"

    async def test_put_update_user(
        self,
        microcks_with_sample_api: MicrocksFixture,
        aiohttp_resource: AioHttpClientResource,
    ) -> None:
        """Test PUT request to update a user."""
        url = microcks_with_sample_api.get_mock_url(SAMPLE_API_NAME, SAMPLE_API_VERSION, "/api/users/1")
        payload = {"name": "John Updated", "email": "john.updated@example.com"}

        async with aiohttp_resource.acquire_client_session() as session:
            async with session.put(url, json=payload) as response:
                assert response.status == HTTPStatus.OK
                data: dict[str, Any] = await response.json()
                assert data["name"] == "John Updated"

    async def test_delete_user(
        self,
        microcks_with_sample_api: MicrocksFixture,
        aiohttp_resource: AioHttpClientResource,
    ) -> None:
        """Test DELETE request to delete a user."""
        url = microcks_with_sample_api.get_mock_url(SAMPLE_API_NAME, SAMPLE_API_VERSION, "/api/users/1")

        async with aiohttp_resource.acquire_client_session() as session:
            async with session.delete(url) as response:
                assert response.status == HTTPStatus.OK
                data: dict[str, Any] = await response.json()
                assert data["deleted"] is True
                assert data["id"] == "1"

    async def test_health_check(
        self,
        microcks_with_sample_api: MicrocksFixture,
        aiohttp_resource: AioHttpClientResource,
    ) -> None:
        """Test health check endpoint."""
        url = microcks_with_sample_api.get_mock_url(SAMPLE_API_NAME, SAMPLE_API_VERSION, "/api/health")

        async with aiohttp_resource.acquire_client_session() as session:
            async with session.get(url) as response:
                assert response.status == HTTPStatus.OK
                data: dict[str, Any] = await response.json()
                assert data["status"] == "healthy"


class TestAioHttpErrorHandling:
    """Tests for error handling using Microcks."""

    async def test_not_found_error(
        self,
        microcks_with_sample_api: MicrocksFixture,
        aiohttp_resource: AioHttpClientResource,
    ) -> None:
        """Test 404 Not Found response."""
        url = microcks_with_sample_api.get_mock_url(SAMPLE_API_NAME, SAMPLE_API_VERSION, "/api/errors/not-found")

        async with aiohttp_resource.acquire_client_session() as session:
            async with session.get(url) as response:
                assert response.status == HTTPStatus.NOT_FOUND
                data: dict[str, Any] = await response.json()
                assert data["error"] == "Not Found"
                assert data["status"] == HTTPStatus.NOT_FOUND.value

    async def test_server_error(
        self,
        microcks_with_sample_api: MicrocksFixture,
        aiohttp_resource: AioHttpClientResource,
    ) -> None:
        """Test 500 Internal Server Error response."""
        url = microcks_with_sample_api.get_mock_url(SAMPLE_API_NAME, SAMPLE_API_VERSION, "/api/errors/server-error")

        async with aiohttp_resource.acquire_client_session() as session:
            async with session.get(url) as response:
                assert response.status == HTTPStatus.INTERNAL_SERVER_ERROR
                data: dict[str, Any] = await response.json()
                assert data["error"] == "Internal Server Error"
                assert data["status"] == HTTPStatus.INTERNAL_SERVER_ERROR.value

    async def test_bad_request_error(
        self,
        microcks_with_sample_api: MicrocksFixture,
        aiohttp_resource: AioHttpClientResource,
    ) -> None:
        """Test 400 Bad Request response."""
        url = microcks_with_sample_api.get_mock_url(SAMPLE_API_NAME, SAMPLE_API_VERSION, "/api/errors/bad-request")
        payload = {"invalid_field": "test"}

        async with aiohttp_resource.acquire_client_session() as session:
            async with session.post(url, json=payload) as response:
                assert response.status == HTTPStatus.BAD_REQUEST
                data: dict[str, Any] = await response.json()
                assert data["error"] == "Bad Request"
                assert data["status"] == HTTPStatus.BAD_REQUEST.value

    async def test_raise_for_status_on_error(
        self,
        microcks_with_sample_api: MicrocksFixture,
        aiohttp_resource: AioHttpClientResource,
    ) -> None:
        """Test raise_for_status() raises ClientResponseError on error status."""
        url = microcks_with_sample_api.get_mock_url(SAMPLE_API_NAME, SAMPLE_API_VERSION, "/api/errors/not-found")

        async with aiohttp_resource.acquire_client_session() as session:
            async with session.get(url) as response:
                with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                    response.raise_for_status()
                assert exc_info.value.status == HTTPStatus.NOT_FOUND


class TestAioHttpConnectionPooling:
    """Tests for connection pooling behavior."""

    async def test_multiple_concurrent_requests(
        self,
        microcks_with_sample_api: MicrocksFixture,
        aiohttp_resource: AioHttpClientResource,
    ) -> None:
        """Test multiple concurrent requests using the connection pool."""
        url = microcks_with_sample_api.get_mock_url(SAMPLE_API_NAME, SAMPLE_API_VERSION, "/api/users")
        num_requests = 5

        async def make_request(session: aiohttp.ClientSession) -> int:
            async with session.get(url) as response:
                return response.status

        async with aiohttp_resource.acquire_client_session() as session:
            tasks = [make_request(session) for _ in range(num_requests)]
            results = await asyncio.gather(*tasks)
            assert all(status == HTTPStatus.OK for status in results)
            assert len(results) == num_requests

    async def test_multiple_sessions_from_same_resource(
        self,
        microcks_with_sample_api: MicrocksFixture,
        aiohttp_resource: AioHttpClientResource,
    ) -> None:
        """Test acquiring multiple sessions from the same resource."""
        url = microcks_with_sample_api.get_mock_url(SAMPLE_API_NAME, SAMPLE_API_VERSION, "/api/health")

        async with aiohttp_resource.acquire_client_session() as session1:
            async with aiohttp_resource.acquire_client_session() as session2:
                async with session1.get(url) as response1:
                    assert response1.status == HTTPStatus.OK
                async with session2.get(url) as response2:
                    assert response2.status == HTTPStatus.OK

    async def test_connection_limit_per_host(
        self,
        microcks_with_sample_api: MicrocksFixture,
    ) -> None:
        """Test that connection limit per host is respected."""
        config = HttpServiceDependencyConfig(
            limit=20,
            limit_per_host=2,  # Low limit to test
            verify_ssl=False,
            graceful_shutdown_timeout=5,
        )
        resource = AioHttpClientResource(dependency_config=config)
        await resource.on_startup()

        url = microcks_with_sample_api.get_mock_url(SAMPLE_API_NAME, SAMPLE_API_VERSION, "/api/users")

        try:
            async with resource.acquire_client_session() as session:
                # Make more requests than the per-host limit
                # The connector should queue requests beyond the limit
                tasks = [session.get(url) for _ in range(5)]
                responses = await asyncio.gather(*tasks)
                for response in responses:
                    assert response.status == HTTPStatus.OK
                    await response.release()
        finally:
            await resource.on_shutdown()


class TestAioHttpSslTls:
    """Tests for SSL/TLS connections."""

    async def test_ssl_verification_disabled(
        self,
        microcks_with_sample_api: MicrocksFixture,
    ) -> None:
        """Test with SSL verification disabled."""
        config = HttpServiceDependencyConfig(
            verify_ssl=False,
            graceful_shutdown_timeout=5,
        )
        resource = AioHttpClientResource(dependency_config=config)
        await resource.on_startup()

        url = microcks_with_sample_api.get_mock_url(SAMPLE_API_NAME, SAMPLE_API_VERSION, "/api/health")

        try:
            async with resource.acquire_client_session() as session:
                async with session.get(url) as response:
                    assert response.status == HTTPStatus.OK
        finally:
            await resource.on_shutdown()

    def test_build_ssl_context_with_verification(self) -> None:
        """Test SSL context building with verification enabled."""
        config = HttpServiceDependencyConfig(
            verify_ssl=True,
            graceful_shutdown_timeout=5,
        )
        ssl_context = AioHttpClientResource.build_ssl_context(config)
        # When verify_ssl is True and no custom CA path, it uses certifi
        assert ssl_context is not False

    def test_build_ssl_context_without_verification(self) -> None:
        """Test SSL context building with verification disabled."""
        config = HttpServiceDependencyConfig(
            verify_ssl=False,
            graceful_shutdown_timeout=5,
        )
        ssl_context = AioHttpClientResource.build_ssl_context(config)
        assert ssl_context is False


class TestAioHttpResourceLifecycle:
    """Tests for AioHttpClientResource lifecycle."""

    async def test_resource_startup_and_shutdown(self) -> None:
        """Test resource startup and shutdown."""
        config = HttpServiceDependencyConfig(
            verify_ssl=False,
            graceful_shutdown_timeout=5,
        )
        resource = AioHttpClientResource(dependency_config=config)

        # Before startup, TCP connector should be None
        assert resource._tcp_connector is None  # pyright: ignore[reportPrivateUsage]

        await resource.on_startup()

        # After startup, TCP connector should be initialized
        assert resource._tcp_connector is not None  # pyright: ignore[reportPrivateUsage]

        await resource.on_shutdown()

    async def test_acquire_session_without_startup_raises_error(self) -> None:
        """Test that acquiring a session without startup raises RuntimeError."""
        config = HttpServiceDependencyConfig(
            verify_ssl=False,
            graceful_shutdown_timeout=5,
        )
        resource = AioHttpClientResource(dependency_config=config)

        with pytest.raises(AioHttpClientError, match="TCP connector is not initialized"):
            async with resource.acquire_client_session():
                pass

    async def test_acquire_session_with_connector_kwarg_raises_error(
        self,
        aiohttp_resource: AioHttpClientResource,
    ) -> None:
        """Test that providing connector kwarg raises ValueError."""
        with pytest.raises(ValueError, match="connector is already provided"):
            async with aiohttp_resource.acquire_client_session(connector=aiohttp.TCPConnector()):
                pass

    async def test_graceful_shutdown_with_active_sessions(
        self,
        microcks_with_sample_api: MicrocksFixture,
    ) -> None:
        """Test graceful shutdown waits for active sessions."""
        config = HttpServiceDependencyConfig(
            verify_ssl=False,
            graceful_shutdown_timeout=2,  # Short timeout for test
        )
        resource = AioHttpClientResource(dependency_config=config)
        await resource.on_startup()

        url = microcks_with_sample_api.get_mock_url(SAMPLE_API_NAME, SAMPLE_API_VERSION, "/api/health")

        # Start a session but don't close it immediately
        session_context = resource.acquire_client_session()
        session = await session_context.__aenter__()

        # Make a request
        async with session.get(url) as response:
            assert response.status == HTTPStatus.OK

        # Start shutdown in background (should wait for session)
        shutdown_task = asyncio.create_task(resource.on_shutdown())

        # Release the session
        await session_context.__aexit__(None, None, None)

        # Wait for shutdown to complete
        await shutdown_task


class TestAioHttpTcpConnector:
    """Tests for TCP connector configuration."""

    async def test_build_tcp_connector_with_defaults(self) -> None:
        """Test TCP connector building with default configuration."""
        config = HttpServiceDependencyConfig()
        connector = AioHttpClientResource.build_tcp_connector(config)

        assert connector.limit == config.limit
        assert connector.limit_per_host == config.limit_per_host
        await connector.close()

    async def test_build_tcp_connector_with_custom_limits(self) -> None:
        """Test TCP connector building with custom connection limits."""
        config = HttpServiceDependencyConfig(
            limit=DEFAULT_CONNECTOR_LIMIT,
            limit_per_host=DEFAULT_CONNECTOR_LIMIT_PER_HOST,
        )
        connector = AioHttpClientResource.build_tcp_connector(config)

        assert connector.limit == DEFAULT_CONNECTOR_LIMIT
        assert connector.limit_per_host == DEFAULT_CONNECTOR_LIMIT_PER_HOST
        await connector.close()

    async def test_build_tcp_connector_with_dns_cache(self) -> None:
        """Test TCP connector building with DNS cache settings."""
        config = HttpServiceDependencyConfig(
            use_dns_cache=True,
            ttl_dns_cache=600,
        )
        connector = AioHttpClientResource.build_tcp_connector(config)

        assert connector._use_dns_cache is True  # pyright: ignore[reportPrivateUsage]
        await connector.close()


class TestAioHttpIntegrationScenarios:
    """Integration test scenarios simulating real-world usage."""

    async def test_typical_crud_workflow(
        self,
        microcks_with_sample_api: MicrocksFixture,
        aiohttp_resource: AioHttpClientResource,
    ) -> None:
        """Test a typical CRUD workflow."""
        base_url = microcks_with_sample_api.container.get_mock_endpoint(SAMPLE_API_NAME, SAMPLE_API_VERSION)

        async with aiohttp_resource.acquire_client_session() as session:
            # Create a user
            async with session.post(
                f"{base_url}/api/users", json={"name": "New User", "email": "new@example.com"}
            ) as create_response:
                assert create_response.status == HTTPStatus.CREATED
                created_user: dict[str, Any] = await create_response.json()
                assert "id" in created_user

            # Get all users
            async with session.get(f"{base_url}/api/users") as list_response:
                assert list_response.status == HTTPStatus.OK
                users: list[dict[str, Any]] = await list_response.json()
                assert isinstance(users, list)

            # Update a user
            async with session.put(
                f"{base_url}/api/users/1", json={"name": "Updated", "email": "updated@example.com"}
            ) as update_response:
                assert update_response.status == HTTPStatus.OK

            # Delete a user
            async with session.delete(f"{base_url}/api/users/1") as delete_response:
                assert delete_response.status == HTTPStatus.OK

    async def test_base_url_with_relative_paths(
        self,
        microcks_with_sample_api: MicrocksFixture,
    ) -> None:
        """Test using base_url configuration with relative paths.

        This test verifies that when a base_url is configured in the
        HttpServiceDependencyConfig, the client session can use relative
        paths for requests instead of absolute URLs.
        """
        # Get the base URL from Microcks and ensure it has a trailing slash
        base_url_str = microcks_with_sample_api.container.get_mock_endpoint(SAMPLE_API_NAME, SAMPLE_API_VERSION)
        if not base_url_str.endswith("/"):
            base_url_str += "/"

        # Create config with base_url set
        config = HttpServiceDependencyConfig(
            url=HttpUrl(base_url_str),
            limit=10,
            limit_per_host=5,
            use_dns_cache=True,
            ttl_dns_cache=300,
            verify_ssl=False,
            graceful_shutdown_timeout=5,
        )

        # Create resource with base_url configured
        resource = AioHttpClientResource(dependency_config=config)
        await resource.on_startup()

        try:
            async with resource.acquire_client_session() as session:
                # Test GET with relative path
                async with session.get("api/users/1") as response:
                    assert response.status == HTTPStatus.OK
                    data: dict[str, Any] = await response.json()
                    assert "id" in data
                    assert data["id"] == "1"

                # Test GET all users with relative path
                async with session.get("api/users") as response:
                    assert response.status == HTTPStatus.OK
                    users: list[dict[str, Any]] = await response.json()
                    assert isinstance(users, list)
                    assert len(users) > 0

                # Test POST with relative path
                async with session.post(
                    "api/users", json={"name": "Test User", "email": "test@example.com"}
                ) as response:
                    assert response.status == HTTPStatus.CREATED
                    created_user: dict[str, Any] = await response.json()
                    assert "id" in created_user

                # Test PUT with relative path
                async with session.put(
                    "api/users/1", json={"name": "Updated User", "email": "updated@example.com"}
                ) as response:
                    assert response.status == HTTPStatus.OK

                # Test DELETE with relative path
                async with session.delete("api/users/1") as response:
                    assert response.status == HTTPStatus.OK

                # Test health check with relative path
                async with session.get("api/health") as response:
                    assert response.status == HTTPStatus.OK
                    health: dict[str, Any] = await response.json()
                    assert health.get("status") == "healthy"

        finally:
            await resource.on_shutdown()

    async def test_error_handling_workflow(
        self,
        microcks_with_sample_api: MicrocksFixture,
        aiohttp_resource: AioHttpClientResource,
    ) -> None:
        """Test error handling in a typical workflow."""
        base_url = microcks_with_sample_api.container.get_mock_endpoint(SAMPLE_API_NAME, SAMPLE_API_VERSION)

        async with aiohttp_resource.acquire_client_session() as session:
            # Try to get a non-existent resource
            async with session.get(f"{base_url}/api/errors/not-found") as response:
                if response.status == HTTPStatus.NOT_FOUND:
                    error_data: dict[str, Any] = await response.json()
                    assert "error" in error_data

            # Handle server error gracefully
            async with session.get(f"{base_url}/api/errors/server-error") as response:
                assert response.status == HTTPStatus.INTERNAL_SERVER_ERROR
                # Application should handle this gracefully
                assert not response.ok
