"""Pytest fixtures for infra test doubles (loaded via the pytest11 plugin only)."""

from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import pytest_asyncio
from beanie import init_beanie
from fastapi import FastAPI
from pymongo.asynchronous.database import AsyncDatabase
from redis.asyncio import Redis

from fastapi_factory_utilities.core.plugins.odm_plugin.repositories import AbstractRepository
from fastapi_factory_utilities.core.plugins.redis_plugin.constants import STATE_REDIS_CLIENT_KEY
from fastapi_factory_utilities.core.plugins.s3_plugin.constants import (
    STATE_BUCKET_PREFIX_KEY,
    STATE_S3_CLIENT_KEY,
)
from fastapi_factory_utilities.core.plugins.s3_plugin.resources import S3BucketResource
from fastapi_factory_utilities.core.plugins.taskiq_plugins.depends import DEPENDS_SCHEDULER_COMPONENT_KEY
from fastapi_factory_utilities.core.plugins.taskiq_plugins.schedulers import SchedulerComponent
from fastapi_factory_utilities.core.testing.contracts.models import ContractDocument, ContractRepository
from fastapi_factory_utilities.core.testing.odm import build_mongomock_database
from fastapi_factory_utilities.core.testing.otel import InMemoryOtel, build_in_memory_otel
from fastapi_factory_utilities.core.testing.redis import build_fakeredis
from fastapi_factory_utilities.core.testing.s3 import build_s3_bucket_resource, moto_s3_client
from fastapi_factory_utilities.core.testing.taskiq import build_in_memory_scheduler_component

__all__ = [
    "fixture_app_with_fakeredis",
    "fixture_app_with_in_memory_otel",
    "fixture_app_with_in_memory_taskiq",
    "fixture_app_with_moto_s3",
    "fixture_contract_repository_mongomock",
    "fixture_fakeredis_client",
    "fixture_in_memory_otel",
    "fixture_in_memory_scheduler_component",
    "fixture_mongomock_database",
    "fixture_mongomock_odm_database",
    "fixture_moto_s3_bucket",
]


@pytest_asyncio.fixture(name="mongomock_database")
async def fixture_mongomock_database() -> AsyncGenerator[AsyncDatabase[Any], None]:
    """Yield a fresh mongomock-backed database for one test."""
    database = build_mongomock_database()
    yield database
    await database.client.aclose()


@pytest_asyncio.fixture(name="mongomock_odm_database")
async def fixture_mongomock_odm_database(
    mongomock_database: AsyncDatabase[Any],
) -> AsyncGenerator[AsyncDatabase[Any], None]:
    """Yield a mongomock database with :class:`ContractDocument` initialized via Beanie."""
    await init_beanie(database=mongomock_database, document_models=[ContractDocument])
    yield mongomock_database


@pytest_asyncio.fixture(name="contract_repository_mongomock")
async def fixture_contract_repository_mongomock(
    mongomock_odm_database: AsyncDatabase[Any],
) -> AbstractRepository[Any, Any]:
    """:class:`ContractRepository` backed by mongomock (for contract tests)."""
    return ContractRepository(database=mongomock_odm_database)


@pytest_asyncio.fixture(name="fakeredis_client")
async def fixture_fakeredis_client() -> AsyncGenerator[Redis, None]:
    """Yield a fresh fakeredis client and close it after the test."""
    client = build_fakeredis()
    yield client
    await client.aclose()


@pytest_asyncio.fixture(name="app_with_fakeredis")
async def fixture_app_with_fakeredis(
    fakeredis_client: Redis,
) -> AsyncGenerator[Any, None]:
    """Yield a minimal FastAPI app with ``redis_client`` on state for Depends."""
    app = FastAPI()
    setattr(app.state, STATE_REDIS_CLIENT_KEY, fakeredis_client)
    yield app


@pytest_asyncio.fixture(name="moto_s3_bucket")
async def fixture_moto_s3_bucket() -> AsyncGenerator[S3BucketResource, None]:
    """Yield an :class:`S3BucketResource` backed by moto."""
    async with moto_s3_client() as (client, endpoint_url, names):
        yield build_s3_bucket_resource(
            client,
            key="default",
            bucket_name=names[0],
            endpoint_url=endpoint_url,
        )


@pytest_asyncio.fixture(name="app_with_moto_s3")
async def fixture_app_with_moto_s3() -> AsyncGenerator[Any, None]:
    """Yield a FastAPI app with moto S3 client + default bucket on state."""
    async with moto_s3_client() as (client, endpoint_url, names):
        app = FastAPI()
        bucket = build_s3_bucket_resource(
            client,
            key="default",
            bucket_name=names[0],
            endpoint_url=endpoint_url,
        )
        setattr(app.state, STATE_S3_CLIENT_KEY, client)
        setattr(app.state, f"{STATE_BUCKET_PREFIX_KEY}default", bucket)
        yield app


@pytest.fixture(name="in_memory_scheduler_component")
def fixture_in_memory_scheduler_component() -> SchedulerComponent:
    """Yield a :class:`SchedulerComponent` backed by ``InMemoryBroker``."""
    return build_in_memory_scheduler_component()


@pytest.fixture(name="app_with_in_memory_taskiq")
def fixture_app_with_in_memory_taskiq() -> Any:
    """Yield a FastAPI app with in-memory ``scheduler_component`` on state."""
    app = FastAPI()
    build_in_memory_scheduler_component(app=app)
    assert getattr(app.state, DEPENDS_SCHEDULER_COMPONENT_KEY) is not None
    return app


@pytest.fixture(name="in_memory_otel")
def fixture_in_memory_otel() -> Generator[InMemoryOtel, None, None]:
    """Yield in-memory OTel providers; shut them down after the test."""
    otel = build_in_memory_otel()
    yield otel
    otel.tracer_provider.shutdown()
    otel.meter_provider.shutdown()


@pytest.fixture(name="app_with_in_memory_otel")
def fixture_app_with_in_memory_otel(in_memory_otel: InMemoryOtel) -> Any:
    """Yield a FastAPI app with tracer/meter providers on state for Depends."""
    app = FastAPI()
    app.state.tracer_provider = in_memory_otel.tracer_provider
    app.state.meter_provider = in_memory_otel.meter_provider
    return app
