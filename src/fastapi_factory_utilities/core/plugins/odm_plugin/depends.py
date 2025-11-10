"""Provide FastAPI dependency for ODM."""

from typing import Any

from fastapi import Request
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.mongo_client import AsyncMongoClient


def depends_odm_client(request: Request) -> AsyncMongoClient[Any]:
    """Acquire the ODM client from the request.

    Args:
        request (Request): The request.

    Returns:
        AsyncIOMotorClient: The ODM client.
    """
    return request.app.state.odm_client


def depends_odm_database(request: Request) -> AsyncDatabase[Any]:
    """Acquire the ODM database from the request.

    Args:
        request (Request): The request.

    Returns:
        AsyncIOMotorClient: The ODM database.
    """
    return request.app.state.odm_database
