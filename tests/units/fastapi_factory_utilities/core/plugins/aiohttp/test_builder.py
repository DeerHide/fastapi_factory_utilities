"""Tests for aiohttp plugin builder."""
# pylint: disable=protected-access

from unittest.mock import MagicMock, patch

from fastapi_factory_utilities.core.plugins.aiohttp.builder import AioHttpClientBuilder
from fastapi_factory_utilities.core.plugins.aiohttp.configs import HttpServiceDependencyConfig
from fastapi_factory_utilities.core.plugins.aiohttp.resources import AioHttpClientResource

# Test constants
EXPECTED_SERVICE_COUNT_TWO: int = 2
EXPECTED_SERVICE_COUNT_THREE: int = 3
TEST_PACKAGE_NAME: str = "test_package"


class TestAioHttpClientBuilder:
    """Test cases for AioHttpClientBuilder class."""

    def _create_mock_application(self) -> MagicMock:
        """Create a mock application for testing."""
        mock_app = MagicMock()
        mock_app.PACKAGE_NAME = TEST_PACKAGE_NAME
        return mock_app

    def test_init(self) -> None:
        """Test AioHttpClientBuilder initialization."""
        keys = ["service1", "service2"]
        mock_app = self._create_mock_application()
        builder = AioHttpClientBuilder(keys=keys, application=mock_app)

        assert builder._keys == keys  # pylint: disable=protected-access
        assert not builder._configs  # pylint: disable=protected-access
        assert not builder._resources  # pylint: disable=protected-access

    def test_init_with_empty_keys(self) -> None:
        """Test AioHttpClientBuilder initialization with empty keys list."""
        mock_app = self._create_mock_application()
        builder = AioHttpClientBuilder(keys=[], application=mock_app)

        assert builder._keys == []  # pylint: disable=protected-access
        assert not builder._configs  # pylint: disable=protected-access
        assert not builder._resources  # pylint: disable=protected-access

    def test_build_configs(self) -> None:
        """Test build_configs method creates configs for each key."""
        keys = ["service1", "service2"]
        mock_app = self._create_mock_application()
        builder = AioHttpClientBuilder(keys=keys, application=mock_app)

        mock_config1 = MagicMock(spec=HttpServiceDependencyConfig)
        mock_config2 = MagicMock(spec=HttpServiceDependencyConfig)

        with patch(
            "fastapi_factory_utilities.core.plugins.aiohttp.builder.build_http_dependency_config"
        ) as mock_factory:
            mock_factory.side_effect = [mock_config1, mock_config2]

            result = builder.build_configs()

            assert result is builder  # Returns self for chaining
            assert builder._configs["service1"] == mock_config1
            assert builder._configs["service2"] == mock_config2
            assert mock_factory.call_count == EXPECTED_SERVICE_COUNT_TWO
            mock_factory.assert_any_call(key="service1", application_package=TEST_PACKAGE_NAME)
            mock_factory.assert_any_call(key="service2", application_package=TEST_PACKAGE_NAME)

    def test_build_configs_with_empty_keys(self) -> None:
        """Test build_configs with empty keys list."""
        mock_app = self._create_mock_application()
        builder = AioHttpClientBuilder(keys=[], application=mock_app)

        with patch(
            "fastapi_factory_utilities.core.plugins.aiohttp.builder.build_http_dependency_config"
        ) as mock_factory:
            result = builder.build_configs()

            assert result is builder
            assert not builder._configs  # pylint: disable=protected-access
            mock_factory.assert_not_called()

    def test_build_resources(self) -> None:
        """Test build_resources method creates resources for each config."""
        keys = ["service1", "service2"]
        mock_app = self._create_mock_application()
        builder = AioHttpClientBuilder(keys=keys, application=mock_app)

        # Manually set up configs
        mock_config1 = MagicMock(spec=HttpServiceDependencyConfig)
        mock_config2 = MagicMock(spec=HttpServiceDependencyConfig)
        builder._configs = {"service1": mock_config1, "service2": mock_config2}

        result = builder.build_resources()

        assert result is builder  # Returns self for chaining
        assert "service1" in builder._resources
        assert "service2" in builder._resources
        assert isinstance(builder._resources["service1"], AioHttpClientResource)
        assert isinstance(builder._resources["service2"], AioHttpClientResource)

    def test_build_resources_with_empty_configs(self) -> None:
        """Test build_resources with empty configs."""
        mock_app = self._create_mock_application()
        builder = AioHttpClientBuilder(keys=[], application=mock_app)
        builder._configs = {}

        result = builder.build_resources()

        assert result is builder
        assert not builder._resources  # pylint: disable=protected-access

    def test_resources_property(self) -> None:
        """Test resources property returns the resources dictionary."""
        mock_app = self._create_mock_application()
        builder = AioHttpClientBuilder(keys=[], application=mock_app)
        mock_resource = MagicMock(spec=AioHttpClientResource)
        builder._resources = {"service1": mock_resource}

        result = builder.resources

        assert result == {"service1": mock_resource}

    def test_full_build_flow(self) -> None:
        """Test the complete build flow: build_configs -> build_resources."""
        keys = ["api_service"]
        mock_app = self._create_mock_application()
        builder = AioHttpClientBuilder(keys=keys, application=mock_app)

        mock_config = HttpServiceDependencyConfig(
            limit=50,
            limit_per_host=25,
        )

        with patch(
            "fastapi_factory_utilities.core.plugins.aiohttp.builder.build_http_dependency_config"
        ) as mock_factory:
            mock_factory.return_value = mock_config

            builder.build_configs().build_resources()

            assert "api_service" in builder._configs
            assert "api_service" in builder._resources
            assert isinstance(builder._resources["api_service"], AioHttpClientResource)

    def test_method_chaining(self) -> None:
        """Test that build methods support chaining."""
        keys = ["service"]
        mock_app = self._create_mock_application()
        builder = AioHttpClientBuilder(keys=keys, application=mock_app)

        with patch(
            "fastapi_factory_utilities.core.plugins.aiohttp.builder.build_http_dependency_config"
        ) as mock_factory:
            mock_factory.return_value = HttpServiceDependencyConfig()

            # Test chaining
            result = builder.build_configs().build_resources()

            assert result is builder

    def test_multiple_services(self) -> None:
        """Test building with multiple services."""
        keys = ["service_a", "service_b", "service_c"]
        mock_app = self._create_mock_application()
        builder = AioHttpClientBuilder(keys=keys, application=mock_app)

        configs = {
            "service_a": HttpServiceDependencyConfig(limit=10),
            "service_b": HttpServiceDependencyConfig(limit=20),
            "service_c": HttpServiceDependencyConfig(limit=30),
        }

        with patch(
            "fastapi_factory_utilities.core.plugins.aiohttp.builder.build_http_dependency_config"
        ) as mock_factory:
            mock_factory.side_effect = lambda key, application_package: configs[key]

            builder.build_configs().build_resources()

            assert len(builder._configs) == EXPECTED_SERVICE_COUNT_THREE
            assert len(builder.resources) == EXPECTED_SERVICE_COUNT_THREE

            for key in keys:
                assert key in builder._configs
                assert key in builder.resources
