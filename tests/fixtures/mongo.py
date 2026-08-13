"""Configuration for MongoDB tests."""

import os
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from beanie import Document
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.mongo_client import AsyncMongoClient
from pymongo.encryption_options import AutoEncryptionOpts
from structlog.stdlib import BoundLogger, get_logger
from testcontainers.mongodb import MongoDbContainer

from fastapi_factory_utilities.core.plugins.odm_plugin import ODMPlugin
from fastapi_factory_utilities.core.plugins.odm_plugin.configs import ODMConfig
from fastapi_factory_utilities.core.plugins.odm_plugin.encryption import (
    build_schema_map,
    resolve_or_create_data_key,
)

_logger: BoundLogger = get_logger(__package__)

CSFLE_KEY_VAULT_COLLECTION = "__keyVault"


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


@pytest.fixture(scope="session", name="mongodb_enterprise_server_as_container")
def fixture_mongodb_enterprise_server_as_container() -> Generator[MongoDbContainer, None, None]:
    """Start the MongoDB Enterprise server image, required for CSFLE automatic encryption."""
    mongodb_container: MongoDbContainer = MongoDbContainer(
        "mongodb/mongodb-enterprise-server:8.0-ubi9-slim",
        port=27017,
    )
    mongodb_container.start()
    yield mongodb_container
    mongodb_container.stop(delete_volume=True)


@pytest.fixture(scope="function", name="csfle_fake_local_key")
def fixture_csfle_fake_local_key() -> bytes:
    """A fake 96-byte local KMS master key, for tests only. Never used against real data."""
    return os.urandom(96)


@pytest_asyncio.fixture(scope="function", name="encrypting_odm_factory")  # pyright: ignore
async def fixture_encrypting_odm_factory(
    mongodb_enterprise_server_as_container: MongoDbContainer,  # pylint: disable=redefined-outer-name
    mongodb_database_name: str,
    csfle_fake_local_key: bytes,  # pylint: disable=redefined-outer-name
) -> AsyncGenerator[
    Callable[[list[type[Document]]], Awaitable[tuple[AsyncMongoClient[Any], AsyncDatabase[Any], AsyncDatabase[Any]]]],
    None,
]:
    """Build a CSFLE-encrypting client/database pair, plus a plain (non-encrypting) database handle.

    Uses a fake local KMS key (never Vault) but the library's own key-vault provisioning and
    schema-map builder, so those production code paths are exercised end to end. Requires
    `mongocryptd` on PATH; callers should skip when it is unavailable.
    """
    exposed_port: int = int(mongodb_enterprise_server_as_container.get_exposed_port(27017))
    host: str = mongodb_enterprise_server_as_container.get_container_host_ip()
    username: str = os.environ.get("MONGO_INITDB_ROOT_USERNAME", "test")
    password: str = os.environ.get("MONGO_INITDB_ROOT_PASSWORD", "test")
    uri: str = f"mongodb://{username}:{password}@{host}:{exposed_port}"
    kms_providers: dict[str, Any] = {"local": {"key": csfle_fake_local_key}}

    plain_client: AsyncMongoClient[Any] = AsyncMongoClient(uri, connect=True)
    encrypting_client: AsyncMongoClient[Any] | None = None

    async def _factory(
        document_models: list[type[Document]],
    ) -> tuple[AsyncMongoClient[Any], AsyncDatabase[Any], AsyncDatabase[Any]]:
        nonlocal encrypting_client
        key_id = await resolve_or_create_data_key(
            client=plain_client,
            key_vault_database=mongodb_database_name,
            key_vault_collection=CSFLE_KEY_VAULT_COLLECTION,
            kms_providers=kms_providers,
        )
        schema_map = build_schema_map(document_models, database_name=mongodb_database_name, key_id=key_id)
        auto_encryption_opts: AutoEncryptionOpts = AutoEncryptionOpts(
            kms_providers=kms_providers,
            key_vault_namespace=f"{mongodb_database_name}.{CSFLE_KEY_VAULT_COLLECTION}",
            schema_map=schema_map,
        )
        encrypting_client = AsyncMongoClient(uri, connect=True, auto_encryption_opts=auto_encryption_opts)
        return (
            encrypting_client,
            AsyncDatabase(encrypting_client, mongodb_database_name),
            AsyncDatabase(plain_client, mongodb_database_name),
        )

    yield _factory

    await plain_client.drop_database(mongodb_database_name)
    await plain_client.close()
    if encrypting_client is not None:
        await encrypting_client.close()
