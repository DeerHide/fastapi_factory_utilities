"""Unit tests for FastAPIBuilder CORS middleware installation."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from starlette.middleware import Middleware

from fastapi_factory_utilities.core.app.config import (
    BaseApplicationConfig,
    CorsConfig,
    RootConfig,
)
from fastapi_factory_utilities.core.app.enums import EnvironmentEnum
from fastapi_factory_utilities.core.app.fastapi_builder import FastAPIBuilder


def _root_config(*, cors: CorsConfig | None = None) -> RootConfig:
    """Build a minimal RootConfig for FastAPIBuilder tests."""
    return RootConfig(
        application=BaseApplicationConfig(
            service_namespace="test",
            environment=EnvironmentEnum.DEVELOPMENT,
            service_name="cors-test",
            description="CORS builder tests",
            version="0.0.0",
        ),
        cors=cors if cors is not None else CorsConfig(),
    )


@asynccontextmanager
async def _noop_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """No-op lifespan for builder tests."""
    yield


def _cors_middleware_entries(app: FastAPI) -> list[Middleware]:
    """Return CORSMiddleware entries from the app's user middleware stack."""
    return [entry for entry in app.user_middleware if entry.cls is CORSMiddleware]


class TestFastAPIBuilderCors:
    """FastAPIBuilder CORS opt-in behavior."""

    def test_default_config_does_not_install_cors_middleware(self) -> None:
        """Empty default allow_origins must not install CORSMiddleware."""
        app = FastAPIBuilder(root_config=_root_config()).build(lifespan=_noop_lifespan)
        assert _cors_middleware_entries(app) == []

    def test_default_config_does_not_reflect_arbitrary_origin(self) -> None:
        """Default apps must not emit ACAO reflecting a foreign Origin."""
        app = FastAPIBuilder(root_config=_root_config()).build(lifespan=_noop_lifespan)

        @app.get("/ping")
        def ping() -> dict[str, str]:
            return {"ok": "yes"}

        client = TestClient(app)
        response = client.get("/ping", headers={"Origin": "https://evil.example"})
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers
        assert "access-control-allow-credentials" not in response.headers

    def test_explicit_origins_install_cors_middleware(self) -> None:
        """Non-empty allow_origins opts into CORSMiddleware."""
        cors = CorsConfig(
            allow_origins=["https://app.example"],
            allow_credentials=True,
        )
        app = FastAPIBuilder(root_config=_root_config(cors=cors)).build(lifespan=_noop_lifespan)
        entries = _cors_middleware_entries(app)
        assert len(entries) == 1
        kwargs: dict[str, Any] = entries[0].kwargs
        assert kwargs["allow_origins"] == ["https://app.example"]
        assert kwargs["allow_credentials"] is True

    def test_explicit_origin_allows_matching_credentialed_request(self) -> None:
        """Configured origin receives ACAO + credentials headers."""
        cors = CorsConfig(
            allow_origins=["https://app.example"],
            allow_credentials=True,
        )
        app = FastAPIBuilder(root_config=_root_config(cors=cors)).build(lifespan=_noop_lifespan)

        @app.get("/ping")
        def ping() -> dict[str, str]:
            return {"ok": "yes"}

        client = TestClient(app)
        response = client.get("/ping", headers={"Origin": "https://app.example"})
        assert response.headers["access-control-allow-origin"] == "https://app.example"
        assert response.headers["access-control-allow-credentials"] == "true"
        # Foreign origin must not be reflected.
        foreign = client.get("/ping", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in foreign.headers
