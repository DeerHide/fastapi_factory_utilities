"""Test for fastapi_factory_utilities.core.utils.configs."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from fastapi_factory_utilities.core.utils.configs import (
    UnableToReadConfigFileError,
    ValueErrorConfigError,
    build_config_from_file_in_package,
)
from fastapi_factory_utilities.core.utils.yaml_reader import UnableToReadYamlFileError


class TestBuildConfigFromFileInPackage:
    """Provides test cases for the build_config_from_file_in_package function."""

    @contextmanager
    def mock_method(
        self,
        mock_value_file_path: str,
        mock_value_file_content: dict[str, Any],
        base_key: str = "base_key",
        side_effects: type[Exception] | None = None,
    ) -> Iterator[tuple[MagicMock, MagicMock, MagicMock]]:
        """Mock the methods used in the build_config_from_file_in_package function.

        Args:
            mock_value_file_path (str): The file path.
            mock_value_file_content (dict[str, Any]): The file content.
            base_key (str): The base key in the yaml file.
            side_effects (type[Exception] | None): The side effects for the read method.

        Yields:
            tuple[MagicMock, MagicMock, MagicMock]: The mocks for the methods. (
                mock_get_path_file_in_package,
                mock_yamlfilereader_constructor,
                mock_yaml_file_reader_object)

        """
        # mock get_path_file_in_package
        with patch(
            "fastapi_factory_utilities.core.utils.configs.get_path_file_in_package"
        ) as mock_get_path_file_in_package:
            mock_get_path_file_in_package.return_value = mock_value_file_path

            with patch(
                "fastapi_factory_utilities.core.utils.configs.YamlFileReader"
            ) as mock_yamlfilereader_constructor:
                # mock YamlFileReader Class behavior
                mock_yaml_file_reader_object = MagicMock()
                if side_effects is not None:
                    mock_yaml_file_reader_object.read.side_effect = side_effects
                else:
                    mock_yaml_file_reader_object.read.return_value = mock_value_file_content[base_key]
                mock_yamlfilereader_constructor.return_value = mock_yaml_file_reader_object

                yield (
                    mock_get_path_file_in_package,
                    mock_yamlfilereader_constructor,
                    mock_yaml_file_reader_object,
                )

    def test_build_config_from_file_in_package(self) -> None:
        """Test the case where the configuration file is read successfully."""

        class TestConfigModel(BaseModel):
            """Test configuration model."""

            key: str

        mock_value_file_path: str = "file_path"
        mock_value_package_name: str = "package_name"
        mock_value_file_content: dict[str, Any] = {
            "base_key": {
                "key": "value",
            }
        }

        with self.mock_method(
            mock_value_file_path=mock_value_file_path,
            mock_value_file_content=mock_value_file_content,
            base_key="base_key",
        ) as (_, _, _):
            # Test
            config: TestConfigModel = build_config_from_file_in_package(
                package_name=mock_value_package_name,
                filename=mock_value_file_path,
                config_class=TestConfigModel,
                yaml_base_key="base_key",
            )

            assert isinstance(config, TestConfigModel)
            for key, value in mock_value_file_content["base_key"].items():
                assert getattr(config, key) == value

    @pytest.mark.parametrize(
        "side_effects,expected_raise",
        [
            [UnableToReadYamlFileError, UnableToReadConfigFileError],
            [FileNotFoundError, UnableToReadConfigFileError],
            [ImportError, UnableToReadConfigFileError],
        ],
    )
    def test_build_config_from_file_in_package_with_exception(
        self, side_effects: type[Exception], expected_raise: type[Exception]
    ) -> None:
        """Test the case where an exception is raised."""
        mock_value_file_path: str = "file_path"
        mock_value_package_name: str = "package_name"
        mock_value_file_content: dict[str, str] = {
            "key": "value",
        }

        with self.mock_method(
            mock_value_file_path=mock_value_file_path,
            mock_value_file_content=mock_value_file_content,
            side_effects=side_effects,
        ) as (_, _, _):
            # Test

            with pytest.raises(expected_exception=expected_raise):
                build_config_from_file_in_package(
                    package_name=mock_value_package_name,
                    filename=mock_value_file_path,
                    config_class=BaseModel,
                    yaml_base_key="base_key",
                )

    def test_build_config_from_file_in_package_with_invalid_config(self) -> None:
        """Test the case where the configuration file is invalid."""

        class TestConfigModel(BaseModel):
            key: str

        mock_value_file_path: str = "file_path"
        mock_value_package_name: str = "package_name"
        mock_value_file_content: dict[str, Any] = {
            "base_key": {
                "key": 1,
            }
        }

        with self.mock_method(
            mock_value_file_path=mock_value_file_path,
            mock_value_file_content=mock_value_file_content,
            base_key="base_key",
        ) as (_, _, _):
            # Test

            with pytest.raises(expected_exception=ValueErrorConfigError, match="key:") as exc_info:
                build_config_from_file_in_package(
                    package_name=mock_value_package_name,
                    filename=mock_value_file_path,
                    config_class=TestConfigModel,
                    yaml_base_key="base_key",
                )

            assert "Invalid configuration values" in str(exc_info.value)
