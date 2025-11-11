"""Configuration for MongoDB tests."""

import os
from collections.abc import AsyncGenerator, Callable, Generator
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from beanie import Document
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.mongo_client import AsyncMongoClient
from structlog.stdlib import BoundLogger, get_logger
from testcontainers.mongodb import MongoDbContainer

from fastapi_factory_utilities.core.plugins.odm_plugin import ODMPlugin
from fastapi_factory_utilities.core.plugins.odm_plugin.configs import ODMConfig

_logger: BoundLogger = get_logger(__package__)


@pytest.fixture(scope="session", name="mongodb_server_as_container")
def fixture_mongodb_server_as_container() -> Generator[MongoDbContainer, None, None]:
    """Start the mongodb server."""
    mongodb_container: MongoDbContainer = MongoDbContainer(
        "mongo:latest",
        port=27017,
    )
    if not mongodb_container:
        raise Exception(  # pylint: disable=broad-exception-raised
            "Could not find a random port for the mongodb server."
        )

    mongodb_container.start()
    yield mongodb_container
    mongodb_container.stop(delete_volume=True)


@pytest.fixture(scope="function", name="mongodb_database_name")
def fixture_mongodb_database_name() -> str:
    """Create a MongoDB database name."""
    return f"test_{uuid4()!s}"


@pytest_asyncio.fixture(scope="function", name="async_motor_database")  # pyright: ignore
async def fixture_async_motor_database(
    mongodb_server_as_container: MongoDbContainer,  # pylint: disable=redefined-outer-name
    mongodb_database_name: str,
) -> AsyncGenerator[AsyncDatabase[Any], None]:
    """Create an async motor database."""
    exposed_port: int | None = int(mongodb_server_as_container.get_exposed_port(27017))
    exposed_port = exposed_port if exposed_port else 27017
    username: str = os.environ.get("MONGO_INITDB_ROOT_USERNAME", "test")
    password: str = os.environ.get("MONGO_INITDB_ROOT_PASSWORD", "test")
    mongodb_client: AsyncMongoClient[Any] = AsyncMongoClient(
        host=mongodb_server_as_container.get_container_host_ip(),
        port=exposed_port,
        connect=True,
        username=username,
        password=password,
    )
    mongodb_database: AsyncDatabase[Any] = AsyncDatabase(mongodb_client, mongodb_database_name)

    yield mongodb_database

    await mongodb_client.drop_database(mongodb_database_name)
    await mongodb_client.close()


@pytest.fixture(scope="function", name="odm_plugin_factory")
async def fixture_odm_plugin_factory(
    mongodb_server_as_container: MongoDbContainer, mongodb_database_name: str
) -> Callable[[list[type[Document]]], ODMPlugin]:
    """Create an ODM plugin."""

    def _factory(document_models: list[type[Document]]) -> ODMPlugin:
        exposed_port: int | None = int(mongodb_server_as_container.get_exposed_port(27017))
        exposed_port = exposed_port if exposed_port else 27017
        username: str = os.environ.get("MONGO_INITDB_ROOT_USERNAME", "test")
        password: str = os.environ.get("MONGO_INITDB_ROOT_PASSWORD", "test")
        return ODMPlugin(
            document_models=document_models,
            odm_config=ODMConfig(
                uri=f"mongodb://{username}:{password}"
                f"@{mongodb_server_as_container.get_container_host_ip()}:{exposed_port}"
                f":{exposed_port}/{mongodb_database_name}",
                database=mongodb_database_name,
            ),
        )

    return _factory
