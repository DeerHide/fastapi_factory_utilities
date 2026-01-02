"""Tests for FastAPI Factory Utilities exceptions."""

import logging
from typing import Any
from unittest.mock import Mock, patch

from opentelemetry.trace import INVALID_SPAN

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError


class BaseExceptionForTestError(FastAPIFactoryUtilitiesError):
    """Base test exception."""


class ExceptionForTestError(BaseExceptionForTestError):
    """Test exception."""


class TestDetermineMessage:
    """Test cases for the determine_message class method."""

    def test_message_from_kwargs(self) -> None:
        """Test that message is extracted from kwargs when present."""
        kwargs: dict[str, Any] = {"message": "From kwargs"}
        args: tuple[Any, ...] = ()

        result = FastAPIFactoryUtilitiesError.determine_message(
            default_message=None,
            docstring="From docstring.",
            kwargs=kwargs,
            args=args,
        )

        assert result == "From kwargs"

    def test_message_from_args(self) -> None:
        """Test that message is extracted from args when not in kwargs."""
        kwargs: dict[str, Any] = {}
        args: tuple[Any, ...] = ("From args",)

        result = FastAPIFactoryUtilitiesError.determine_message(
            default_message=None,
            docstring="From docstring.",
            kwargs=kwargs,
            args=args,
        )

        assert result == "From args"

    def test_message_kwargs_takes_precedence_over_args(self) -> None:
        """Test that kwargs message takes precedence over args."""
        kwargs: dict[str, Any] = {"message": "From kwargs"}
        args: tuple[Any, ...] = ("From args",)

        result = FastAPIFactoryUtilitiesError.determine_message(
            default_message=None,
            docstring="From docstring.",
            kwargs=kwargs,
            args=args,
        )

        assert result == "From kwargs"

    def test_message_from_docstring(self) -> None:
        """Test that message is extracted from docstring when not in kwargs or args."""
        kwargs: dict[str, Any] = {}
        args: tuple[Any, ...] = ()

        result = FastAPIFactoryUtilitiesError.determine_message(
            default_message=None,
            docstring="From docstring.\nSecond line.",
            kwargs=kwargs,
            args=args,
        )

        assert result == "From docstring."

    def test_message_from_default_message(self) -> None:
        """Test that default_message is used when docstring is None."""
        kwargs: dict[str, Any] = {}
        args: tuple[Any, ...] = ()

        result = FastAPIFactoryUtilitiesError.determine_message(
            default_message="Default message",
            docstring=None,
            kwargs=kwargs,
            args=args,
        )

        assert result == "Default message"

    def test_fallback_to_generic_message(self) -> None:
        """Test fallback to generic message when nothing else is available."""
        kwargs: dict[str, Any] = {}
        args: tuple[Any, ...] = ()

        result = FastAPIFactoryUtilitiesError.determine_message(
            default_message=None,
            docstring=None,
            kwargs=kwargs,
            args=args,
        )

        assert result == "An error occurred"

    def test_non_string_first_arg_ignored(self) -> None:
        """Test that non-string first arg is ignored."""
        kwargs: dict[str, Any] = {}
        args: tuple[Any, ...] = (123, "string arg")

        result = FastAPIFactoryUtilitiesError.determine_message(
            default_message=None,
            docstring="From docstring.",
            kwargs=kwargs,
            args=args,
        )

        assert result == "From docstring."

    def test_none_message_in_kwargs_ignored(self) -> None:
        """Test that None message in kwargs is ignored."""
        kwargs: dict[str, Any] = {"message": None}
        args: tuple[Any, ...] = ("From args",)

        result = FastAPIFactoryUtilitiesError.determine_message(
            default_message=None,
            docstring="From docstring.",
            kwargs=kwargs,
            args=args,
        )

        assert result == "From args"


