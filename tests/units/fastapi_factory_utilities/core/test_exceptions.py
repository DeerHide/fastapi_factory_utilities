"""Tests for FastAPI Factory Utilities exceptions."""

import logging
from unittest.mock import Mock, patch

from opentelemetry.trace import INVALID_SPAN

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError


class BaseExceptionForTestError(FastAPIFactoryUtilitiesError):
    """Base test exception."""


class ExceptionForTestError(BaseExceptionForTestError):
    """Test exception."""


class TestFastAPIFactoryUtilitiesError:
    """Test cases for FastAPIFactoryUtilitiesError class."""

    def test_init_with_message_kwarg(self) -> None:
        """Test exception initialization with message as keyword argument."""
        message = "Test error message"
        level = logging.WARNING

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = FastAPIFactoryUtilitiesError(message=message, level=level)

                assert exception.message == message
                assert exception.level == level
                mock_logger.log.assert_called_once_with(level=level, event=message)

    def test_init_with_message_in_args(self) -> None:
        """Test exception initialization with message as first positional argument."""
        message = "Test error message"

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = FastAPIFactoryUtilitiesError(message)

                assert exception.message == message
                assert exception.level == logging.ERROR  # Default level
                mock_logger.log.assert_called_once_with(level=logging.ERROR, event=message)

    def test_init_with_default_level(self) -> None:
        """Test exception initialization with default logging level."""
        message = "Test error message"

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = FastAPIFactoryUtilitiesError(message=message)

                assert exception.level == logging.ERROR
                mock_logger.log.assert_called_once_with(level=logging.ERROR, event=message)

    def test_init_without_message(self) -> None:
        """Test exception initialization without message."""
        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = FastAPIFactoryUtilitiesError()

                # When DEFAULT_MESSAGE is None, the message is extracted from the docstring
                expected_message = "Base exception for the FastAPI Factory Utilities."
                assert exception.message == expected_message
                assert exception.level == FastAPIFactoryUtilitiesError.DEFAULT_LOGGING_LEVEL
                mock_logger.log.assert_called_once_with(
                    level=FastAPIFactoryUtilitiesError.DEFAULT_LOGGING_LEVEL,
                    event=expected_message,
                )

    def test_init_with_non_string_first_arg(self) -> None:
        """Test exception initialization with non-string first positional argument."""
        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = FastAPIFactoryUtilitiesError(123, "additional arg")

                # When DEFAULT_MESSAGE is None, the message is extracted from the docstring
                expected_message = "Base exception for the FastAPI Factory Utilities."
                assert exception.message == expected_message
                assert exception.level == FastAPIFactoryUtilitiesError.DEFAULT_LOGGING_LEVEL
                mock_logger.log.assert_called_once_with(
                    level=FastAPIFactoryUtilitiesError.DEFAULT_LOGGING_LEVEL,
                    event=expected_message,
                )

    def test_init_with_empty_args(self) -> None:
        """Test exception initialization with empty positional arguments."""
        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = FastAPIFactoryUtilitiesError()

                # When DEFAULT_MESSAGE is None, the message is extracted from the docstring
                expected_message = "Base exception for the FastAPI Factory Utilities."
                assert exception.message == expected_message
                assert exception.level == FastAPIFactoryUtilitiesError.DEFAULT_LOGGING_LEVEL
                mock_logger.log.assert_called_once_with(
                    level=FastAPIFactoryUtilitiesError.DEFAULT_LOGGING_LEVEL,
                    event=expected_message,
                )

    def test_otel_span_recording_with_valid_span(self) -> None:
        """Test OpenTelemetry span recording when span is recording."""
        message = "Test error message"
        custom_attr = "custom_value"

        mock_span = Mock()
        mock_span.is_recording.return_value = True

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_get_span:
                mock_get_span.return_value = mock_span

                exception = FastAPIFactoryUtilitiesError(
                    message=message,
                    custom_attr=custom_attr,  # type: ignore[call-arg]
                )

                mock_span.record_exception.assert_called_once_with(exception)
                # Custom attribute should be set
                mock_span.set_attribute.assert_any_call("custom_attr", custom_attr)
                # OTEL semantic attributes should also be set
                mock_span.set_attribute.assert_any_call("error.type", "FastAPIFactoryUtilitiesError")
                mock_span.set_attribute.assert_any_call("exception.message", message)
                mock_span.set_attribute.assert_any_call("exception.type", "FastAPIFactoryUtilitiesError")
                # 1 custom attr + 4 OTEL attributes
                # (error.type, exception.message, exception.stacktrace, exception.type)
                assert mock_span.set_attribute.call_count == 5  # noqa: PLR2004

    def test_otel_span_recording_with_invalid_span(self) -> None:
        """Test OpenTelemetry span recording when span is not recording."""
        message = "Test error message"

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_get_span:
                mock_get_span.return_value = INVALID_SPAN

                FastAPIFactoryUtilitiesError(message=message)  # pylint: disable=pointless-exception-statement

                # Should not raise any errors and should not call span methods

    def test_otel_span_attribute_conversion(self) -> None:
        """Test OpenTelemetry span attribute value conversion for different types."""
        message = "Test error message"
        mock_span = Mock()
        mock_span.is_recording.return_value = True

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_get_span:
                mock_get_span.return_value = mock_span

                # Test with various attribute types
                FastAPIFactoryUtilitiesError(  # pylint: disable=pointless-exception-statement
                    message=message,
                    **{  # type: ignore[arg-type]
                        "str_attr": "string_value",
                        "int_attr": 42,
                        "float_attr": 3.14,
                        "bool_attr": True,
                        "list_attr": [1, 2, 3],
                        "tuple_attr": (1, 2, 3),
                        "complex_attr": complex(1, 2),  # Should be converted to string
                    },
                )

                # Check that all custom attributes were set
                expected_custom_calls = [
                    ("str_attr", "string_value"),
                    ("int_attr", 42),
                    ("float_attr", 3.14),
                    ("bool_attr", True),
                    ("list_attr", str([1, 2, 3])),
                    ("tuple_attr", str((1, 2, 3))),
                    ("complex_attr", "(1+2j)"),  # Complex converted to string
                ]

                for expected_call in expected_custom_calls:
                    mock_span.set_attribute.assert_any_call(*expected_call)

                # OTEL semantic attributes should also be set (4 additional: error.type, exception.message,
                # exception.stacktrace, exception.type)
                mock_span.set_attribute.assert_any_call("error.type", "FastAPIFactoryUtilitiesError")
                mock_span.set_attribute.assert_any_call("exception.message", message)
                mock_span.set_attribute.assert_any_call("exception.type", "FastAPIFactoryUtilitiesError")
                # Total: 7 custom attrs + 4 OTEL attrs = 11
                assert mock_span.set_attribute.call_count == len(expected_custom_calls) + 4

    def test_inheritance_from_exception(self) -> None:
        """Test that FastAPIFactoryUtilitiesError properly inherits from Exception."""
        message = "Test error message"

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = FastAPIFactoryUtilitiesError(message=message)

                assert isinstance(exception, Exception)
                assert str(exception) == message

    def test_exception_with_multiple_args(self) -> None:
        """Test exception initialization with multiple positional arguments."""
        message = "Test error message"
        arg1 = "additional_arg1"
        arg2 = "additional_arg2"

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = FastAPIFactoryUtilitiesError(message, arg1, arg2)

                assert exception.message == message
                mock_logger.log.assert_called_once_with(level=logging.ERROR, event=message)
                # Check that all args are preserved in the exception
                assert str(exception) == message

    def test_exception_with_kwargs_preserved_in_span(self) -> None:
        """Test that kwargs are preserved and set as span attributes."""
        message = "Test error message"
        mock_span = Mock()
        mock_span.is_recording.return_value = True

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_get_span:
                mock_get_span.return_value = mock_span

                FastAPIFactoryUtilitiesError(  # pylint: disable=pointless-exception-statement
                    message=message,
                    **{"user_id": 123, "request_id": "req-456", "error_code": "E001"},  # type: ignore[arg-type]
                )

                # Verify span attributes were set
                expected_attributes = [("user_id", 123), ("request_id", "req-456"), ("error_code", "E001")]

                for attr_name, attr_value in expected_attributes:
                    mock_span.set_attribute.assert_any_call(attr_name, attr_value)

    def test_filtered_attributes_not_set_as_instance_attributes(self) -> None:
        """Test that FILTERED_ATTRIBUTES are not set as instance attributes."""
        message = "Test error message"
        filtered_attr = "filtered_value"
        normal_attr = "normal_value"

        class FilteredError(FastAPIFactoryUtilitiesError):
            """Error with filtered attributes."""

            FILTERED_ATTRIBUTES = ("filtered_attr",)

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = FilteredError(
                    message=message,
                    filtered_attr=filtered_attr,  # type: ignore[call-arg]
                    normal_attr=normal_attr,  # type: ignore[call-arg]
                )

                # Filtered attribute should not be set
                assert not hasattr(exception, "filtered_attr")
                # Normal attribute should be set
                assert hasattr(exception, "normal_attr")
                assert getattr(exception, "normal_attr") == normal_attr

    def test_kwargs_set_as_instance_attributes(self) -> None:
        """Test that kwargs are set as instance attributes."""
        message = "Test error message"
        user_id = 123
        request_id = "req-456"

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = FastAPIFactoryUtilitiesError(
                    message=message,
                    user_id=user_id,  # type: ignore[call-arg]
                    request_id=request_id,  # type: ignore[call-arg]
                )

                assert hasattr(exception, "user_id")
                assert getattr(exception, "user_id") == user_id
                assert hasattr(exception, "request_id")
                assert getattr(exception, "request_id") == request_id

    def test_default_message_when_set(self) -> None:
        """Test that DEFAULT_MESSAGE is used when set."""
        custom_message = "Custom default message"

        class CustomDefaultError(FastAPIFactoryUtilitiesError):
            """Error with custom default message."""

            DEFAULT_MESSAGE = custom_message

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = CustomDefaultError()

                assert exception.message == custom_message
                mock_logger.log.assert_called_once_with(
                    level=FastAPIFactoryUtilitiesError.DEFAULT_LOGGING_LEVEL,
                    event=custom_message,
                )

    def test_default_message_overridden_by_kwarg(self) -> None:
        """Test that DEFAULT_MESSAGE is overridden by message kwarg."""
        custom_message = "Custom default message"
        override_message = "Override message"

        class CustomDefaultError(FastAPIFactoryUtilitiesError):
            """Error with custom default message."""

            DEFAULT_MESSAGE = custom_message

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = CustomDefaultError(message=override_message)

                assert exception.message == override_message
                mock_logger.log.assert_called_once_with(
                    level=FastAPIFactoryUtilitiesError.DEFAULT_LOGGING_LEVEL,
                    event=override_message,
                )

    def test_default_message_overridden_by_arg(self) -> None:
        """Test that DEFAULT_MESSAGE is overridden by positional arg."""
        custom_message = "Custom default message"
        override_message = "Override message"

        class CustomDefaultError(FastAPIFactoryUtilitiesError):
            """Error with custom default message."""

            DEFAULT_MESSAGE = custom_message

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = CustomDefaultError(override_message)

                assert exception.message == override_message
                mock_logger.log.assert_called_once_with(
                    level=FastAPIFactoryUtilitiesError.DEFAULT_LOGGING_LEVEL,
                    event=override_message,
                )

    def test_otel_span_exception_handling(self) -> None:
        """Test that exceptions in OpenTelemetry span handling are suppressed."""
        message = "Test error message"

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_get_span:
                # Simulate get_current_span raising an exception
                mock_get_span.side_effect = Exception("OpenTelemetry error")

                # Should not raise, should handle gracefully
                exception = FastAPIFactoryUtilitiesError(message=message)

                assert exception.message == message

    def test_str_with_none_message(self) -> None:
        """Test __str__ method when message is None."""
        # Create an exception with message explicitly set to None
        # This is an edge case that shouldn't normally happen, but we test it
        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = FastAPIFactoryUtilitiesError("test_arg")
                # Manually set message to None to test edge case
                exception.message = None  # type: ignore[assignment]

                # Should fall back to parent's __str__
                str_repr = str(exception)
                assert str_repr is not None
                # When message is None, it should use parent's __str__ which uses args
                assert "test_arg" in str_repr

    def test_filtered_attributes_not_in_span(self) -> None:
        """Test that FILTERED_ATTRIBUTES are not added to span attributes."""
        message = "Test error message"
        filtered_attr = "filtered_value"
        normal_attr = "normal_value"

        class FilteredError(FastAPIFactoryUtilitiesError):
            """Error with filtered attributes."""

            FILTERED_ATTRIBUTES = ("filtered_attr",)

        mock_span = Mock()
        mock_span.is_recording.return_value = True

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_get_span:
                mock_get_span.return_value = mock_span

                FilteredError(  # pylint: disable=pointless-exception-statement
                    message=message,
                    filtered_attr=filtered_attr,  # type: ignore[call-arg]
                    normal_attr=normal_attr,  # type: ignore[call-arg]
                )

                # Filtered attribute should not be in span
                mock_span.set_attribute.assert_any_call("normal_attr", normal_attr)
                # Verify filtered_attr was never called
                calls = [call[0][0] for call in mock_span.set_attribute.call_args_list]
                assert "filtered_attr" not in calls


