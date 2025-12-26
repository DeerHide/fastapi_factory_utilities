"""Tests for aiohttp plugin factories."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fastapi_factory_utilities.core.plugins.aiohttp.configs import HttpServiceDependencyConfig
from fastapi_factory_utilities.core.plugins.aiohttp.exceptions import UnableToReadHttpDependencyConfigError
from fastapi_factory_utilities.core.plugins.aiohttp.factories import (
    BASE_YAML_PATH,
    DEFAULT_YAML_BASE_KEY,
    build_http_dependency_config,
)
from fastapi_factory_utilities.core.utils.yaml_reader import UnableToReadYamlFileError

# Test constants
DEFAULT_LIMIT: int = 10
DEFAULT_LIMIT_PER_HOST: int = 10
CUSTOM_LIMIT: int = 20
CUSTOM_LIMIT_PER_HOST: int = 10


class TestFactoryConstants:
    """Test cases for factory constants."""

    def test_base_yaml_path(self) -> None:
        """Test BASE_YAML_PATH constant value."""
        assert BASE_YAML_PATH == Path("application.yaml")

    def test_default_yaml_base_key(self) -> None:
        """Test DEFAULT_YAML_BASE_KEY constant value."""
        assert DEFAULT_YAML_BASE_KEY == "dependencies.http"


class TestBuildHttpDependencyConfig:
    """Test cases for build_http_dependency_config function."""

    def test_successful_config_build(self) -> None:
        """Test successful HTTP dependency config build."""
        key = "test_service"
        mock_yaml_data = {
            "url": "https://api.example.com",
            "limit": CUSTOM_LIMIT,
            "limit_per_host": CUSTOM_LIMIT_PER_HOST,
        }

        with patch("fastapi_factory_utilities.core.plugins.aiohttp.factories.YamlFileReader") as mock_yaml_reader:
            mock_reader_instance = MagicMock()
            mock_reader_instance.read.return_value = mock_yaml_data
            mock_yaml_reader.return_value = mock_reader_instance

            config = build_http_dependency_config(key=key)

            assert isinstance(config, HttpServiceDependencyConfig)
            assert str(config.url) == "https://api.example.com/"
            assert config.limit == CUSTOM_LIMIT
            assert config.limit_per_host == CUSTOM_LIMIT_PER_HOST

            # Verify YamlFileReader was called with correct parameters
            expected_key_path = f"{DEFAULT_YAML_BASE_KEY}.{key}"
            mock_yaml_reader.assert_called_once_with(file_path=BASE_YAML_PATH, yaml_base_key=expected_key_path)

    def test_with_default_values(self) -> None:
        """Test config build with empty YAML data (uses defaults)."""
        key = "test_service"
        mock_yaml_data: dict[str, object] = {}

        with patch("fastapi_factory_utilities.core.plugins.aiohttp.factories.YamlFileReader") as mock_yaml_reader:
            mock_reader_instance = MagicMock()
            mock_reader_instance.read.return_value = mock_yaml_data
            mock_yaml_reader.return_value = mock_reader_instance

            config = build_http_dependency_config(key=key)

            assert isinstance(config, HttpServiceDependencyConfig)
            assert config.url is None
            assert config.limit == DEFAULT_LIMIT  # Default value
            assert config.limit_per_host == DEFAULT_LIMIT_PER_HOST  # Default value

    def test_file_not_found_error(self) -> None:
        """Test that FileNotFoundError is wrapped in UnableToReadHttpDependencyConfigError."""
        key = "test_service"

        with patch("fastapi_factory_utilities.core.plugins.aiohttp.factories.YamlFileReader") as mock_yaml_reader:
            mock_yaml_reader.side_effect = FileNotFoundError("File not found")

            with patch("fastapi_factory_utilities.core.exceptions._logger"):
                with patch("fastapi_factory_utilities.core.exceptions.get_current_span", MagicMock()):
                    with pytest.raises(UnableToReadHttpDependencyConfigError) as exc_info:
                        build_http_dependency_config(key=key)

                    assert exc_info.value.__cause__ is not None
                    assert isinstance(exc_info.value.__cause__, FileNotFoundError)

    def test_import_error(self) -> None:
        """Test that ImportError is wrapped in UnableToReadHttpDependencyConfigError."""
        key = "test_service"

        with patch("fastapi_factory_utilities.core.plugins.aiohttp.factories.YamlFileReader") as mock_yaml_reader:
            mock_yaml_reader.side_effect = ImportError("Import failed")

            with patch("fastapi_factory_utilities.core.exceptions._logger"):
                with patch("fastapi_factory_utilities.core.exceptions.get_current_span", MagicMock()):
                    with pytest.raises(UnableToReadHttpDependencyConfigError) as exc_info:
                        build_http_dependency_config(key=key)

                    assert exc_info.value.__cause__ is not None
                    assert isinstance(exc_info.value.__cause__, ImportError)

    def test_unable_to_read_yaml_file_error(self) -> None:
        """Test that UnableToReadYamlFileError is wrapped in UnableToReadHttpDependencyConfigError."""
        key = "test_service"

        with patch("fastapi_factory_utilities.core.plugins.aiohttp.factories.YamlFileReader") as mock_yaml_reader:
            mock_yaml_reader.side_effect = UnableToReadYamlFileError(file_path=Path("test.yaml"), message="YAML error")

            with patch("fastapi_factory_utilities.core.exceptions._logger"):
                with patch("fastapi_factory_utilities.core.exceptions.get_current_span", MagicMock()):
                    with pytest.raises(UnableToReadHttpDependencyConfigError) as exc_info:
                        build_http_dependency_config(key=key)

                    assert exc_info.value.__cause__ is not None
                    assert isinstance(exc_info.value.__cause__, UnableToReadYamlFileError)

    def test_value_error_on_read(self) -> None:
        """Test that ValueError from read() is wrapped in UnableToReadHttpDependencyConfigError."""
        key = "test_service"

        with patch("fastapi_factory_utilities.core.plugins.aiohttp.factories.YamlFileReader") as mock_yaml_reader:
            mock_reader_instance = MagicMock()
            mock_reader_instance.read.side_effect = ValueError("Invalid YAML")
            mock_yaml_reader.return_value = mock_reader_instance

            with patch("fastapi_factory_utilities.core.exceptions._logger"):
                with patch("fastapi_factory_utilities.core.exceptions.get_current_span", MagicMock()):
                    with pytest.raises(UnableToReadHttpDependencyConfigError) as exc_info:
                        build_http_dependency_config(key=key)

                    assert exc_info.value.__cause__ is not None
                    assert isinstance(exc_info.value.__cause__, ValueError)

    def test_key_path_formatting(self) -> None:
        """Test that key path is correctly formatted."""
        key = "my.nested.service"

        with patch("fastapi_factory_utilities.core.plugins.aiohttp.factories.YamlFileReader") as mock_yaml_reader:
            mock_reader_instance = MagicMock()
            mock_reader_instance.read.return_value = {}
            mock_yaml_reader.return_value = mock_reader_instance

            build_http_dependency_config(key=key)

            expected_key_path = f"{DEFAULT_YAML_BASE_KEY}.{key}"
            mock_yaml_reader.assert_called_once_with(file_path=BASE_YAML_PATH, yaml_base_key=expected_key_path)

    @pytest.mark.parametrize(
        "key",
        [
            "service1",
            "my_service",
            "external-api",
            "nested.service.name",
        ],
    )
    def test_various_key_formats(self, key: str) -> None:
        """Test various key format configurations."""
        with patch("fastapi_factory_utilities.core.plugins.aiohttp.factories.YamlFileReader") as mock_yaml_reader:
            mock_reader_instance = MagicMock()
            mock_reader_instance.read.return_value = {}
            mock_yaml_reader.return_value = mock_reader_instance

            config = build_http_dependency_config(key=key)

            assert isinstance(config, HttpServiceDependencyConfig)
