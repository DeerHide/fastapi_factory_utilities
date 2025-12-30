"""Tests for aiohttp plugin resources."""
# pylint: disable=protected-access

import ssl
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from pydantic import HttpUrl

from fastapi_factory_utilities.core.plugins.aiohttp.configs import HttpServiceDependencyConfig
from fastapi_factory_utilities.core.plugins.aiohttp.exceptions import AioHttpClientError
from fastapi_factory_utilities.core.plugins.aiohttp.resources import AioHttpClientResource

# Test constants
CUSTOM_LIMIT: int = 50
CUSTOM_LIMIT_PER_HOST: int = 25
CUSTOM_GRACEFUL_SHUTDOWN: int = 30


class TestAioHttpClientResourceInit:
    """Test cases for AioHttpClientResource initialization."""

    def test_init(self) -> None:
        """Test AioHttpClientResource initialization."""
        config = HttpServiceDependencyConfig()
        resource = AioHttpClientResource(dependency_config=config)

        assert resource._dependency_config == config  # pylint: disable=protected-access
        assert resource._tcp_connector is None  # pylint: disable=protected-access
        assert not resource._client_sessions  # pylint: disable=protected-access
        assert resource._tracer_provider is None  # pylint: disable=protected-access
        assert resource._meter_provider is None  # pylint: disable=protected-access

    def test_init_with_custom_config(self) -> None:
        """Test initialization with custom configuration."""
        config = HttpServiceDependencyConfig(
            limit=CUSTOM_LIMIT,
            limit_per_host=CUSTOM_LIMIT_PER_HOST,
            graceful_shutdown_timeout=CUSTOM_GRACEFUL_SHUTDOWN,
        )
        resource = AioHttpClientResource(dependency_config=config)

        assert resource._dependency_config.limit == CUSTOM_LIMIT
        assert resource._dependency_config.limit_per_host == CUSTOM_LIMIT_PER_HOST
        assert resource._dependency_config.graceful_shutdown_timeout == CUSTOM_GRACEFUL_SHUTDOWN


