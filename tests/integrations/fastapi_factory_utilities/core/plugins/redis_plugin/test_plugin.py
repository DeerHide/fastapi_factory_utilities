"""Integration tests for RedisPlugin against testcontainers Redis."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request
from redis.asyncio import Redis

from fastapi_factory_utilities.core.plugins.redis_plugin import (
    STATE_REDIS_CLIENT_KEY,
    RedisPlugin,
    depends_redis,
)
from fastapi_factory_utilities.core.plugins.redis_plugin.configs import RedisCredentialsConfig
from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol
from fastapi_factory_utilities.core.services.status.services import StatusService
from tests.fixtures.redis import RedisFixture


class TestRedisPluginIntegration:
    """Integration tests for ``RedisPlugin`` with a real Redis container."""

    @pytest.fixture
    def mock_application(self) -> MagicMock:
        """Create a mock application with FastAPI state and status service."""
        app: MagicMock = MagicMock(spec=ApplicationAbstractProtocol)
        app.PACKAGE_NAME = "test"
        fastapi_app: FastAPI = FastAPI()
        app.get_asgi_app.return_value = fastapi_app
        app.get_status_service.return_value = StatusService()
        return app

    async def test_lifecycle_ping_get_set_and_depends(
        self,
        redis_container: RedisFixture,
        mock_application: MagicMock,
    ) -> None:
        """Ping, GET/SET via Depends (HTTP-style request), and clean aclose."""
        plugin: RedisPlugin = RedisPlugin(
            name_suffix="test-svc",
            redis_credentials_config=RedisCredentialsConfig(url=redis_container.get_connection_url()),
        )
        plugin.set_application(mock_application)
        plugin.on_load()
        await plugin.on_startup()

        fastapi_app: FastAPI = mock_application.get_asgi_app.return_value
        client: Redis = getattr(fastapi_app.state, STATE_REDIS_CLIENT_KEY)
        assert await client.ping() is True

        key: str = plugin.build_key("count", "widgets", "digest1")
        assert key.startswith("test-svc:count:widgets:")
        await client.set(key, "42", ex=30)
        assert await client.get(key) == "42"

        # HTTP-style Depends accessor
        mock_request: MagicMock = MagicMock(spec=Request)
        mock_request.app = fastapi_app
        depends_client: Redis = depends_redis(mock_request)
        assert await depends_client.get(key) == "42"

        # Taskiq-style: same Depends with a request whose app.state is set
        taskiq_request: MagicMock = MagicMock()
        taskiq_request.app = fastapi_app
        taskiq_client: Redis = depends_redis(taskiq_request)
        assert await taskiq_client.get(key) == "42"

        await plugin.on_shutdown()
        # Client closed; further commands should fail or report closed connection
        with pytest.raises(Exception):
            await client.ping()
