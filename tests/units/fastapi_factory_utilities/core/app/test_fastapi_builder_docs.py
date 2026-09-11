"""Unit tests for OpenAPI / docs exposure via FastAPIBuilder."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

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
    """Build a minimal RootConfig for docs exposure tests."""
    return RootConfig(
        application=BaseApplicationConfig(
            service_namespace="test",
            environment=environment,
            service_name="docs-test",
            description="docs exposure tests",
            version="0.0.0",
        ),
        docs=docs if docs is not None else DocsConfig(),
    )


@asynccontextmanager
async def _noop_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield


class TestFastAPIBuilderDocsExposure:
    """Docs / OpenAPI are opt-in outside development by default."""

    def test_production_defaults_disable_docs_and_openapi(self) -> None:
        """Production apps must not expose /docs, /redoc, or /openapi.json."""
        app = FastAPIBuilder(root_config=_root_config(environment=EnvironmentEnum.PRODUCTION)).build(
            lifespan=_noop_lifespan
        )
        client = TestClient(app)
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404

    def test_development_defaults_enable_docs(self) -> None:
        """Development still gets interactive docs when docs.enabled is unset."""
        app = FastAPIBuilder(root_config=_root_config(environment=EnvironmentEnum.DEVELOPMENT)).build(
            lifespan=_noop_lifespan
        )
        client = TestClient(app)
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").status_code == 200

    def test_explicit_enabled_overrides_production(self) -> None:
        """docs.enabled=True force-enables docs in production."""
        app = FastAPIBuilder(
            root_config=_root_config(
                environment=EnvironmentEnum.PRODUCTION,
                docs=DocsConfig(enabled=True),
            )
        ).build(lifespan=_noop_lifespan)
        assert TestClient(app).get("/openapi.json").status_code == 200

    def test_explicit_disabled_overrides_development(self) -> None:
        """docs.enabled=False force-disables docs in development."""
        app = FastAPIBuilder(
            root_config=_root_config(
                environment=EnvironmentEnum.DEVELOPMENT,
                docs=DocsConfig(enabled=False),
            )
        ).build(lifespan=_noop_lifespan)
        assert TestClient(app).get("/docs").status_code == 404
