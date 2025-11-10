"""Configuration for MongoDB tests."""

import os
from collections.abc import AsyncGenerator, Generator
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.mongo_client import AsyncMongoClient
from structlog.stdlib import BoundLogger, get_logger
from testcontainers.mongodb import MongoDbContainer

_logger: BoundLogger = get_logger(__package__)


@pytest.fixture(scope="session", name="mongodb_server_as_container")
def mongodb_server_as_container() -> Generator[MongoDbContainer, None, None]:
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


@pytest_asyncio.fixture(scope="function", name="async_motor_database")  # pyright: ignore
async def mongodb_async_database_from_container(
    mongodb_server_as_container: MongoDbContainer,  # pylint: disable=redefined-outer-name
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
    database_name: UUID = uuid4()
    mongodb_database: AsyncDatabase[Any] = AsyncDatabase(mongodb_client, str(database_name))

    yield mongodb_database

    await mongodb_client.drop_database(str(database_name))
    await mongodb_client.close()
