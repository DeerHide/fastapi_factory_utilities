"""Unit tests for application exception handlers."""

from http import HTTPStatus

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from fastapi_factory_utilities.core.app.handlers import register_exception_handlers


@pytest.mark.asyncio
async def test_validation_exception_handler_returns_422_and_structured_detail() -> None:
    """Request validation should return HTTP 422 with a FastAPI-like detail list."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/items/{item_id}")
    async def get_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/items/not-an-int")

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert detail[0]["loc"] == ["path", "item_id"]