class TestDetermineLevel:
    """Test cases for the determine_level class method."""

    def test_level_from_kwargs(self) -> None:
        """Test that level is extracted from kwargs when present."""
        kwargs: dict[str, Any] = {"level": logging.WARNING}

        result = FastAPIFactoryUtilitiesError.determine_level(
            default_level=logging.ERROR,
            kwargs=kwargs,
        )

        assert result == logging.WARNING

    def test_fallback_to_default_level(self) -> None:
        """Test that default_level is used when not in kwargs."""
        kwargs: dict[str, Any] = {}

        result = FastAPIFactoryUtilitiesError.determine_level(
            default_level=logging.ERROR,
            kwargs=kwargs,
        )

        assert result == logging.ERROR

    def test_level_debug(self) -> None:
        """Test that DEBUG level can be set."""
        kwargs: dict[str, Any] = {"level": logging.DEBUG}

        result = FastAPIFactoryUtilitiesError.determine_level(
            default_level=logging.ERROR,
            kwargs=kwargs,
        )

        assert result == logging.DEBUG

    def test_level_critical(self) -> None:
        """Test that CRITICAL level can be set."""
        kwargs: dict[str, Any] = {"level": logging.CRITICAL}

        result = FastAPIFactoryUtilitiesError.determine_level(
            default_level=logging.ERROR,
            kwargs=kwargs,
        )

        assert result == logging.CRITICAL


