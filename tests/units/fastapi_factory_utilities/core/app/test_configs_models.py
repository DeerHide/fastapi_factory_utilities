"""Provides unit tests for the app configs models."""

import pytest
from pydantic_core import ValidationError

from fastapi_factory_utilities.core.app.config import (
    BaseApplicationConfig,
    CorsConfig,
    DevelopmentConfig,
    ServerConfig,
)


class TestAppConfigsModels:
    """Unit tests for the app configs models."""

    def test_cors_can_be_initialized_with_default_values(self) -> None:
        """Test that the CorsConfig can be initialized with default values."""
        cors = CorsConfig()
        assert cors.allow_origins == []
        assert cors.allow_credentials is False
        assert cors.allow_methods == ["*"]
        assert cors.allow_headers == ["*"]
        assert cors.expose_headers == []
        assert cors.max_age == 600

    def test_cors_rejects_wildcard_origins_with_credentials(self) -> None:
        """Wildcard origins with credentials is the Starlette Origin-reflect footgun."""
        with pytest.raises(ValidationError, match="allow_origins cannot include"):
            CorsConfig(allow_origins=["*"], allow_credentials=True)

    def test_cors_allows_wildcard_origins_without_credentials(self) -> None:
        """Wildcard origins remain valid when credentials are disabled."""
        cors = CorsConfig(allow_origins=["*"], allow_credentials=False)
        assert cors.allow_origins == ["*"]
        assert cors.allow_credentials is False

    def test_cors_allows_explicit_origins_with_credentials(self) -> None:
        """Explicit origins may enable credentials."""
        cors = CorsConfig(
            allow_origins=["https://app.example"],
            allow_credentials=True,
        )
        assert cors.allow_origins == ["https://app.example"]
        assert cors.allow_credentials is True

    def test_server_can_be_initialized_with_default_values(self) -> None:
        """Test that the ServerConfig can be initialized with default values."""
        server = ServerConfig()
        assert server.host is not None
        assert server.port is not None
        assert server.workers is not None

    def test_development_can_be_initialized_with_default_values(self) -> None:
        """Test that the DevelopmentConfig can be initialized with default values."""
        development = DevelopmentConfig()
        assert development.reload is not None
        assert development.debug is not None

    def test_development_values_are_false_by_default(self) -> None:
        """Test that the DevelopmentConfig values are False by default."""
        development = DevelopmentConfig()
        assert development.reload is False
        assert development.debug is False

    def test_application_can_not_be_initialized_without_values(self) -> None:
        """Test that the ServerConfig can not be initialized without values."""
        with pytest.raises(ValidationError):
            BaseApplicationConfig()  # type: ignore
