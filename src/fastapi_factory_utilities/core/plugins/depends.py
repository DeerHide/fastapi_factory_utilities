"""Shared FastAPI depends for named plugin resources on application state."""

from typing import ClassVar, Generic, TypeVar

from fastapi import Request
from fastapi.datastructures import State

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError
from fastapi_factory_utilities.core.plugins.state import StateKey

T = TypeVar("T")


class NamedResourceDepends(Generic[T]):
    """Resolve ``state.<prefix><key>`` for multi-resource plugins (aiohttp, s3)."""

    prefix: ClassVar[StateKey]
    not_found_error: ClassVar[type[FastAPIFactoryUtilitiesError]]
    not_found_message: ClassVar[str]

    def __init__(self, key: str) -> None:
        """Initialize the depends.

        Args:
            key: Logical resource key declared in plugin config.
        """
        self._key: str = key

    @classmethod
    def export_from_state(cls, state: State, key: str) -> T:
        """Export the named resource from application state.

        Args:
            state: FastAPI application state.
            key: Logical resource key.

        Returns:
            The resource stored under ``prefix + key``.

        Raises:
            FastAPIFactoryUtilitiesError: ``not_found_error`` when the key is missing or ``None``.
        """
        resource: T | None = getattr(state, cls.prefix.resource_attr(key), None)
        if resource is None:
            raise cls.not_found_error(cls.not_found_message, key=key)
        return resource

    def __call__(self, request: Request) -> T:
        """Resolve the resource for the given request.

        Args:
            request: The incoming FastAPI request.

        Returns:
            The named resource.
        """
        return self.export_from_state(state=request.app.state, key=self._key)
