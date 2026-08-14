"""Provide FastAPI / Taskiq dependencies for ODM."""

from typing import Any

from fastapi import Request
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.mongo_client import AsyncMongoClient
from taskiq import TaskiqDepends

from fastapi_factory_utilities.core.plugins.state import ODM_CLIENT, ODM_DATABASE, get_from_state


def depends_odm_client(request: Request = TaskiqDepends()) -> AsyncMongoClient[Any]:
    """Acquire the ODM client from application state.

    Args:
        request: The incoming request (or Taskiq-bridged request).

    Returns:
        The shared async MongoDB client.

    Raises:
        PluginNotRegisteredError: If no ``ODMPlugin`` was registered.
    """
    return get_from_state(request.app.state, ODM_CLIENT)


def depends_odm_database(request: Request = TaskiqDepends()) -> AsyncDatabase[Any]:
    """Acquire the ODM database from application state.

    Args:
        request: The incoming request (or Taskiq-bridged request).

    Returns:
        The shared async MongoDB database.

    Raises:
        PluginNotRegisteredError: If no ``ODMPlugin`` was registered.
    """
    return get_from_state(request.app.state, ODM_DATABASE)
