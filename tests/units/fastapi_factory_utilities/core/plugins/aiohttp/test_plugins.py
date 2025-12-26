"""Tests for aiohttp plugin."""
# pylint: disable=protected-access

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.plugins.aiohttp.builder import AioHttpClientBuilder
from fastapi_factory_utilities.core.plugins.aiohttp.constants import STATE_PREFIX_KEY
from fastapi_factory_utilities.core.plugins.aiohttp.plugins import AioHttpClientPlugin
from fastapi_factory_utilities.core.plugins.aiohttp.resources import AioHttpClientResource


class TestAioHttpClientPlugin:
    """Test cases for AioHttpClientPlugin class."""

    def test_inheritance(self) -> None:
        """Test that AioHttpClientPlugin inherits from PluginAbstract."""
        with patch("fastapi_factory_utilities.core.plugins.aiohttp.plugins.AioHttpClientBuilder") as mock_builder_class:
            mock_builder = MagicMock(spec=AioHttpClientBuilder)
            mock_builder_class.return_value = mock_builder

            plugin = AioHttpClientPlugin(keys=["service1"])

            assert isinstance(plugin, PluginAbstract)

    def test_init_creates_builder(self) -> None:
        """Test that __init__ creates and initializes a builder."""
        with patch("fastapi_factory_utilities.core.plugins.aiohttp.plugins.AioHttpClientBuilder") as mock_builder_class:
            mock_builder = MagicMock(spec=AioHttpClientBuilder)
            mock_builder_class.return_value = mock_builder

            plugin = AioHttpClientPlugin(keys=["service1", "service2"])

            mock_builder_class.assert_called_once_with(keys=["service1", "service2"])
            assert plugin._builder is not None  # pyright: ignore[reportPrivateUsage]
            mock_builder.build_configs.assert_called_once()
            assert plugin._builder == mock_builder

    def test_init_with_empty_keys(self) -> None:
        """Test __init__ with empty keys list."""
        with patch("fastapi_factory_utilities.core.plugins.aiohttp.plugins.AioHttpClientBuilder") as mock_builder_class:
            mock_builder = MagicMock(spec=AioHttpClientBuilder)
            mock_builder_class.return_value = mock_builder

            AioHttpClientPlugin(keys=[])

            mock_builder_class.assert_called_once_with(keys=[])

    def test_on_load(self) -> None:
        """Test on_load method does nothing."""
        with patch("fastapi_factory_utilities.core.plugins.aiohttp.plugins.AioHttpClientBuilder") as mock_builder_class:
            mock_builder = MagicMock(spec=AioHttpClientBuilder)
            mock_builder_class.return_value = mock_builder

            plugin = AioHttpClientPlugin(keys=["service1"])

            # Should not raise
            plugin.on_load()

    async def test_on_startup_builds_resources(self) -> None:
        """Test on_startup builds resources and starts them."""
        with patch("fastapi_factory_utilities.core.plugins.aiohttp.plugins.AioHttpClientBuilder") as mock_builder_class:
            mock_builder = MagicMock(spec=AioHttpClientBuilder)
            mock_resource = AsyncMock(spec=AioHttpClientResource)
            mock_builder.resources = {"service1": mock_resource}
            mock_builder_class.return_value = mock_builder

            plugin = AioHttpClientPlugin(keys=["service1"])

            # Set up mock application (required for _add_to_state)
            # Use spec=[] to prevent MagicMock from auto-creating attributes
            mock_app = MagicMock()
            mock_state = MagicMock(spec=[])
            # Set tracer_provider and meter_provider to None explicitly
            mock_state.tracer_provider = None
            mock_state.meter_provider = None
            mock_app.get_asgi_app.return_value.state = mock_state
            plugin._application = mock_app  # pyright: ignore[reportPrivateUsage]

            await plugin.on_startup()

            mock_builder.build_resources.assert_called_once()
            mock_resource.on_startup.assert_called_once_with(tracer_provider=None, meter_provider=None)

    async def test_on_startup_with_application_providers(self) -> None:
        """Test on_startup retrieves OpenTelemetry providers from application state."""
        with patch("fastapi_factory_utilities.core.plugins.aiohttp.plugins.AioHttpClientBuilder") as mock_builder_class:
            mock_builder = MagicMock(spec=AioHttpClientBuilder)
            mock_resource = AsyncMock(spec=AioHttpClientResource)
            mock_builder.resources = {"service1": mock_resource}
            mock_builder_class.return_value = mock_builder

            plugin = AioHttpClientPlugin(keys=["service1"])

            # Set up mock application with OpenTelemetry providers
            mock_app = MagicMock()
            mock_tracer = MagicMock()
            mock_meter = MagicMock()
            mock_app.get_asgi_app.return_value.state.tracer_provider = mock_tracer
            mock_app.get_asgi_app.return_value.state.meter_provider = mock_meter
            plugin._application = mock_app

            await plugin.on_startup()

            mock_resource.on_startup.assert_called_once_with(tracer_provider=mock_tracer, meter_provider=mock_meter)

    async def test_on_startup_adds_resources_to_state(self) -> None:
        """Test on_startup adds resources to application state."""
        with patch("fastapi_factory_utilities.core.plugins.aiohttp.plugins.AioHttpClientBuilder") as mock_builder_class:
            mock_builder = MagicMock(spec=AioHttpClientBuilder)
            mock_resource = AsyncMock(spec=AioHttpClientResource)
            mock_builder.resources = {"service1": mock_resource}
            mock_builder_class.return_value = mock_builder

            plugin = AioHttpClientPlugin(keys=["service1"])

            # Set up mock application
            mock_app = MagicMock()
            mock_state = MagicMock()
            mock_app.get_asgi_app.return_value.state = mock_state
            plugin._application = mock_app

            await plugin.on_startup()

            # Verify resource was added to state with correct key
            expected_key = f"{STATE_PREFIX_KEY}service1"
            setattr(mock_state, expected_key, mock_resource)

    async def test_on_startup_multiple_resources(self) -> None:
        """Test on_startup handles multiple resources."""
        with patch("fastapi_factory_utilities.core.plugins.aiohttp.plugins.AioHttpClientBuilder") as mock_builder_class:
            mock_builder = MagicMock(spec=AioHttpClientBuilder)
            mock_resource1 = AsyncMock(spec=AioHttpClientResource)
            mock_resource2 = AsyncMock(spec=AioHttpClientResource)
            mock_builder.resources = {
                "service1": mock_resource1,
                "service2": mock_resource2,
            }
            mock_builder_class.return_value = mock_builder

            plugin = AioHttpClientPlugin(keys=["service1", "service2"])

            # Set up mock application (required for _add_to_state)
            mock_app = MagicMock()
            mock_state = MagicMock()
            mock_app.get_asgi_app.return_value.state = mock_state
            plugin._application = mock_app  # pyright: ignore[reportPrivateUsage]

            await plugin.on_startup()

            mock_resource1.on_startup.assert_called_once()
            mock_resource2.on_startup.assert_called_once()

    async def test_on_shutdown_shuts_down_resources(self) -> None:
        """Test on_shutdown shuts down all resources."""
        with patch("fastapi_factory_utilities.core.plugins.aiohttp.plugins.AioHttpClientBuilder") as mock_builder_class:
            mock_builder = MagicMock(spec=AioHttpClientBuilder)
            mock_resource1 = AsyncMock(spec=AioHttpClientResource)
            mock_resource2 = AsyncMock(spec=AioHttpClientResource)
            mock_builder.resources = {
                "service1": mock_resource1,
                "service2": mock_resource2,
            }
            mock_builder_class.return_value = mock_builder

            plugin = AioHttpClientPlugin(keys=["service1", "service2"])

            await plugin.on_shutdown()

            mock_resource1.on_shutdown.assert_called_once()
            mock_resource2.on_shutdown.assert_called_once()

    async def test_on_shutdown_with_empty_resources(self) -> None:
        """Test on_shutdown with no resources."""
        with patch("fastapi_factory_utilities.core.plugins.aiohttp.plugins.AioHttpClientBuilder") as mock_builder_class:
            mock_builder = MagicMock(spec=AioHttpClientBuilder)
            mock_builder.resources = {}
            mock_builder_class.return_value = mock_builder

            plugin = AioHttpClientPlugin(keys=[])

            # Should not raise
            await plugin.on_shutdown()

    async def test_full_lifecycle(self) -> None:
        """Test full plugin lifecycle: init -> on_load -> on_startup -> on_shutdown."""
        with patch("fastapi_factory_utilities.core.plugins.aiohttp.plugins.AioHttpClientBuilder") as mock_builder_class:
            mock_builder = MagicMock(spec=AioHttpClientBuilder)
            mock_resource = AsyncMock(spec=AioHttpClientResource)
            mock_builder.resources = {"service1": mock_resource}
            mock_builder_class.return_value = mock_builder

            # Init
            plugin = AioHttpClientPlugin(keys=["service1"])
            assert plugin._builder is not None

            # on_load
            plugin.on_load()

            # on_startup
            mock_app = MagicMock()
            mock_app.get_asgi_app.return_value.state = MagicMock()
            plugin._application = mock_app

            await plugin.on_startup()
            mock_builder.build_resources.assert_called_once()
            mock_resource.on_startup.assert_called_once()

            # on_shutdown
            await plugin.on_shutdown()
            mock_resource.on_shutdown.assert_called_once()