class TestAioHttpClientResourceBuildSslContext:
    """Test cases for build_ssl_context class method."""

    def test_ssl_verification_disabled(self) -> None:
        """Test SSL context when verification is disabled."""
        config = HttpServiceDependencyConfig(verify_ssl=False)

        result = AioHttpClientResource.build_ssl_context(dependency_config=config)

        assert result is False

    def test_ssl_with_default_ca(self) -> None:
        """Test SSL context with default CA from certifi."""
        config = HttpServiceDependencyConfig(verify_ssl=True)

        with patch("fastapi_factory_utilities.core.plugins.aiohttp.resources.certifi") as mock_certifi:
            mock_certifi.where.return_value = "/path/to/certifi/cacert.pem"
            with patch("ssl.create_default_context") as mock_create_context:
                mock_context = MagicMock(spec=ssl.SSLContext)
                mock_create_context.return_value = mock_context

                result = AioHttpClientResource.build_ssl_context(dependency_config=config)

                assert result == mock_context
                mock_certifi.where.assert_called_once()
                mock_create_context.assert_called_once_with(cafile="/path/to/certifi/cacert.pem")

    def test_ssl_with_custom_ca_path(self) -> None:
        """Test SSL context with custom CA path."""
        ca_path = "/path/to/custom/ca.crt"
        config = HttpServiceDependencyConfig(verify_ssl=True, ssl_ca_path=ca_path)

        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("ssl.create_default_context") as mock_create_context:
                mock_context = MagicMock(spec=ssl.SSLContext)
                mock_create_context.return_value = mock_context

                result = AioHttpClientResource.build_ssl_context(dependency_config=config)

                assert result == mock_context
                mock_create_context.assert_called_once_with(cafile=ca_path)

    def test_ssl_with_nonexistent_ca_path(self) -> None:
        """Test SSL context with non-existent CA path raises error."""
        ca_path = "/path/to/nonexistent/ca.crt"
        config = HttpServiceDependencyConfig(verify_ssl=True, ssl_ca_path=ca_path)

        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = False

            with patch("fastapi_factory_utilities.core.exceptions._logger"):
                with patch("fastapi_factory_utilities.core.exceptions.get_current_span", MagicMock()):
                    with pytest.raises(AioHttpClientError) as exc_info:
                        AioHttpClientResource.build_ssl_context(dependency_config=config)

                    assert ca_path in str(exc_info.value)

    def test_ssl_with_client_certificate(self) -> None:
        """Test SSL context with client certificate."""
        config = HttpServiceDependencyConfig(
            verify_ssl=True,
            ssl_certfile="/path/to/cert.pem",
            ssl_keyfile="/path/to/key.pem",
        )

        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("fastapi_factory_utilities.core.plugins.aiohttp.resources.certifi") as mock_certifi:
                mock_certifi.where.return_value = "/path/to/certifi/cacert.pem"
                with patch("ssl.create_default_context") as mock_create_context:
                    mock_context = MagicMock(spec=ssl.SSLContext)
                    mock_create_context.return_value = mock_context

                    result = AioHttpClientResource.build_ssl_context(dependency_config=config)

                    assert result == mock_context
                    mock_context.load_cert_chain.assert_called_once_with("/path/to/cert.pem", "/path/to/key.pem")

    def test_ssl_with_client_certificate_and_password(self) -> None:
        """Test SSL context with client certificate and password."""
        config = HttpServiceDependencyConfig(
            verify_ssl=True,
            ssl_certfile="/path/to/cert.pem",
            ssl_keyfile="/path/to/key.pem",
            ssl_keyfile_password="secret123",
        )

        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("fastapi_factory_utilities.core.plugins.aiohttp.resources.certifi") as mock_certifi:
                mock_certifi.where.return_value = "/path/to/certifi/cacert.pem"
                with patch("ssl.create_default_context") as mock_create_context:
                    mock_context = MagicMock(spec=ssl.SSLContext)
                    mock_create_context.return_value = mock_context

                    result = AioHttpClientResource.build_ssl_context(dependency_config=config)

                    assert result == mock_context
                    mock_context.load_cert_chain.assert_called_once_with(
                        "/path/to/cert.pem", "/path/to/key.pem", password="secret123"
                    )

    def test_ssl_with_nonexistent_certfile(self) -> None:
        """Test SSL context with non-existent cert file raises error."""
        config = HttpServiceDependencyConfig(
            verify_ssl=True,
            ssl_certfile="/path/to/nonexistent/cert.pem",
            ssl_keyfile="/path/to/key.pem",
        )

        def exists_side_effect(path: str) -> bool:
            return path != "/path/to/nonexistent/cert.pem"

        with patch("os.path.exists") as mock_exists:
            mock_exists.side_effect = exists_side_effect
            with patch("fastapi_factory_utilities.core.plugins.aiohttp.resources.certifi") as mock_certifi:
                mock_certifi.where.return_value = "/path/to/certifi/cacert.pem"
                with patch("ssl.create_default_context"):
                    with patch("fastapi_factory_utilities.core.exceptions._logger"):
                        with patch("fastapi_factory_utilities.core.exceptions.get_current_span", MagicMock()):
                            with pytest.raises(AioHttpClientError):
                                AioHttpClientResource.build_ssl_context(dependency_config=config)

    def test_ssl_with_nonexistent_keyfile(self) -> None:
        """Test SSL context with non-existent key file raises error."""
        config = HttpServiceDependencyConfig(
            verify_ssl=True,
            ssl_certfile="/path/to/cert.pem",
            ssl_keyfile="/path/to/nonexistent/key.pem",
        )

        def exists_side_effect(path: str) -> bool:
            return path != "/path/to/nonexistent/key.pem"

        with patch("os.path.exists") as mock_exists:
            mock_exists.side_effect = exists_side_effect
            with patch("fastapi_factory_utilities.core.plugins.aiohttp.resources.certifi") as mock_certifi:
                mock_certifi.where.return_value = "/path/to/certifi/cacert.pem"
                with patch("ssl.create_default_context"):
                    with patch("fastapi_factory_utilities.core.exceptions._logger"):
                        with patch("fastapi_factory_utilities.core.exceptions.get_current_span", MagicMock()):
                            with pytest.raises(AioHttpClientError):
                                AioHttpClientResource.build_ssl_context(dependency_config=config)


