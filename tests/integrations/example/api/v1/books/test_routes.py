"""Tests for the routes of the books API."""

import os
from http import HTTPStatus
from typing import Any
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from structlog.stdlib import get_logger
from testcontainers.mongodb import MongoDbContainer  # type: ignore[import-untyped]

from fastapi_factory_utilities.example.app import AppBuilder

_logger = get_logger(__package__)


class TestBooksRoutes:
    """Tests for the routes of the books API."""

    @pytest.mark.asyncio()
    async def test_create_book(self, mongodb_server_as_container: MongoDbContainer) -> None:
        """Test creating a new book."""
        mongo_uri: str = mongodb_server_as_container.get_connection_url()

        with patch.dict(os.environ, {"MONGO_URI": mongo_uri}):
            with TestClient(app=AppBuilder().build()) as client:
                book_data: dict[str, Any] = {
                    "title": "The Lord of the Rings",
                    "book_type": "fantasy",
                }

                response: Response = client.post("/api/v1/books", json=book_data)
                assert response.status_code == HTTPStatus.CREATED

                data: dict[str, Any] = response.json()
                assert "id" in data
                assert data["title"] == "The Lord of the Rings"
                assert data["book_type"] == "fantasy"

                # Verify UUID is valid
                book_id: UUID = UUID(str(data["id"]))
                assert isinstance(book_id, UUID)

    @pytest.mark.asyncio()
    async def test_create_book_validation_error(self, mongodb_server_as_container: MongoDbContainer) -> None:
        """Test creating a book with invalid data returns validation error."""
        mongo_uri: str = mongodb_server_as_container.get_connection_url()

        with patch.dict(os.environ, {"MONGO_URI": mongo_uri}):
            with TestClient(app=AppBuilder().build()) as client:
                # Missing required fields
                book_data: dict[str, Any] = {"title": "Incomplete Book"}

                response: Response = client.post("/api/v1/books", json=book_data)
                assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio()
    async def test_get_book_by_id(self, mongodb_server_as_container: MongoDbContainer) -> None:
        """Test getting a specific book by ID."""
        mongo_uri: str = mongodb_server_as_container.get_connection_url()

        with patch.dict(os.environ, {"MONGO_URI": mongo_uri}):
            with TestClient(app=AppBuilder().build()) as client:
                # Create a book
                book_data: dict[str, Any] = {"title": "Harry Potter", "book_type": "fantasy"}
                create_response: Response = client.post("/api/v1/books", json=book_data)
                assert create_response.status_code == HTTPStatus.CREATED

                created_book: dict[str, Any] = create_response.json()
                book_id: str = str(created_book["id"])

                # Get the book by ID
                response: Response = client.get(f"/api/v1/books/{book_id}")
                assert response.status_code == HTTPStatus.OK

                data: dict[str, Any] = response.json()
                assert data["id"] == book_id
                assert data["title"] == "Harry Potter"
                assert data["book_type"] == "fantasy"

    @pytest.mark.asyncio()
    async def test_get_book_not_found(self, mongodb_server_as_container: MongoDbContainer) -> None:
        """Test getting a non-existent book returns error."""
        mongo_uri: str = mongodb_server_as_container.get_connection_url()

        with patch.dict(os.environ, {"MONGO_URI": mongo_uri}):
            with TestClient(app=AppBuilder().build()) as client:
                non_existent_id: UUID = uuid4()
                response: Response = client.get(f"/api/v1/books/{non_existent_id}")
                assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio()
    async def test_update_book(self, mongodb_server_as_container: MongoDbContainer) -> None:
        """Test updating an existing book."""
        mongo_uri: str = mongodb_server_as_container.get_connection_url()

        with patch.dict(os.environ, {"MONGO_URI": mongo_uri}):
            with TestClient(app=AppBuilder().build()) as client:
                # Create a book
                book_data: dict[str, Any] = {"title": "Original Title", "book_type": "mystery"}
                create_response: Response = client.post("/api/v1/books", json=book_data)
                assert create_response.status_code == HTTPStatus.CREATED

                created_book: dict[str, Any] = create_response.json()
                book_id: str = str(created_book["id"])

                # Update the book
                update_data: dict[str, Any] = {"title": "Updated Title", "book_type": "thriller"}
                response: Response = client.put(f"/api/v1/books/{book_id}", json=update_data)
                assert response.status_code == HTTPStatus.OK

                data: dict[str, Any] = response.json()
                assert data["id"] == book_id
                assert data["title"] == "Updated Title"
                assert data["book_type"] == "thriller"

    @pytest.mark.asyncio()
    async def test_update_book_not_found(self, mongodb_server_as_container: MongoDbContainer) -> None:
        """Test updating a non-existent book returns error."""
        mongo_uri: str = mongodb_server_as_container.get_connection_url()

        with patch.dict(os.environ, {"MONGO_URI": mongo_uri}):
            with TestClient(app=AppBuilder().build()) as client:
                non_existent_id: UUID = uuid4()
                update_data: dict[str, Any] = {"title": "New Title", "book_type": "fantasy"}
                response: Response = client.put(f"/api/v1/books/{non_existent_id}", json=update_data)
                assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio()
    async def test_delete_book(self, mongodb_server_as_container: MongoDbContainer) -> None:
        """Test deleting an existing book."""
        mongo_uri: str = mongodb_server_as_container.get_connection_url()

        with patch.dict(os.environ, {"MONGO_URI": mongo_uri}):
            with TestClient(app=AppBuilder().build()) as client:
                # Create a book
                book_data: dict[str, Any] = {"title": "Book to Delete", "book_type": "horror"}
                create_response: Response = client.post("/api/v1/books", json=book_data)
                assert create_response.status_code == HTTPStatus.CREATED

                created_book: dict[str, Any] = create_response.json()
                book_id: str = str(created_book["id"])

                # Delete the book
                response: Response = client.delete(f"/api/v1/books/{book_id}")
                assert response.status_code == HTTPStatus.NO_CONTENT

                # Verify book is deleted
                get_response: Response = client.get(f"/api/v1/books/{book_id}")
                assert get_response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio()
    async def test_delete_book_not_found(self, mongodb_server_as_container: MongoDbContainer) -> None:
        """Test deleting a non-existent book returns error."""
        mongo_uri: str = mongodb_server_as_container.get_connection_url()

        with patch.dict(os.environ, {"MONGO_URI": mongo_uri}):
            with TestClient(app=AppBuilder().build()) as client:
                non_existent_id: UUID = uuid4()
                response: Response = client.delete(f"/api/v1/books/{non_existent_id}")
                assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio()
    async def test_full_crud_flow(self, mongodb_server_as_container: MongoDbContainer) -> None:
        """Test complete CRUD flow: Create → Read → Update → Delete."""
        mongo_uri: str = mongodb_server_as_container.get_connection_url()

        with patch.dict(os.environ, {"MONGO_URI": mongo_uri}):
            with TestClient(app=AppBuilder().build()) as client:
                # 1. Create a book
                book_data: dict[str, Any] = {"title": "CRUD Test Book", "book_type": "adventure"}
                create_response: Response = client.post("/api/v1/books", json=book_data)
                assert create_response.status_code == HTTPStatus.CREATED

                created_book: dict[str, Any] = create_response.json()
                book_id: str = str(created_book["id"])
                assert created_book["title"] == "CRUD Test Book"
                assert created_book["book_type"] == "adventure"

                # 2. Read the book
                read_response: Response = client.get(f"/api/v1/books/{book_id}")
                assert read_response.status_code == HTTPStatus.OK

                read_book: dict[str, Any] = read_response.json()
                assert read_book["id"] == book_id
                assert read_book["title"] == "CRUD Test Book"

                # 3. Update the book
                update_data: dict[str, Any] = {"title": "Updated CRUD Book", "book_type": "historical_fiction"}
                update_response: Response = client.put(f"/api/v1/books/{book_id}", json=update_data)
                assert update_response.status_code == HTTPStatus.OK

                updated_book: dict[str, Any] = update_response.json()
                assert updated_book["id"] == book_id
                assert updated_book["title"] == "Updated CRUD Book"
                assert updated_book["book_type"] == "historical_fiction"

                # 4. Verify the update persisted
                verify_response: Response = client.get(f"/api/v1/books/{book_id}")
                assert verify_response.status_code == HTTPStatus.OK

                verified_book: dict[str, Any] = verify_response.json()
                assert verified_book["title"] == "Updated CRUD Book"
                assert verified_book["book_type"] == "historical_fiction"

                # 5. Delete the book
                delete_response: Response = client.delete(f"/api/v1/books/{book_id}")
                assert delete_response.status_code == HTTPStatus.NO_CONTENT

                # 6. Verify deletion
                final_response: Response = client.get(f"/api/v1/books/{book_id}")
                assert final_response.status_code == HTTPStatus.NOT_FOUND
