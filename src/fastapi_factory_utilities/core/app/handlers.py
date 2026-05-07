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
    errors = cast(RequestValidationError, exc).errors()
    _logger.warning(
        "Validation error",
        method=request.method,
        path=request.url.path,
        errors_count=len(errors),
    )
    return JSONResponse(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, content={"detail": errors})


def register_exception_handlers(app: FastAPI) -> None:
    """Register the exception handlers."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