class TestAioHttpClientResourceBuildTcpConnector:
    """Test cases for build_tcp_connector class method."""

    def test_build_tcp_connector(self) -> None:
        """Test TCP connector creation with configuration."""
        config = HttpServiceDependencyConfig(
            limit=50,
            limit_per_host=25,
            use_dns_cache=True,
            ttl_dns_cache=600,
            verify_ssl=False,
        )

        with patch(
            "fastapi_factory_utilities.core.plugins.aiohttp.resources.AioHttpClientResource.build_ssl_context"
        ) as mock_ssl:
            mock_ssl.return_value = False
            with patch(
                "fastapi_factory_utilities.core.plugins.aiohttp.resources.aiohttp.TCPConnector"
            ) as mock_connector:
                mock_connector_instance = MagicMock()
                mock_connector.return_value = mock_connector_instance

                result = AioHttpClientResource.build_tcp_connector(dependency_config=config)

                assert result == mock_connector_instance
                mock_connector.assert_called_once_with(
                    limit=50,
                    limit_per_host=25,
                    use_dns_cache=True,
                    ttl_dns_cache=600,
                    ssl=False,
                )


class TestAioHttpClientResourceBuildTraceConfig:
    """Test cases for build_trace_config class method."""

    def test_build_trace_config_with_no_providers(self) -> None:
        """Test trace config returns None when providers are None."""
        result = AioHttpClientResource.build_trace_config(tracer_provider=None, meter_provider=None)

        assert result is None

    def test_build_trace_config_with_tracer_only(self) -> None:
        """Test trace config returns None when only tracer provider is set."""
        mock_tracer = MagicMock()

        result = AioHttpClientResource.build_trace_config(tracer_provider=mock_tracer, meter_provider=None)

        assert result is None

    def test_build_trace_config_with_meter_only(self) -> None:
        """Test trace config returns None when only meter provider is set."""
        mock_meter = MagicMock()

        result = AioHttpClientResource.build_trace_config(tracer_provider=None, meter_provider=mock_meter)

        assert result is None

    def test_build_trace_config_with_providers_and_instrumentation(self) -> None:
        """Test trace config with OpenTelemetry instrumentation available."""
        mock_tracer = MagicMock()
        mock_meter = MagicMock()
        mock_trace_config = MagicMock(spec=aiohttp.TraceConfig)

        with patch("fastapi_factory_utilities.core.plugins.aiohttp.resources.find_spec") as mock_find_spec:
            mock_find_spec.return_value = MagicMock()  # Spec found
            with patch.dict(
                "sys.modules",
                {"opentelemetry.instrumentation.aiohttp_client": MagicMock()},
            ):
                with patch("opentelemetry.instrumentation.aiohttp_client.create_trace_config") as mock_create:
                    mock_create.return_value = mock_trace_config

                    result = AioHttpClientResource.build_trace_config(
                        tracer_provider=mock_tracer, meter_provider=mock_meter
                    )

                    assert result == mock_trace_config

    def test_build_trace_config_without_instrumentation(self) -> None:
        """Test trace config returns None when instrumentation is not available."""
        mock_tracer = MagicMock()
        mock_meter = MagicMock()

        with patch("fastapi_factory_utilities.core.plugins.aiohttp.resources.find_spec") as mock_find_spec:
            mock_find_spec.return_value = None  # Spec not found

            result = AioHttpClientResource.build_trace_config(tracer_provider=mock_tracer, meter_provider=mock_meter)

            assert result is None


class TestAioHttpClientResourceOnLoad:
    """Test cases for on_load method."""

    def test_on_load(self) -> None:
        """Test on_load method does nothing (placeholder)."""
        config = HttpServiceDependencyConfig()
        resource = AioHttpClientResource(dependency_config=config)

        # Should not raise any exceptions
        resource.on_load()


class TestAioHttpClientResourceOnStartup:
    """Test cases for on_startup method."""

    async def test_on_startup_creates_tcp_connector(self) -> None:
        """Test on_startup creates TCP connector."""
        config = HttpServiceDependencyConfig()
        resource = AioHttpClientResource(dependency_config=config)

        mock_connector = MagicMock(spec=aiohttp.TCPConnector)

        with patch.object(AioHttpClientResource, "build_tcp_connector", return_value=mock_connector):
            await resource.on_startup()

            assert resource._tcp_connector == mock_connector

    async def test_on_startup_sets_providers(self) -> None:
        """Test on_startup sets tracer and meter providers."""
        config = HttpServiceDependencyConfig()
        resource = AioHttpClientResource(dependency_config=config)

        mock_tracer = MagicMock()
        mock_meter = MagicMock()

        with patch.object(AioHttpClientResource, "build_tcp_connector"):
            await resource.on_startup(tracer_provider=mock_tracer, meter_provider=mock_meter)

            assert resource._tracer_provider == mock_tracer
            assert resource._meter_provider == mock_meter

    async def test_on_startup_does_not_recreate_connector(self) -> None:
        """Test on_startup does not recreate TCP connector if already exists."""
        config = HttpServiceDependencyConfig()
        resource = AioHttpClientResource(dependency_config=config)

        existing_connector = MagicMock(spec=aiohttp.TCPConnector)
        resource._tcp_connector = existing_connector

        with patch.object(AioHttpClientResource, "build_tcp_connector") as mock_build:
            await resource.on_startup()

            mock_build.assert_not_called()
            assert resource._tcp_connector == existing_connector


class TestAioHttpClientResourceOnShutdown:
    """Test cases for on_shutdown method."""

    async def test_on_shutdown_closes_tcp_connector(self) -> None:
        """Test on_shutdown closes TCP connector."""
        config = HttpServiceDependencyConfig(graceful_shutdown_timeout=0)
        resource = AioHttpClientResource(dependency_config=config)

        mock_connector = AsyncMock(spec=aiohttp.TCPConnector)
        resource._tcp_connector = mock_connector

        await resource.on_shutdown()

        mock_connector.close.assert_called_once()

    async def test_on_shutdown_closes_client_sessions(self) -> None:
        """Test on_shutdown closes remaining client sessions."""
        config = HttpServiceDependencyConfig(graceful_shutdown_timeout=0)
        resource = AioHttpClientResource(dependency_config=config)

        mock_session1 = AsyncMock(spec=aiohttp.ClientSession)
        mock_session2 = AsyncMock(spec=aiohttp.ClientSession)
        resource._client_sessions = [mock_session1, mock_session2]
        resource._tcp_connector = AsyncMock()

        await resource.on_shutdown()

        mock_session1.close.assert_called_once()
        mock_session2.close.assert_called_once()

    async def test_on_shutdown_handles_connector_close_error(self) -> None:
        """Test on_shutdown handles errors when closing TCP connector."""
        config = HttpServiceDependencyConfig(graceful_shutdown_timeout=0)
        resource = AioHttpClientResource(dependency_config=config)

        mock_connector = AsyncMock(spec=aiohttp.TCPConnector)
        mock_connector.close.side_effect = OSError("Connection error")
        resource._tcp_connector = mock_connector

        # Should not raise, should log warning
        await resource.on_shutdown()

    async def test_on_shutdown_handles_session_close_error(self) -> None:
        """Test on_shutdown handles errors when closing client sessions."""
        config = HttpServiceDependencyConfig(graceful_shutdown_timeout=0)
        resource = AioHttpClientResource(dependency_config=config)

        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.close.side_effect = aiohttp.ClientError("Session error")
        resource._client_sessions = [mock_session]
        resource._tcp_connector = AsyncMock()

        # Should not raise, should log warning
        await resource.on_shutdown()

    async def test_on_shutdown_with_no_connector(self) -> None:
        """Test on_shutdown when TCP connector is None."""
        config = HttpServiceDependencyConfig(graceful_shutdown_timeout=0)
        resource = AioHttpClientResource(dependency_config=config)

        # Should not raise
        await resource.on_shutdown()


