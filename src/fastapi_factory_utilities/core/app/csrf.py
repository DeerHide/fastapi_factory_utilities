"""Provides the dependencies for the CSRF protect."""

from http import HTTPStatus
from typing import ClassVar

from fastapi import FastAPI, Request
from fastapi.datastructures import State
from fastapi.responses import JSONResponse
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from structlog.stdlib import BoundLogger, get_logger

_logger: BoundLogger = get_logger(__package__)


class DependsCsrfProtect:
    """Dependency for the CSRF protect."""

    STATE_KEY: ClassVar[str] = "csrf_protect"

    @classmethod
    def import_to_state(cls, state: State, csrf_protect: CsrfProtect) -> None:
        """Import the CSRF protect to the state."""
        state[cls.STATE_KEY] = csrf_protect

    @classmethod
    def export_from_state(cls, state: State) -> CsrfProtect:
        """Export the CSRF protect from the state."""
        return state[cls.STATE_KEY]

    def __call__(self, request: Request) -> CsrfProtect:
        """Call the dependency."""
        return self.export_from_state(state=request.app.state)


depends_csrf_protect: DependsCsrfProtect = DependsCsrfProtect()


async def csrf_protect_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """CSRF exception handler."""
    _logger.warning("CSRF error", request=request, exc=exc)
    return JSONResponse(status_code=HTTPStatus.FORBIDDEN, content={"detail": "CSRF token is invalid"})


def register_exception_handler(app: FastAPI) -> None:
    """Register the CSRF exception handler."""
    app.add_exception_handler(CsrfProtectError, csrf_protect_exception_handler)
