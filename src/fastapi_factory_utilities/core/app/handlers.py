"""Provides the application handlers."""

from http import HTTPStatus
from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from structlog.stdlib import BoundLogger, get_logger

_logger: BoundLogger = get_logger(__package__)


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Validation exception handler."""
    exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
    content = {"status_code": 422, "message": exc_str, "data": None}
    errors = cast(RequestValidationError, exc).errors()
    _logger.error("Validation error", request=request, exc_str=exc_str, content=content)
    return JSONResponse(status_code=HTTPStatus.BAD_REQUEST, content={"detail": errors})


def register_exception_handlers(app: FastAPI) -> None:
    """Register the exception handlers."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