class TestAioHttpClientResourceAcquireClientSession:
    """Test cases for acquire_client_session method."""

    async def test_acquire_client_session_success(self) -> None:
        """Test successful client session acquisition."""
        config = HttpServiceDependencyConfig()
        resource = AioHttpClientResource(dependency_config=config)

        mock_connector = MagicMock()
        resource._tcp_connector = mock_connector  # pyright: ignore[reportPrivateUsage]

        with patch.object(AioHttpClientResource, "build_trace_config", return_value=None):
            with patch(
                "fastapi_factory_utilities.core.plugins.aiohttp.resources.aiohttp.ClientSession"
            ) as mock_session_class:
                mock_session = MagicMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session_class.return_value = mock_session

                async with resource.acquire_client_session() as session:
                    assert session == mock_session
                    assert mock_session in resource._client_sessions  # pyright: ignore[reportPrivateUsage]

                assert mock_session not in resource._client_sessions  # pyright: ignore[reportPrivateUsage]

    async def test_acquire_client_session_raises_without_connector(self) -> None:
        """Test acquire_client_session raises when connector not initialized."""
        config = HttpServiceDependencyConfig()
        resource = AioHttpClientResource(dependency_config=config)

        with pytest.raises(AioHttpClientError) as exc_info:
            async with resource.acquire_client_session():
                pass

        assert "TCP connector is not initialized" in str(exc_info.value)

    async def test_acquire_client_session_raises_with_connector_in_kwargs(self) -> None:
        """Test acquire_client_session raises when connector provided in kwargs."""
        config = HttpServiceDependencyConfig()
        resource = AioHttpClientResource(dependency_config=config)

        mock_connector = MagicMock(spec=aiohttp.TCPConnector)
        resource._tcp_connector = mock_connector

        with pytest.raises(ValueError) as exc_info:
            async with resource.acquire_client_session(connector=MagicMock()):
                pass

        assert "connector is already provided" in str(exc_info.value)

    async def test_acquire_client_session_with_trace_config(self) -> None:
        """Test acquire_client_session passes trace config when available."""
        config = HttpServiceDependencyConfig()
        resource = AioHttpClientResource(dependency_config=config)

        mock_connector = MagicMock()
        mock_trace_config = MagicMock()
        resource._tcp_connector = mock_connector  # pyright: ignore[reportPrivateUsage]

        with patch.object(AioHttpClientResource, "build_trace_config", return_value=mock_trace_config):
            with patch(
                "fastapi_factory_utilities.core.plugins.aiohttp.resources.aiohttp.ClientSession"
            ) as mock_session_class:
                mock_session = MagicMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session_class.return_value = mock_session

                async with resource.acquire_client_session():
                    pass

                # Verify trace_config was passed
                call_kwargs: dict[str, Any] = mock_session_class.call_args.kwargs
                assert "trace_configs" in call_kwargs
                assert call_kwargs["trace_configs"] == [mock_trace_config]
                assert call_kwargs["connector_owner"] is False

    async def test_acquire_client_session_passes_additional_kwargs(self) -> None:
        """Test acquire_client_session passes additional kwargs to ClientSession."""
        config = HttpServiceDependencyConfig()
        resource = AioHttpClientResource(dependency_config=config)

        mock_connector = MagicMock()
        mock_connector.closed = False
        resource._tcp_connector = mock_connector  # pyright: ignore[reportPrivateUsage]

        custom_timeout = aiohttp.ClientTimeout(total=30)

        with patch.object(AioHttpClientResource, "build_trace_config", return_value=None):
            with patch(
                "fastapi_factory_utilities.core.plugins.aiohttp.resources.aiohttp.ClientSession"
            ) as mock_session_class:
                mock_session = MagicMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session_class.return_value = mock_session

                async with resource.acquire_client_session(timeout=custom_timeout):
                    pass

                call_kwargs: dict[str, Any] = mock_session_class.call_args.kwargs
                assert call_kwargs["timeout"] == custom_timeout
                assert call_kwargs["connector"] == mock_connector
                assert call_kwargs["connector_owner"] is False

    async def test_acquire_client_session_removes_session_on_exception(self) -> None:
        """Test acquire_client_session removes session from list on exception."""
        config = HttpServiceDependencyConfig()
        resource = AioHttpClientResource(dependency_config=config)

        mock_connector = MagicMock()
        resource._tcp_connector = mock_connector  # pyright: ignore[reportPrivateUsage]

        with patch.object(AioHttpClientResource, "build_trace_config", return_value=None):
            with patch(
                "fastapi_factory_utilities.core.plugins.aiohttp.resources.aiohttp.ClientSession"
            ) as mock_session_class:
                mock_session = MagicMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session_class.return_value = mock_session

                with pytest.raises(ValueError):
                    async with resource.acquire_client_session():
                        assert mock_session in resource._client_sessions  # pyright: ignore[reportPrivateUsage]
                        raise ValueError("Test error")

                assert mock_session not in resource._client_sessions  # pyright: ignore[reportPrivateUsage]

    async def test_acquire_client_session_without_base_url(self) -> None:
        """Test acquire_client_session does not set base_url when url is None."""
        config = HttpServiceDependencyConfig()
        resource = AioHttpClientResource(dependency_config=config)

        mock_connector = MagicMock()
        mock_connector.closed = False
        resource._tcp_connector = mock_connector  # pyright: ignore[reportPrivateUsage]

        with patch.object(AioHttpClientResource, "build_trace_config", return_value=None):
            with patch(
                "fastapi_factory_utilities.core.plugins.aiohttp.resources.aiohttp.ClientSession"
            ) as mock_session_class:
                mock_session = MagicMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session_class.return_value = mock_session

                async with resource.acquire_client_session():
                    pass

                call_kwargs: dict[str, Any] = mock_session_class.call_args.kwargs
                assert "base_url" not in call_kwargs
                assert call_kwargs["connector"] == mock_connector
                assert call_kwargs["connector_owner"] is False

    async def test_acquire_client_session_with_base_url(self) -> None:
        """Test acquire_client_session sets base_url when url is provided."""
        config = HttpServiceDependencyConfig(url=HttpUrl("http://example.com"))
        resource = AioHttpClientResource(dependency_config=config)

        mock_connector = MagicMock()
        mock_connector.closed = False
        resource._tcp_connector = mock_connector  # pyright: ignore[reportPrivateUsage]

        with patch.object(AioHttpClientResource, "build_trace_config", return_value=None):
            with patch(
                "fastapi_factory_utilities.core.plugins.aiohttp.resources.aiohttp.ClientSession"
            ) as mock_session_class:
                mock_session = MagicMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session_class.return_value = mock_session

                async with resource.acquire_client_session():
                    pass

                call_kwargs: dict[str, Any] = mock_session_class.call_args.kwargs
                assert "base_url" in call_kwargs
                assert call_kwargs["base_url"] == "http://example.com/"
                assert call_kwargs["connector"] == mock_connector
                assert call_kwargs["connector_owner"] is False

    async def test_acquire_client_session_sets_connector_owner_to_false(self) -> None:
        """Test acquire_client_session sets connector_owner to False."""
        config = HttpServiceDependencyConfig()
        resource = AioHttpClientResource(dependency_config=config)

        mock_connector = MagicMock()
        mock_connector.closed = False
        resource._tcp_connector = mock_connector  # pyright: ignore[reportPrivateUsage]

        with patch.object(AioHttpClientResource, "build_trace_config", return_value=None):
            with patch(
                "fastapi_factory_utilities.core.plugins.aiohttp.resources.aiohttp.ClientSession"
            ) as mock_session_class:
                mock_session = MagicMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session_class.return_value = mock_session

                async with resource.acquire_client_session():
                    pass

                call_kwargs: dict[str, Any] = mock_session_class.call_args.kwargs
                assert "connector_owner" in call_kwargs
                assert call_kwargs["connector_owner"] is False
                assert call_kwargs["connector"] == mock_connector

    async def test_acquire_client_session_sets_connector_owner_with_trace_config(self) -> None:
        """Test acquire_client_session sets connector_owner to False when trace config is provided."""
        config = HttpServiceDependencyConfig()
        resource = AioHttpClientResource(dependency_config=config)

        mock_connector = MagicMock()
        mock_connector.closed = False
        mock_trace_config = MagicMock()
        resource._tcp_connector = mock_connector  # pyright: ignore[reportPrivateUsage]

        with patch.object(AioHttpClientResource, "build_trace_config", return_value=mock_trace_config):
            with patch(
                "fastapi_factory_utilities.core.plugins.aiohttp.resources.aiohttp.ClientSession"
            ) as mock_session_class:
                mock_session = MagicMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session_class.return_value = mock_session

                async with resource.acquire_client_session():
                    pass

                call_kwargs: dict[str, Any] = mock_session_class.call_args.kwargs
                assert "connector_owner" in call_kwargs
                assert call_kwargs["connector_owner"] is False
                assert call_kwargs["connector"] == mock_connector
                assert "trace_configs" in call_kwargs

    async def test_acquire_client_session_sets_connector_owner_with_base_url(self) -> None:
        """Test acquire_client_session sets connector_owner to False when base_url is provided."""
        config = HttpServiceDependencyConfig(url=HttpUrl("https://api.example.com"))
        resource = AioHttpClientResource(dependency_config=config)

        mock_connector = MagicMock()
        mock_connector.closed = False
        resource._tcp_connector = mock_connector  # pyright: ignore[reportPrivateUsage]

        with patch.object(AioHttpClientResource, "build_trace_config", return_value=None):
            with patch(
                "fastapi_factory_utilities.core.plugins.aiohttp.resources.aiohttp.ClientSession"
            ) as mock_session_class:
                mock_session = MagicMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session_class.return_value = mock_session

                async with resource.acquire_client_session():
                    pass

                call_kwargs: dict[str, Any] = mock_session_class.call_args.kwargs
                assert "connector_owner" in call_kwargs
                assert call_kwargs["connector_owner"] is False
                assert call_kwargs["connector"] == mock_connector
                assert "base_url" in call_kwargs

    async def test_acquire_client_session_connector_not_closed_when_session_closes(self) -> None:
        """Test that connector is not closed when session closes due to connector_owner=False."""
        config = HttpServiceDependencyConfig()
        resource = AioHttpClientResource(dependency_config=config)

        mock_connector = MagicMock()
        mock_connector.closed = False
        resource._tcp_connector = mock_connector  # pyright: ignore[reportPrivateUsage]

        with patch.object(AioHttpClientResource, "build_trace_config", return_value=None):
            with patch(
                "fastapi_factory_utilities.core.plugins.aiohttp.resources.aiohttp.ClientSession"
            ) as mock_session_class:
                mock_session = MagicMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session_class.return_value = mock_session

                async with resource.acquire_client_session():
                    pass

                # Verify connector_owner was set to False
                call_kwargs: dict[str, Any] = mock_session_class.call_args.kwargs
                assert call_kwargs["connector_owner"] is False

                # Verify the connector's close method was not called when session closed
                # (This is the expected behavior when connector_owner=False)
                mock_connector.close.assert_not_called()
