"""Tests for aiohttp plugin exceptions."""

from unittest.mock import Mock, patch

from opentelemetry.trace import INVALID_SPAN

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError
from fastapi_factory_utilities.core.plugins.aiohttp.exceptions import (
    AioHttpClientError,
    AioHttpClientResourceNotFoundError,
    UnableToReadHttpDependencyConfigError,
)


class TestAioHttpClientError:
    """Test cases for AioHttpClientError class."""

    def test_inheritance(self) -> None:
        """Test that AioHttpClientError inherits from FastAPIFactoryUtilitiesError."""
        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = AioHttpClientError("Test error")

                assert isinstance(exception, FastAPIFactoryUtilitiesError)
                assert isinstance(exception, Exception)

    def test_init_with_message(self) -> None:
        """Test exception initialization with message."""
        message = "Custom error message"

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = AioHttpClientError(message)

                assert exception.message == message
                assert str(exception) == message

    def test_can_be_raised_and_caught(self) -> None:
        """Test that AioHttpClientError can be raised and caught."""
        message = "Test error message"

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception_raised = False
                try:
                    raise AioHttpClientError(message)
                except AioHttpClientError as e:
                    exception_raised = True
                    assert str(e) == message

                assert exception_raised, "Exception should be raised and caught"


class TestUnableToReadHttpDependencyConfigError:
    """Test cases for UnableToReadHttpDependencyConfigError class."""

    def test_inheritance(self) -> None:
        """Test that UnableToReadHttpDependencyConfigError inherits from AioHttpClientError."""
        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = UnableToReadHttpDependencyConfigError("Test error")

                assert isinstance(exception, AioHttpClientError)
                assert isinstance(exception, FastAPIFactoryUtilitiesError)

    def test_init_with_message_and_kwargs(self) -> None:
        """Test exception initialization with message and keyword arguments."""
        message = "Unable to read config"
        key_path = "dependencies.http.service1"
        file_path = "application.yaml"

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = UnableToReadHttpDependencyConfigError(message, key_path=key_path, file_path=file_path)

                assert exception.message == message
                assert hasattr(exception, "key_path")
                assert getattr(exception, "key_path") == key_path
                assert hasattr(exception, "file_path")
                assert getattr(exception, "file_path") == file_path

    def test_can_be_caught_by_base_class(self) -> None:
        """Test that exception can be caught by AioHttpClientError."""
        message = "Test error message"

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception_raised = False
                try:
                    raise UnableToReadHttpDependencyConfigError(message)
                except AioHttpClientError as e:
                    exception_raised = True
                    assert isinstance(e, UnableToReadHttpDependencyConfigError)

                assert exception_raised, "Exception should be raised and caught by base class"


class TestAioHttpClientResourceNotFoundError:
    """Test cases for AioHttpClientResourceNotFoundError class."""

    def test_inheritance(self) -> None:
        """Test that AioHttpClientResourceNotFoundError inherits from AioHttpClientError."""
        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = AioHttpClientResourceNotFoundError("Test error")

                assert isinstance(exception, AioHttpClientError)
                assert isinstance(exception, FastAPIFactoryUtilitiesError)

    def test_init_with_message_and_key(self) -> None:
        """Test exception initialization with message and key."""
        message = "Aiohttp resource not found"
        key = "my_service"

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = AioHttpClientResourceNotFoundError(message, key=key)

                assert exception.message == message
                assert hasattr(exception, "key")
                assert getattr(exception, "key") == key

    def test_docstring_used_as_default_message(self) -> None:
        """Test that docstring is used as default message when no message provided."""
        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = AioHttpClientResourceNotFoundError()

                # The docstring first line should be used as the default message
                expected_message = "Exception for the Aiohttp resource not found in the application state."
                assert exception.message == expected_message
