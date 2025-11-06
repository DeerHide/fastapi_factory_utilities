"""Provides the dependencies for the Aiopika plugin."""

from typing import cast

from aio_pika.abc import AbstractRobustConnection
from fastapi import Request

from .exceptions import AiopikaPluginBaseError

DEPENDS_AIOPIKA_ROBUST_CONNECTION_KEY: str = "aiopika_robust_connection"


def depends_aiopika_robust_connection(request: Request) -> AbstractRobustConnection:
    """Get the Aiopika robust connection."""
    robust_connection: AbstractRobustConnection | None = cast(
        AbstractRobustConnection | None, getattr(request.app.state, DEPENDS_AIOPIKA_ROBUST_CONNECTION_KEY, None)
    )
    if robust_connection is None:
        raise AiopikaPluginBaseError("Aiopika robust connection not found in the application state.")
    return robust_connection
