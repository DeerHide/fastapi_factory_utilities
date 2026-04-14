"""Integration tests for ASGI server utilities."""

import asyncio
import socket
from threading import Thread
from time import sleep

import httpx
import pytest
import uvicorn
from fastapi import FastAPI
from hypercorn.asyncio import serve as hypercorn_serve

from fastapi_factory_utilities.core.app.builder import ServerImplementationEnum
from fastapi_factory_utilities.core.app.config import BaseApplicationConfig, DevelopmentConfig, RootConfig, ServerConfig
from fastapi_factory_utilities.core.app.enums import EnvironmentEnum
from fastapi_factory_utilities.core.services.status.services import StatusService
from fastapi_factory_utilities.core.utils.hypercorn import HypercornUtils
from fastapi_factory_utilities.core.utils.uvicorn import UvicornUtils

HTTP_OK = 200


def _build_root_config(port: int) -> RootConfig:
    """Build a minimal root config used for integration tests."""
    return RootConfig(
        application=BaseApplicationConfig(
            service_namespace="test",
            service_name="test-app",
            description="test",
            version="0.0.0",
            environment=EnvironmentEnum.DEVELOPMENT,
        ),
        server=ServerConfig(host="127.0.0.1", port=port, workers=1),
        development=DevelopmentConfig(reload=False),
    )


class FakeApplication:
    """Minimal application implementing required protocol methods."""

    def __init__(self, root_config: RootConfig) -> None:
        """Initialize a fake application with a single health endpoint."""
        self._root_config = root_config
        self._status_service = StatusService()
        app = FastAPI()

        @app.get("/")
        async def root() -> dict[str, str]:
            return {"status": "ok"}

        self._app = app

    def get_config(self) -> RootConfig:
        """Return the root configuration."""
        return self._root_config

    def get_asgi_app(self) -> FastAPI:
        """Return the ASGI app."""
        return self._app

    def get_status_service(self) -> StatusService:
        """Return the status service."""
        return self._status_service


@pytest.fixture(name="free_port")
def fixture_free_port() -> int:
    """Provide a free local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_http_ready(base_url: str, timeout_seconds: float = 10.0) -> None:
    """Wait until HTTP server is reachable."""
    elapsed = 0.0
    while elapsed < timeout_seconds:
        try:
            response = httpx.get(f"{base_url}/", timeout=0.5)
            if response.status_code == HTTP_OK:
                return
        except (httpx.HTTPError, OSError):
            pass

        sleep(0.1)
        elapsed += 0.1

    raise TimeoutError(f"Server did not become ready in {timeout_seconds} seconds")


def test_uvicorn_utils_integration(free_port: int) -> None:
    """Serve a FastAPI app with UvicornUtils and validate response."""
    app = FakeApplication(root_config=_build_root_config(port=free_port))
    uvicorn_utils = UvicornUtils(app=app)
    config = uvicorn_utils.build_uvicorn_config()
    server = uvicorn.Server(config=config)
    server.install_signal_handlers = lambda: None  # type: ignore[method-assign]

    thread = Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{free_port}"
    try:
        _wait_http_ready(base_url=base_url)
        response = httpx.get(f"{base_url}/", timeout=2.0)
        assert response.status_code == HTTP_OK
        assert response.json() == {"status": "ok"}
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        assert not thread.is_alive()


@pytest.mark.asyncio
async def test_hypercorn_utils_integration(free_port: int) -> None:
    """Serve a FastAPI app with HypercornUtils and validate response."""
    app = FakeApplication(root_config=_build_root_config(port=free_port))
    hypercorn_utils = HypercornUtils(app=app)
    config = hypercorn_utils.build_hypercorn_config()

    shutdown_event = asyncio.Event()
    task = asyncio.create_task(
        hypercorn_serve(
            app=app.get_asgi_app(),
            config=config,
            shutdown_trigger=shutdown_event.wait,
        )
    )

    base_url = f"http://127.0.0.1:{free_port}"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            for _ in range(100):
                try:
                    response = await client.get(f"{base_url}/")
                    if response.status_code == HTTP_OK:
                        break
                except (httpx.HTTPError, OSError):
                    await asyncio.sleep(0.1)
            else:
                raise TimeoutError("Hypercorn server did not become ready")

            assert response.status_code == HTTP_OK
            assert response.json() == {"status": "ok"}
    finally:
        shutdown_event.set()
        await asyncio.wait_for(task, timeout=5.0)


def test_server_implementation_enum_defaults_to_uvicorn() -> None:
    """Ensure the default implementation value remains uvicorn."""
    assert ServerImplementationEnum.UVICORN == "uvicorn"
