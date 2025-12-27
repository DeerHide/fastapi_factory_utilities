"""FastAPI Factory Utilities exceptions."""

import logging
import traceback
from typing import Any, cast

from opentelemetry.semconv.attributes.error_attributes import ERROR_TYPE
from opentelemetry.semconv.attributes.exception_attributes import (
    EXCEPTION_MESSAGE,
    EXCEPTION_STACKTRACE,
    EXCEPTION_TYPE,
)
from opentelemetry.trace import Span, get_current_span
from opentelemetry.util.types import AttributeValue
from structlog.stdlib import BoundLogger, get_logger

_logger: BoundLogger = get_logger()


class FastAPIFactoryUtilitiesError(Exception):
    """Base exception for the FastAPI Factory Utilities."""

    FILTERED_ATTRIBUTES: tuple[str, ...] = ()
    DEFAULT_LOGGING_LEVEL: int = logging.ERROR
    DEFAULT_MESSAGE: str | None = None

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
        # If Default Message is not set, try to extract it from docstring (first line)
        default_message: str = self.DEFAULT_MESSAGE or "An error occurred"
        if self.DEFAULT_MESSAGE is None and self.__doc__ is not None:
            default_message = self.__doc__.split("\n", maxsplit=1)[0]
        # Extract the message and the level from the kwargs if they are present
        self.message: str | None = cast(str | None, kwargs.pop("message", None))
        self.level: int = cast(int, kwargs.pop("level", self.DEFAULT_LOGGING_LEVEL))

        # If the message is not present, try to extract it from the args
        if self.message is None and len(args) > 0 and isinstance(args[0], str):
            self.message = args[0]
        elif self.message is None:
            self.message = default_message

        # Log the Exception
        if self.message:
            _logger.log(level=self.level, event=self.message)

        # Set the kwargs as attributes of the exception
        for key, value in kwargs.items():
            if key in self.FILTERED_ATTRIBUTES:
                continue
            setattr(self, key, value)

        try:
            # Propagate the exception
            span: Span = get_current_span()
            # If not otel is setup, INVALID_SPAN is retrieved from get_current_span
            # and it will respond False to the is_recording method
            if span.is_recording():
                # Set the kwargs attributes
                for key, value in kwargs.items():
                    if key in self.FILTERED_ATTRIBUTES:
                        continue
                    attribute_value: AttributeValue
                    if not isinstance(value, (str, bool, int, float)):
                        attribute_value = str(value)
                    else:
                        attribute_value = value
                    span.set_attribute(key, attribute_value)

                # Record official Attributes last to avoid overriding them
                span.record_exception(self)
                # Set the exception and error attributes
                span.set_attribute(ERROR_TYPE, self.__class__.__name__)
                span.set_attribute(EXCEPTION_MESSAGE, self.message)
                span.set_attribute(EXCEPTION_STACKTRACE, traceback.format_exc())
                span.set_attribute(EXCEPTION_TYPE, self.__class__.__name__)
        except Exception:  # pylint: disable=broad-exception-caught
            # Suppress any errors that occur while propagating the exception
            pass

        # Call the parent class
        super().__init__(*args)

    def __str__(self) -> str:
        """Return the string representation of the exception.

        Returns:
            str: The message if available, otherwise the default exception string.
        """
        if self.message is not None:
            return self.message
        return super().__str__()
