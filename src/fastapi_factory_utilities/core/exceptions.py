"""FastAPI Factory Utilities exceptions."""

import logging
import traceback
from typing import Any

from opentelemetry.semconv.attributes.error_attributes import ERROR_TYPE
from opentelemetry.semconv.attributes.exception_attributes import (
    EXCEPTION_MESSAGE,
    EXCEPTION_STACKTRACE,
    EXCEPTION_TYPE,
)
from opentelemetry.trace import Span, get_current_span
from structlog.stdlib import BoundLogger, get_logger


class FastAPIFactoryUtilitiesError(Exception):
    """Base exception for the FastAPI Factory Utilities."""

    FILTERED_ATTRIBUTES: tuple[str, ...] = ()
    DEFAULT_LOGGING_LEVEL: int = logging.ERROR
    DEFAULT_MESSAGE: str | None = None

    @classmethod
    def determine_message(
        cls, default_message: str | None, docstring: str | None, kwargs: dict[str, Any], args: tuple[Any, ...]
    ) -> str:
        """Determine the log message for the exception.

        Args:
            default_message: The default message.
            docstring: The docstring.
            kwargs: The keyword arguments.
            args: The arguments.

        Returns:
            str: The log message.
        """
        # If the message is present in the kwargs, return it (keyword argument)
        if "message" in kwargs and kwargs["message"] is not None:
            return kwargs["message"]

        # If the message is present in the args, return it (positional argument)
        if len(args) > 0 and isinstance(args[0], str):
            return args[0]

        # If the default message is not set, try to extract it from the docstring (class docstring)
        if default_message is None and docstring is not None:
            return docstring.split("\n", maxsplit=1)[0]

        # If the default message is not set, return the default message (class attribute)
        return default_message or "An error occurred"

    @classmethod
    def determine_level(cls, default_level: int, kwargs: dict[str, Any]) -> int:
        """Determine the logging level for the exception.

        Args:
            default_level: The default logging level.
            kwargs: The keyword arguments.

        Returns:
            int: The logging level.
        """
        if "level" in kwargs:
            return kwargs["level"]

        return default_level

    @classmethod
    def determine_safe_attributes(cls, kwargs: dict[str, Any], filtered_attributes: tuple[str, ...]) -> dict[str, Any]:
        """Determine the safe attributes for the exception.

        Args:
            kwargs: The keyword arguments.
            filtered_attributes: The filtered attributes.

        Returns:
            dict[str, Any]: The safe attributes.
        """
        # Always filter out "message" and "level" as they are used internally
        internal_filtered = ("message", "level")
        safe_attributes: dict[str, Any] = {}
        for key, value in kwargs.items():
            if key in filtered_attributes or key in internal_filtered:
                continue
            if not isinstance(value, (str, bool, int, float)):
                safe_attributes[key] = str(value)
            else:
                safe_attributes[key] = value
        return safe_attributes

    def __init__(
        self,
        *args: object,
        **kwargs: Any,
    ) -> None:
        """Instantiate the exception.

        Args:
            *args: The arguments.
            **kwargs: The keyword arguments.

        """
        # Get the logger for the child class's module
        logger: BoundLogger = get_logger(self.__class__.__module__)

        # Extract the message and the level from the kwargs if they are present
        self.message: str = self.determine_message(
            default_message=self.DEFAULT_MESSAGE,
            docstring=self.__doc__,
            kwargs=kwargs,
            args=args,
        )
        self.level: int = self.determine_level(
            default_level=self.DEFAULT_LOGGING_LEVEL,
            kwargs=kwargs,
        )

        # Filter the kwargs to remove the filtered attributes
        safe_attributes: dict[str, Any] = self.determine_safe_attributes(
            kwargs=kwargs,
            filtered_attributes=self.FILTERED_ATTRIBUTES,
        )

        # Set the kwargs as attributes of the exception
        for key, value in safe_attributes.items():
            setattr(self, key, value)

        # Log the Exception using the logger for the child class's module
        if self.message:
            logger.log(level=self.level, event=self.message, **safe_attributes)

        try:
            # Propagate the exception
            span: Span = get_current_span()
            # If not otel is setup, INVALID_SPAN is retrieved from get_current_span
            # and it will respond False to the is_recording method
            if span.is_recording():
                # Set the kwargs attributes
                for key, value in safe_attributes.items():
                    span.set_attribute(key, value)

                # Record official Attributes last to avoid overriding them
                span.record_exception(self)
                # Set the exception and error attributes
                span.set_attribute(ERROR_TYPE, self.__class__.__name__)
                span.set_attribute(EXCEPTION_MESSAGE, self.message)
                span.set_attribute(EXCEPTION_STACKTRACE, traceback.format_exc())
                span.set_attribute(EXCEPTION_TYPE, self.__class__.__name__)
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Suppress any errors that occur while propagating the exception
            logger.error("An error occurred while recording the exception as trace", exc_info=e)

        # Call the parent class with the message so str(exception) returns it
        super().__init__(self.message)