class TestExceptionForTestError:
    """Test cases for ExceptionForTestError class."""

    def test_init_with_message_kwarg(self) -> None:
        """Test exception initialization with message as keyword argument."""
        message = "Custom test error message"
        level = logging.WARNING

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = ExceptionForTestError(message=message, level=level)

                assert exception.message == message
                assert exception.level == level
                mock_logger.log.assert_called_once_with(level=level, event=message)

    def test_init_with_message_in_args(self) -> None:
        """Test exception initialization with message as first positional argument."""
        message = "Custom test error message"

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = ExceptionForTestError(message)

                assert exception.message == message
                assert exception.level == logging.ERROR  # Default level
                mock_logger.log.assert_called_once_with(level=logging.ERROR, event=message)

    def test_init_without_message(self) -> None:
        """Test exception initialization without message uses docstring."""
        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = ExceptionForTestError()

                # When DEFAULT_MESSAGE is None, the message is extracted from the docstring
                expected_message = "Test exception."
                assert exception.message == expected_message
                assert exception.level == FastAPIFactoryUtilitiesError.DEFAULT_LOGGING_LEVEL
                mock_logger.log.assert_called_once_with(
                    level=FastAPIFactoryUtilitiesError.DEFAULT_LOGGING_LEVEL,
                    event=expected_message,
                )

    def test_inheritance_chain(self) -> None:
        """Test that TestErrorForTestError properly inherits from base classes."""
        message = "Test error message"

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = ExceptionForTestError(message=message)

                assert isinstance(exception, Exception)
                assert isinstance(exception, FastAPIFactoryUtilitiesError)
                assert isinstance(exception, BaseExceptionForTestError)
                assert not isinstance(exception, TestExceptionForTestError)
                assert str(exception) == message

    def test_exception_can_be_raised_and_caught(self) -> None:
        """Test that ExceptionForTestError can be raised and caught."""
        message = "Test error message"

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception_raised = False
                try:
                    raise ExceptionForTestError(message=message)
                except ExceptionForTestError as e:
                    exception_raised = True
                    assert str(e) == message
                    assert e.message == message

                assert exception_raised, "Exception should be raised and caught"

    def test_exception_can_be_caught_by_base_class(self) -> None:
        """Test that ExceptionForTestError can be caught by base exception classes."""
        message = "Test error message"

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception_raised = False
                try:
                    raise ExceptionForTestError(message=message)
                except BaseExceptionForTestError as e:
                    exception_raised = True
                    assert str(e) == message
                    assert isinstance(e, ExceptionForTestError)

                assert exception_raised, "Exception should be raised and caught by base class"

    def test_otel_span_recording_with_valid_span(self) -> None:
        """Test OpenTelemetry span recording when span is recording."""
        message = "Test error message"
        custom_attr = "custom_value"

        mock_span = Mock()
        mock_span.is_recording.return_value = True

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_get_span:
                mock_get_span.return_value = mock_span

                exception = ExceptionForTestError(
                    message=message,
                    custom_attr=custom_attr,  # type: ignore[call-arg]
                )

                mock_span.record_exception.assert_called_once_with(exception)
                # Custom attribute should be set
                mock_span.set_attribute.assert_any_call("custom_attr", custom_attr)
                # OTEL semantic attributes should also be set
                mock_span.set_attribute.assert_any_call("error.type", "ExceptionForTestError")
                mock_span.set_attribute.assert_any_call("exception.message", message)
                mock_span.set_attribute.assert_any_call("exception.type", "ExceptionForTestError")
                # 1 custom attr + 4 OTEL attributes
                # (error.type, exception.message, exception.stacktrace, exception.type)
                assert mock_span.set_attribute.call_count == 5  # noqa: PLR2004

    def test_otel_span_recording_with_invalid_span(self) -> None:
        """Test OpenTelemetry span recording when span is not recording."""
        message = "Test error message"

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_get_span:
                mock_get_span.return_value = INVALID_SPAN

                ExceptionForTestError(message=message)  # pylint: disable=pointless-exception-statement

                # Should not raise any errors and should not call span methods

    def test_exception_with_kwargs_preserved_in_span(self) -> None:
        """Test that kwargs are preserved and set as span attributes."""
        message = "Test error message"
        mock_span = Mock()
        mock_span.is_recording.return_value = True

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_get_span:
                mock_get_span.return_value = mock_span

                ExceptionForTestError(  # pylint: disable=pointless-exception-statement
                    message=message,
                    **{"user_id": 123, "request_id": "req-456", "error_code": "E001"},  # type: ignore[arg-type]
                )

                # Verify span attributes were set
                expected_attributes = [("user_id", 123), ("request_id", "req-456"), ("error_code", "E001")]

                for attr_name, attr_value in expected_attributes:
                    mock_span.set_attribute.assert_any_call(attr_name, attr_value)