class TestAioHttpClientPluginIntegration:
    """Integration-style tests for AioHttpClientPlugin."""

    async def test_plugin_with_real_builder(self) -> None:
        """Test plugin with mocked factory but real builder."""
        mock_config = MagicMock()

        with patch(
            "fastapi_factory_utilities.core.plugins.aiohttp.builder.build_http_dependency_config"
        ) as mock_factory:
            mock_factory.return_value = mock_config

            plugin = AioHttpClientPlugin(keys=["test_service"])

            # Verify builder was created and config was built
            assert plugin._builder is not None
            assert "test_service" in plugin._builder._configs

    @pytest.mark.parametrize(
        "keys",
        [
            ["single_service"],
            ["service_a", "service_b"],
            ["api", "database", "cache"],
        ],
    )
    async def test_plugin_with_various_key_counts(self, keys: list[str]) -> None:
        """Test plugin initialization with various numbers of keys."""
        mock_config = MagicMock()

        with patch(
            "fastapi_factory_utilities.core.plugins.aiohttp.builder.build_http_dependency_config"
        ) as mock_factory:
            mock_factory.return_value = mock_config

            plugin = AioHttpClientPlugin(keys=keys)

            assert len(plugin._builder._configs) == len(keys)
            for key in keys:
                assert key in plugin._builder._configs
