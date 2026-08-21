"""Test cases for the health endpoint."""

import os
from http import HTTPStatus
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from structlog.stdlib import get_logger
from testcontainers.mongodb import MongoDbContainer

from fastapi_factory_utilities.example.app import AppBuilder

_logger = get_logger(__package__)


class TestApiV1SysHealth:
    """Test the health endpoint."""

    @pytest.mark.asyncio()
    async def test_get_api_v1_sys_health(self, mongodb_server_as_container: MongoDbContainer) -> None:
        """Test the get_api_v1_sys_health function."""
        # Use the container's connection URL directly
        mongo_uri: str = mongodb_server_as_container.get_connection_url()

        with patch.dict(os.environ, {"MONGO_URI": mongo_uri}):
            with TestClient(app=AppBuilder().build()) as client:
                response: Response = client.get(url="/api/v1/sys/health")
                assert response.status_code == HTTPStatus.OK.value
                assert response.json() == {"status": "healthy"}
