"""Provides a function to setup the logging configuration."""

import logging
import sys
from enum import StrEnum, auto
from typing import Annotated, Any

import structlog
from pydantic import BaseModel, BeforeValidator
from structlog.types import EventDict

_logger = structlog.getLogger(__package__)


def ensure_logging_level(level: Any) -> int:
    """Ensure the logging level.

    Args:
        level (Any): The logging level.

    Returns:
        int: The logging level.
    """
    if isinstance(level, int):
        return level

    if isinstance(level, str):
        try:
            return getattr(logging, str(level).upper())
        except AttributeError as exception:
            raise ValueError(f"Invalid logging level: {level}") from exception

    raise ValueError(f"Invalid logging level: {level}")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    name: str
    level: Annotated[int, BeforeValidator(ensure_logging_level)]


class LogModeEnum(StrEnum):
    """Defines the possible logging modes."""

    CONSOLE = auto()
    JSON = auto()


# https://github.com/hynek/structlog/issues/35#issuecomment-591321744
def _rename_event_key(_: Any, __: Any, event_dict: EventDict) -> EventDict:  # pylint: disable=invalid-name
    """Renames the `event` key to `message` in the event dictionary.

    Log entries keep the text message in the `event` field, but Datadog
    uses the `message` field. This processor moves the value from one field to
    the other.
    See https://github.com/hynek/structlog/issues/35#issuecomment-591321744
    """
    event_dict["message"] = event_dict.pop("event")
    return event_dict


def clean_uvicorn_logger() -> None:
    """Cleans the uvicorn loggers."""
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        # Clear the log handlers for uvicorn loggers, and enable propagation
        # so the messages are caught by our root logger and formatted correctly
        # by structlog
        logging.getLogger(logger_name).handlers.clear()
        logging.getLogger(logger_name).propagate = True


def clean_hypercorn_logger() -> None:
    """Cleans the Hypercorn loggers."""
    for logger_name in ["hypercorn.error", "hypercorn.access"]:
        logging.getLogger(logger_name).handlers.clear()
        logging.getLogger(logger_name).propagate = True


def _drop_color_message_key(_: Any, __: Any, event_dict: EventDict) -> EventDict:  # pylint: disable=invalid-name
    """Cleans the `color_message` key from the event dictionary.

    Uvicorn logs the message a second time in the extra `color_message`, but we don't
    need it. This processor drops the key from the event dict if it exists.
    """
    event_dict.pop("color_message", None)
    return event_dict


def setup_log(
    mode: LogModeEnum = LogModeEnum.CONSOLE, log_level: str = "DEBUG", logging_config: list[LoggingConfig] | None = None
) -> None:
    """Prepares the logging configuration.

    Args:
        mode (LogMode): The logging mode to use.
        log_level (str): The log level to use.
        logging_config (List[LoggingConfig], optional): The logging configuration. Defaults to None.

    Returns:
        None
    """
    processors: list[structlog.typing.Processor] = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.stdlib.ExtraAdder(),
        structlog.processors.CallsiteParameterAdder(
            parameters={
                structlog.processors.CallsiteParameter.MODULE: True,
                structlog.processors.CallsiteParameter.FUNC_NAME: True,
                structlog.processors.CallsiteParameter.LINENO: True,
            }
        ),
        _drop_color_message_key,
    ]

    log_renderer: structlog.dev.ConsoleRenderer | structlog.processors.JSONRenderer
    match mode:
        case LogModeEnum.CONSOLE:
            log_renderer = structlog.dev.ConsoleRenderer(
                exception_formatter=structlog.dev.RichTracebackFormatter(),
            )
        case LogModeEnum.JSON:
            # We rename the `event` key to `message` only in JSON logs,
            # as Datadog looks for the
            # `message` key but the pretty ConsoleRenderer looks for `event`
            processors.append(_rename_event_key)
            # Format the exception only for JSON logs, as we want
            # to pretty-print them when
            # using the ConsoleRenderer
            processors.append(
                structlog.processors.dict_tracebacks,
            )
            log_renderer = structlog.processors.JSONRenderer()

    # Remove all existing loggers
    structlog.reset_defaults()
    structlog_processors: list[structlog.typing.Processor] = processors.copy()
    structlog_processors.append(structlog.stdlib.ProcessorFormatter.wrap_for_formatter)
    structlog.configure(
        processors=structlog_processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        # These run ONLY on `logging` entries that do NOT originate within
        # structlog.
        foreign_pre_chain=processors,
        # These run on ALL entries after the pre_chain is done.
        processors=[
            # Remove _record & _from_structlog.
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            log_renderer,
        ],
    )

    handler = logging.StreamHandler()
    # Use OUR `ProcessorFormatter` to format all `logging` entries.
    handler.setFormatter(formatter)
    root_logger: logging.Logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())

    for logging_config_item in logging_config or []:
        logger = logging.getLogger(logging_config_item.name)
        logger.setLevel(logging_config_item.level)

    def handle_exception(exc_type: Any, exc_value: Any, exc_traceback: Any) -> None:
        """Handle uncaught exceptions.

        Log any uncaught exception instead of letting it be printed by Python
        (but leave KeyboardInterrupt untouched to allow users to Ctrl+C to stop)
        See https://stackoverflow.com/a/16993115/3641865
        """
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        _logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception
