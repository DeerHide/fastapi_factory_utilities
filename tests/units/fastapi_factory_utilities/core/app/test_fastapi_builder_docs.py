"""Unit tests for OpenAPI / docs exposure via FastAPIBuilder."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_factory_utilities.core.app.config import (
    BaseApplicationConfig,
    DocsConfig,
    RootConfig,
)
from fastapi_factory_utilities.core.app.enums import EnvironmentEnum
from fastapi_factory_utilities.core.app.fastapi_builder import FastAPIBuilder


def _root_config(
    *,
    environment: EnvironmentEnum,
    docs: DocsConfig | None = None,
) -> RootConfig:
    """Build a minimal RootConfig for docs exposure tests.

    When ``docs`` is omitted, RootConfig's ``docs`` default_factory runs so
    ``docs.enabled`` stays ``None`` (environment-driven).
    """
    application = BaseApplicationConfig(
        service_namespace="test",
        environment=environment,
        service_name="docs-test",
        description="docs exposure tests",
        version="0.0.0",
    )
    if docs is None:
        return RootConfig(application=application)
    return RootConfig(application=application, docs=docs)


@asynccontextmanager
async def _noop_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield


class TestFastAPIBuilderDocsExposure:
    """Docs / OpenAPI are opt-in outside development by default."""

    def test_production_defaults_disable_docs_and_openapi(self) -> None:
        """Production apps must not expose /docs, /redoc, or /openapi.json."""
        root_config = _root_config(environment=EnvironmentEnum.PRODUCTION)
        assert root_config.docs.enabled is None
        app = FastAPIBuilder(root_config=root_config).build(lifespan=_noop_lifespan)
        with TestClient(app) as client:
            assert client.get("/docs").status_code == HTTPStatus.NOT_FOUND
            assert client.get("/redoc").status_code == HTTPStatus.NOT_FOUND
            assert client.get("/openapi.json").status_code == HTTPStatus.NOT_FOUND

    def test_development_defaults_enable_docs(self) -> None:
        """Development still gets interactive docs when docs.enabled is unset."""
        root_config = _root_config(environment=EnvironmentEnum.DEVELOPMENT)
        assert root_config.docs.enabled is None
        app = FastAPIBuilder(root_config=root_config).build(lifespan=_noop_lifespan)
        with TestClient(app) as client:
            assert client.get("/docs").status_code == HTTPStatus.OK
            assert client.get("/openapi.json").status_code == HTTPStatus.OK

    def test_explicit_enabled_overrides_production(self) -> None:
        """docs.enabled=True force-enables docs in production."""
        app = FastAPIBuilder(
            root_config=_root_config(
                environment=EnvironmentEnum.PRODUCTION,
                docs=DocsConfig(enabled=True),
            )
        ).build(lifespan=_noop_lifespan)
        with TestClient(app) as client:
            assert client.get("/openapi.json").status_code == HTTPStatus.OK

    def test_explicit_disabled_overrides_development(self) -> None:
        """docs.enabled=False force-disables docs in development."""
        app = FastAPIBuilder(
            root_config=_root_config(
                environment=EnvironmentEnum.DEVELOPMENT,
                docs=DocsConfig(enabled=False),
            )
        ).build(lifespan=_noop_lifespan)
        with TestClient(app) as client:
            assert client.get("/docs").status_code == HTTPStatus.NOT_FOUND
