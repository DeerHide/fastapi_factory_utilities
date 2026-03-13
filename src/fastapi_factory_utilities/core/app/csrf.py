"""Provides the dependencies for the CSRF protect."""

from typing import ClassVar

from fastapi import Request
from fastapi.datastructures import State
from fastapi_csrf_protect import CsrfProtect


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
