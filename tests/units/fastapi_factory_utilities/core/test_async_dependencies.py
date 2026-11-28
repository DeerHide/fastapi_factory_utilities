"""Guard: request-scoped state-lookup dependencies must be ``async def``.

FastAPI runs every sync ``def`` dependency in the AnyIO threadpool. For a
dependency that only reads ``request.app.state`` that hop costs far more than the
work: it needs a threadpool slot and a GIL handoff back to the event loop, which
under CPU load waits for the interpreter switch interval (5 ms) on every hop.
"""

import inspect
from collections.abc import Callable
from typing import Any

import pytest

from fastapi_factory_utilities.core.app.csrf import DependsCsrfProtect
from fastapi_factory_utilities.core.app.depends import (
    DependsApplicationConfig,
    DependsRootConfig,
    depends_csrf_config,
)
from fastapi_factory_utilities.core.plugins.aiohttp_plugin.depends import AioHttpResourceDepends
from fastapi_factory_utilities.core.plugins.aiopika_plugin.depends import depends_aiopika_robust_connection
from fastapi_factory_utilities.core.plugins.depends import NamedResourceDepends
from fastapi_factory_utilities.core.plugins.odm_plugin.depends import depends_odm_client, depends_odm_database
from fastapi_factory_utilities.core.plugins.opentelemetry_plugin.depends import (
    depends_meter_provider,
    depends_otel_config,
    depends_tracer_provider,
)
from fastapi_factory_utilities.core.plugins.redis_plugin.depends import depends_redis, depends_redis_plugin
from fastapi_factory_utilities.core.plugins.s3_plugin.depends import S3BucketDepends, depends_s3_client
from fastapi_factory_utilities.core.plugins.taskiq_plugin.depends import depends_scheduler_component
from fastapi_factory_utilities.core.security.jwt.configs import DependsJWTBearerAuthenticationConfig
from fastapi_factory_utilities.core.security.jwt.stores import DependsHydraJWKStoreMemory
from fastapi_factory_utilities.core.services.status.services import depends_status_service
from fastapi_factory_utilities.core.utils.query_helper import QueryFilterHelper

FUNCTION_DEPENDENCIES: list[Callable[..., Any]] = [
    depends_aiopika_robust_connection,
    depends_csrf_config,
    depends_meter_provider,
    depends_odm_client,
    depends_odm_database,
    depends_otel_config,
    depends_redis,
    depends_redis_plugin,
    depends_s3_client,
    depends_scheduler_component,
    depends_status_service,
    depends_tracer_provider,
]

CLASS_DEPENDENCIES: list[type[Any]] = [
    AioHttpResourceDepends,
    DependsApplicationConfig,
    DependsCsrfProtect,
    DependsHydraJWKStoreMemory,
    DependsJWTBearerAuthenticationConfig,
    DependsRootConfig,
    NamedResourceDepends,
    QueryFilterHelper,
    S3BucketDepends,
]


@pytest.mark.parametrize("dependency", FUNCTION_DEPENDENCIES, ids=lambda d: d.__name__)
def test_function_dependency_is_async(dependency: Callable[..., Any]) -> None:
    """State-lookup dependency functions run on the event loop, not the threadpool."""
    assert inspect.iscoroutinefunction(dependency)


@pytest.mark.parametrize("dependency_class", CLASS_DEPENDENCIES, ids=lambda c: c.__name__)
def test_class_dependency_call_is_async(dependency_class: type[Any]) -> None:
    """State-lookup dependency classes expose an ``async def __call__``."""
    assert inspect.iscoroutinefunction(dependency_class.__call__)
