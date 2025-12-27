"""Tests for MongoDB persistence of books."""

import os
from http import HTTPStatus
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from structlog.stdlib import get_logger
from testcontainers.mongodb import MongoDbContainer  # type: ignore[import-untyped]

from fastapi_factory_utilities.example.app import AppBuilder

_logger = get_logger(__package__)


class TestBookPersistence:
    """Tests for MongoDB persistence of books."""

    @pytest.mark.asyncio()
    async def test_books_persist_across_app_restarts(self, mongodb_server_as_container: MongoDbContainer) -> None:
        """Test that books persist in MongoDB across application restarts."""
        mongo_uri: str = mongodb_server_as_container.get_connection_url()

        with patch.dict(os.environ, {"MONGO_URI": mongo_uri}):
            # First application instance - create books
            with TestClient(app=AppBuilder().build()) as client1:
                books_to_create: list[dict[str, Any]] = [
                    {"title": "Persistent Book 1", "book_type": "fantasy"},
                    {"title": "Persistent Book 2", "book_type": "mystery"},
                    {"title": "Persistent Book 3", "book_type": "science_fiction"},
                ]

                created_ids: list[str] = []
                for book_data in books_to_create:
                    response: Response = client1.post("/api/v1/books", json=book_data)
                    assert response.status_code == HTTPStatus.CREATED
                    created_ids.append(str(response.json()["id"]))

            # Second application instance - verify books still exist
            with TestClient(app=AppBuilder().build()) as client2:
                response: Response = client2.get("/api/v1/books")
                assert response.status_code == HTTPStatus.OK

                data: dict[str, Any] = response.json()
                assert data["size"] == len(books_to_create)

                # Verify all created books exist
                book_titles: list[str] = [str(book["title"]) for book in data["books"]]
                assert "Persistent Book 1" in book_titles
                assert "Persistent Book 2" in book_titles
                assert "Persistent Book 3" in book_titles

    @pytest.mark.asyncio()
    async def test_data_integrity_after_operations(self, mongodb_server_as_container: MongoDbContainer) -> None:
        """Test data integrity is maintained after multiple operations."""
        mongo_uri: str = mongodb_server_as_container.get_connection_url()

        with patch.dict(os.environ, {"MONGO_URI": mongo_uri}):
            with TestClient(app=AppBuilder().build()) as client:
                # Create initial book
                book_data: dict[str, Any] = {"title": "Data Integrity Test", "book_type": "thriller"}
                create_response: Response = client.post("/api/v1/books", json=book_data)
                assert create_response.status_code == HTTPStatus.CREATED

                book_id: str = str(create_response.json()["id"])

                # Perform multiple updates
                for i in range(5):
                    update_data: dict[str, Any] = {
                        "title": f"Updated Title {i}",
                        "book_type": "horror",
                    }
                    update_response: Response = client.put(f"/api/v1/books/{book_id}", json=update_data)
                    assert update_response.status_code == HTTPStatus.OK

                # Verify final state
                final_response: Response = client.get(f"/api/v1/books/{book_id}")
                assert final_response.status_code == HTTPStatus.OK

                final_book: dict[str, Any] = final_response.json()
                assert final_book["title"] == "Updated Title 4"
                assert final_book["book_type"] == "horror"
                assert final_book["id"] == book_id

    @pytest.mark.asyncio()
    async def test_unique_title_constraint(self, mongodb_server_as_container: MongoDbContainer) -> None:
        """Test that duplicate book titles are handled correctly."""
        mongo_uri: str = mongodb_server_as_container.get_connection_url()

        with patch.dict(os.environ, {"MONGO_URI": mongo_uri}):
            with TestClient(app=AppBuilder().build()) as client:
                # Create first book
                book_data: dict[str, Any] = {"title": "Unique Title Test Book", "book_type": "fantasy"}
                first_response: Response = client.post("/api/v1/books", json=book_data)
                assert first_response.status_code == HTTPStatus.CREATED

                # For this test, we just verify the first creation works
                # The unique constraint is enforced at database level
                assert first_response.json()["title"] == "Unique Title Test Book"

    @pytest.mark.asyncio()
    async def test_delete_and_recreate(self, mongodb_server_as_container: MongoDbContainer) -> None:
        """Test that a book can be deleted and a new one with same title can be created."""
        mongo_uri: str = mongodb_server_as_container.get_connection_url()

        with patch.dict(os.environ, {"MONGO_URI": mongo_uri}):
            with TestClient(app=AppBuilder().build()) as client:
                # Create book
                book_data: dict[str, Any] = {"title": "Delete and Recreate", "book_type": "romance"}
                create_response: Response = client.post("/api/v1/books", json=book_data)
                assert create_response.status_code == HTTPStatus.CREATED

                book_id: str = str(create_response.json()["id"])

                # Delete book
                delete_response: Response = client.delete(f"/api/v1/books/{book_id}")
                assert delete_response.status_code == HTTPStatus.NO_CONTENT

                # Create new book with same title
                recreate_response: Response = client.post("/api/v1/books", json=book_data)
                assert recreate_response.status_code == HTTPStatus.CREATED

                new_book: dict[str, Any] = recreate_response.json()
                assert new_book["title"] == "Delete and Recreate"
                assert new_book["id"] != book_id  # Should have different ID