class TestDetermineSafeAttributes:
    """Test cases for the determine_safe_attributes class method."""

    def test_filters_filtered_attributes(self) -> None:
        """Test that FILTERED_ATTRIBUTES are removed."""
        kwargs: dict[str, Any] = {
            "filtered_attr": "should be removed",
            "normal_attr": "should remain",
        }
        filtered_attributes = ("filtered_attr",)

        result = FastAPIFactoryUtilitiesError.determine_safe_attributes(
            kwargs=kwargs,
            filtered_attributes=filtered_attributes,
        )

        assert "filtered_attr" not in result
        assert result["normal_attr"] == "should remain"

    def test_filters_message_and_level_internally(self) -> None:
        """Test that message and level are always filtered out internally."""
        kwargs: dict[str, Any] = {
            "message": "should be removed",
            "level": logging.ERROR,
            "normal_attr": "should remain",
        }

        result = FastAPIFactoryUtilitiesError.determine_safe_attributes(
            kwargs=kwargs,
            filtered_attributes=(),
        )

        assert "message" not in result
        assert "level" not in result
        assert result["normal_attr"] == "should remain"

    def test_preserves_primitive_types(self) -> None:
        """Test that primitive types are preserved as-is."""
        kwargs: dict[str, Any] = {
            "str_attr": "string_value",
            "int_attr": 42,
            "float_attr": 3.14,
            "bool_attr": True,
        }

        result = FastAPIFactoryUtilitiesError.determine_safe_attributes(
            kwargs=kwargs,
            filtered_attributes=(),
        )

        assert result["str_attr"] == "string_value"
        assert result["int_attr"] == 42  # noqa: PLR2004
        assert result["float_attr"] == 3.14  # noqa: PLR2004
        assert result["bool_attr"] is True

    def test_converts_non_primitive_types_to_string(self) -> None:
        """Test that non-primitive types are converted to strings."""
        kwargs: dict[str, Any] = {
            "list_attr": [1, 2, 3],
            "tuple_attr": (1, 2, 3),
            "dict_attr": {"key": "value"},
            "complex_attr": complex(1, 2),
        }

        result = FastAPIFactoryUtilitiesError.determine_safe_attributes(
            kwargs=kwargs,
            filtered_attributes=(),
        )

        assert result["list_attr"] == "[1, 2, 3]"
        assert result["tuple_attr"] == "(1, 2, 3)"
        assert result["dict_attr"] == "{'key': 'value'}"
        assert result["complex_attr"] == "(1+2j)"

    def test_empty_kwargs(self) -> None:
        """Test handling of empty kwargs."""
        kwargs: dict[str, Any] = {}

        result = FastAPIFactoryUtilitiesError.determine_safe_attributes(
            kwargs=kwargs,
            filtered_attributes=(),
        )

        assert not result

    def test_all_filtered(self) -> None:
        """Test when all attributes are filtered."""
        kwargs: dict[str, Any] = {
            "attr1": "value1",
            "attr2": "value2",
        }
        filtered_attributes = ("attr1", "attr2")

        result = FastAPIFactoryUtilitiesError.determine_safe_attributes(
            kwargs=kwargs,
            filtered_attributes=filtered_attributes,
        )

        assert not result


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
                # message and level are filtered out from safe_attributes
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

                # Verify logger was called with custom_attr
                mock_logger.log.assert_called_once_with(
                    level=logging.ERROR,
                    event=message,
                    custom_attr=custom_attr,
                )

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

                # Check that all custom attributes were set (after type conversion)
                expected_custom_calls = [
                    ("str_attr", "string_value"),
                    ("int_attr", 42),
                    ("float_attr", 3.14),
                    ("bool_attr", True),
                    ("list_attr", "[1, 2, 3]"),
                    ("tuple_attr", "(1, 2, 3)"),
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

                # When message is passed as arg, str() returns the message
                exception = FastAPIFactoryUtilitiesError(message)

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
                # Only the message is passed to super().__init__() for str() consistency
                assert exception.args == (message,)
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
                expected_attributes = [
                    ("user_id", 123),
                    ("request_id", "req-456"),
                    ("error_code", "E001"),
                ]

                for attr_name, attr_value in expected_attributes:
                    mock_span.set_attribute.assert_any_call(attr_name, attr_value)

                # Verify logger was called with kwargs (message is filtered out)
                mock_logger.log.assert_called_once_with(
                    level=logging.ERROR,
                    event=message,
                    user_id=123,
                    request_id="req-456",
                    error_code="E001",
                )

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

                # Verify logger was called without filtered_attr
                mock_logger.log.assert_called_once_with(
                    level=logging.ERROR,
                    event=message,
                    normal_attr=normal_attr,
                )

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

                # Verify logger was called with kwargs
                mock_logger.log.assert_called_once_with(
                    level=logging.ERROR,
                    event=message,
                    user_id=user_id,
                    request_id=request_id,
                )

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
        """Test that exceptions in OpenTelemetry span handling are logged."""
        message = "Test error message"

        mock_logger = Mock()
        mock_logger.log = Mock()
        mock_logger.error = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_get_span:
                # Simulate get_current_span raising an exception
                mock_get_span.side_effect = Exception("OpenTelemetry error")

                # Should not raise, should handle gracefully
                exception = FastAPIFactoryUtilitiesError(message=message)

                assert exception.message == message
                # Verify error was logged
                mock_logger.error.assert_called_once()
                # Verify the error message
                call_args = mock_logger.error.call_args
                assert "An error occurred while recording the exception as trace" in call_args[0][0]

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
                # message is also filtered internally
                assert "message" not in calls

    def test_str_uses_exception_args(self) -> None:
        """Test that __str__ uses Exception's default behavior with args."""
        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                # When message is passed as positional arg, str() returns the message
                exception = FastAPIFactoryUtilitiesError("test_arg")

                # __str__ should use args from Exception base class
                str_repr = str(exception)
                assert str_repr is not None
                assert "test_arg" in str_repr

    def test_str_with_message_kwarg_returns_message(self) -> None:
        """Test that __str__ returns message regardless of how it was passed."""
        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                # When message is passed as kwarg, str() still returns the message
                exception = FastAPIFactoryUtilitiesError(message="test message")

                # __str__ returns the message
                str_repr = str(exception)
                assert str_repr == "test message"

    def test_message_and_level_not_set_as_instance_attributes(self) -> None:
        """Test that message and level kwargs are not set as additional instance attributes."""
        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN

                exception = FastAPIFactoryUtilitiesError(
                    message="test",
                    level=logging.WARNING,
                    custom_attr="custom",  # type: ignore[call-arg]
                )

                # message and level should only exist as the primary attributes
                assert exception.message == "test"
                assert exception.level == logging.WARNING
                # custom_attr should be set
                assert hasattr(exception, "custom_attr")
                assert getattr(exception, "custom_attr") == "custom"


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

                # Use positional arg so str() returns the message
                exception = ExceptionForTestError(message)

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
                    # Use positional arg so str() returns the message
                    raise ExceptionForTestError(message)
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
                    # Use positional arg so str() returns the message
                    raise ExceptionForTestError(message)
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

                # Verify logger was called with custom_attr
                mock_logger.log.assert_called_once_with(
                    level=logging.ERROR,
                    event=message,
                    custom_attr=custom_attr,
                )

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
                expected_attributes = [
                    ("user_id", 123),
                    ("request_id", "req-456"),
                    ("error_code", "E001"),
                ]

                for attr_name, attr_value in expected_attributes:
                    mock_span.set_attribute.assert_any_call(attr_name, attr_value)

                # Verify logger was called with kwargs
                mock_logger.log.assert_called_once_with(
                    level=logging.ERROR,
                    event=message,
                    user_id=123,
                    request_id="req-456",
                    error_code="E001",
                )
