"""Tests for aiohttp plugin configs."""

import pytest
from pydantic import HttpUrl, ValidationError

from fastapi_factory_utilities.core.plugins.aiohttp.configs import HttpServiceDependencyConfig

# Test constants for default configuration values
DEFAULT_LIMIT: int = 10
DEFAULT_LIMIT_PER_HOST: int = 10
DEFAULT_TTL_DNS_CACHE: int = 300
DEFAULT_GRACEFUL_SHUTDOWN_TIMEOUT: int = 10

# Test constants for custom configuration values
CUSTOM_LIMIT_LARGE: int = 100
CUSTOM_LIMIT_MEDIUM: int = 50
CUSTOM_LIMIT_SMALL: int = 20
CUSTOM_LIMIT_PER_HOST_LARGE: int = 50
CUSTOM_LIMIT_PER_HOST_MEDIUM: int = 25
CUSTOM_LIMIT_PER_HOST_SMALL: int = 10
CUSTOM_TTL_DNS_CACHE: int = 600
CUSTOM_GRACEFUL_SHUTDOWN_SMALL: int = 20
CUSTOM_GRACEFUL_SHUTDOWN_MEDIUM: int = 30


class TestHttpServiceDependencyConfig:
    """Test cases for HttpServiceDependencyConfig class."""

    def test_default_values(self) -> None:
        """Test that default values are properly set."""
        config = HttpServiceDependencyConfig()

        assert config.url is None
        assert config.limit == DEFAULT_LIMIT
        assert config.limit_per_host == DEFAULT_LIMIT_PER_HOST
        assert config.use_dns_cache is True
        assert config.ttl_dns_cache == DEFAULT_TTL_DNS_CACHE
        assert config.verify_ssl is True
        assert config.ssl_ca_path is None
        assert config.ssl_certfile is None
        assert config.ssl_keyfile is None
        assert config.ssl_keyfile_password is None
        assert config.graceful_shutdown_timeout == DEFAULT_GRACEFUL_SHUTDOWN_TIMEOUT

    def test_with_valid_url(self) -> None:
        """Test config with valid HTTP URL."""
        config = HttpServiceDependencyConfig(url=HttpUrl("https://api.example.com"))

        assert config.url is not None
        assert str(config.url) == "https://api.example.com/"

    def test_with_custom_pool_configuration(self) -> None:
        """Test config with custom pool configuration."""
        config = HttpServiceDependencyConfig(
            limit=CUSTOM_LIMIT_LARGE,
            limit_per_host=CUSTOM_LIMIT_PER_HOST_LARGE,
        )

        assert config.limit == CUSTOM_LIMIT_LARGE
        assert config.limit_per_host == CUSTOM_LIMIT_PER_HOST_LARGE

    def test_with_custom_dns_cache_configuration(self) -> None:
        """Test config with custom DNS cache configuration."""
        config = HttpServiceDependencyConfig(
            use_dns_cache=False,
            ttl_dns_cache=CUSTOM_TTL_DNS_CACHE,
        )

        assert config.use_dns_cache is False
        assert config.ttl_dns_cache == CUSTOM_TTL_DNS_CACHE

    def test_with_ssl_verification_disabled(self) -> None:
        """Test config with SSL verification disabled."""
        config = HttpServiceDependencyConfig(verify_ssl=False)

        assert config.verify_ssl is False

    def test_with_ssl_ca_path(self) -> None:
        """Test config with custom SSL CA path."""
        ca_path = "/path/to/ca-bundle.crt"
        config = HttpServiceDependencyConfig(ssl_ca_path=ca_path)

        assert config.ssl_ca_path == ca_path

    def test_with_ssl_client_certificate(self) -> None:
        """Test config with SSL client certificate configuration."""
        config = HttpServiceDependencyConfig(
            ssl_certfile="/path/to/cert.pem",
            ssl_keyfile="/path/to/key.pem",
            ssl_keyfile_password="secret123",
        )

        assert config.ssl_certfile == "/path/to/cert.pem"
        assert config.ssl_keyfile == "/path/to/key.pem"
        assert config.ssl_keyfile_password == "secret123"

    def test_with_custom_graceful_shutdown_timeout(self) -> None:
        """Test config with custom graceful shutdown timeout."""
        config = HttpServiceDependencyConfig(graceful_shutdown_timeout=CUSTOM_GRACEFUL_SHUTDOWN_MEDIUM)

        assert config.graceful_shutdown_timeout == CUSTOM_GRACEFUL_SHUTDOWN_MEDIUM

    def test_full_configuration(self) -> None:
        """Test config with all options configured."""
        config = HttpServiceDependencyConfig(
            url=HttpUrl("https://api.example.com"),
            limit=CUSTOM_LIMIT_MEDIUM,
            limit_per_host=CUSTOM_LIMIT_PER_HOST_MEDIUM,
            use_dns_cache=True,
            ttl_dns_cache=CUSTOM_TTL_DNS_CACHE,
            verify_ssl=True,
            ssl_ca_path="/path/to/ca.crt",
            ssl_certfile="/path/to/cert.pem",
            ssl_keyfile="/path/to/key.pem",
            ssl_keyfile_password="secret",
            graceful_shutdown_timeout=CUSTOM_GRACEFUL_SHUTDOWN_SMALL,
        )

        assert str(config.url) == "https://api.example.com/"
        assert config.limit == CUSTOM_LIMIT_MEDIUM
        assert config.limit_per_host == CUSTOM_LIMIT_PER_HOST_MEDIUM
        assert config.use_dns_cache is True
        assert config.ttl_dns_cache == CUSTOM_TTL_DNS_CACHE
        assert config.verify_ssl is True
        assert config.ssl_ca_path == "/path/to/ca.crt"
        assert config.ssl_certfile == "/path/to/cert.pem"
        assert config.ssl_keyfile == "/path/to/key.pem"
        assert config.ssl_keyfile_password == "secret"
        assert config.graceful_shutdown_timeout == CUSTOM_GRACEFUL_SHUTDOWN_SMALL

    def test_from_dict(self) -> None:
        """Test creating config from dictionary."""
        data = {
            "url": "https://api.example.com",
            "limit": CUSTOM_LIMIT_SMALL,
            "limit_per_host": CUSTOM_LIMIT_PER_HOST_SMALL,
        }
        config = HttpServiceDependencyConfig(**data)

        assert str(config.url) == "https://api.example.com/"
        assert config.limit == CUSTOM_LIMIT_SMALL
        assert config.limit_per_host == CUSTOM_LIMIT_PER_HOST_SMALL

    def test_invalid_url_raises_validation_error(self) -> None:
        """Test that invalid URL raises ValidationError."""
        with pytest.raises(ValidationError):
            HttpServiceDependencyConfig(url="not-a-valid-url")  # type: ignore[arg-type]  # pyright: ignore

    @pytest.mark.parametrize(
        "limit,limit_per_host",
        [
            (1, 1),
            (100, 100),
            (1000, 500),
        ],
    )
    def test_various_pool_limits(self, limit: int, limit_per_host: int) -> None:
        """Test various pool limit configurations."""
        config = HttpServiceDependencyConfig(
            limit=limit,
            limit_per_host=limit_per_host,
        )

        assert config.limit == limit
        assert config.limit_per_host == limit_per_host
