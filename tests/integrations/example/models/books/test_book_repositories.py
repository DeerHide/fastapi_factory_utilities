"""Provides unit tests for the BookRepository class."""

from typing import Any, cast
from uuid import uuid4

import beanie
import pytest
from pymongo.asynchronous.database import AsyncDatabase

from fastapi_factory_utilities.example.entities.books import (
    BookEntity,
    BookName,
    BookType,
)
from fastapi_factory_utilities.example.models.books.document import BookDocument
from fastapi_factory_utilities.example.models.books.repository import BookRepository


class TestIntegrationBookRepository:
    """Unit tests for the BookRepository class."""

    @pytest.mark.asyncio()
    async def test_book_create(self, async_motor_database: AsyncDatabase[Any]) -> None:
        """Test create method.

        Args:
            async_motor_database (AsyncDatabase): The async motor database.
        """
        await beanie.init_beanie(database=async_motor_database, document_models=[BookDocument])  # pyright: ignore
        book_repository = BookRepository(database=async_motor_database)

        book_entity_created: BookEntity = await book_repository.insert(
            entity=BookEntity(
                id=uuid4(),
                title=BookName("The Hobbit"),
                book_type=BookType.FANTASY,
            )
        )

        assert book_entity_created.title == BookName("The Hobbit")
        assert book_entity_created.book_type == BookType.FANTASY

    @pytest.mark.asyncio()
    async def test_book_get_one_by_id(self, async_motor_database: AsyncDatabase[Any]) -> None:
        """Test get_one_by_id method.

        Args:
            async_motor_database (AsyncDatabase): The async motor database.
        """
        await beanie.init_beanie(database=async_motor_database, document_models=[BookDocument])  # pyright: ignore
        book_repository = BookRepository(database=async_motor_database)

        book_entity_created: BookEntity = await book_repository.insert(
            entity=BookEntity(
                id=uuid4(),
                title=BookName("The Hobbit"),
                book_type=BookType.FANTASY,
            )
        )

        book_entity_retrieved: BookEntity = cast(
            BookEntity, await book_repository.get_one_by_id(entity_id=book_entity_created.id)
        )

        assert book_entity_retrieved.title == BookName("The Hobbit")
        assert book_entity_retrieved.book_type == BookType.FANTASY

    @pytest.mark.asyncio()
    async def test_book_delete_one_by_id(self, async_motor_database: AsyncDatabase[Any]) -> None:
        """Test delete_one_by_id method.

        Args:
            async_motor_database (AsyncDatabase): The async motor database.
        """
        await beanie.init_beanie(database=async_motor_database, document_models=[BookDocument])  # pyright: ignore
        book_repository = BookRepository(database=async_motor_database)

        book_entity_created: BookEntity = await book_repository.insert(
            entity=BookEntity(
                id=uuid4(),
                title=BookName("The Hobbit"),
                book_type=BookType.FANTASY,
            )
        )

        await book_repository.delete_one_by_id(entity_id=book_entity_created.id)

        book_entity_retrieved: BookEntity = cast(
            BookEntity, await book_repository.get_one_by_id(entity_id=book_entity_created.id)
        )

        assert book_entity_retrieved is None

    @pytest.mark.asyncio()
    async def test_find_all_books(self, async_motor_database: AsyncDatabase[Any]) -> None:
        """Test finding all books.

        Args:
            async_motor_database (AsyncDatabase): The async motor database.
        """
        await beanie.init_beanie(database=async_motor_database, document_models=[BookDocument])  # pyright: ignore
        book_repository = BookRepository(database=async_motor_database)

        # Create multiple books
        books_to_create = [
            BookEntity(
                id=uuid4(),
                title=BookName("The Hobbit"),
                book_type=BookType.FANTASY,
            ),
            BookEntity(
                id=uuid4(),
                title=BookName("1984"),
                book_type=BookType.SCIENCE_FICTION,
            ),
            BookEntity(
                id=uuid4(),
                title=BookName("The Great Gatsby"),
                book_type=BookType.THRILLER,
            ),
        ]

        for book in books_to_create:
            await book_repository.insert(entity=book)

        # Find all books
        found_books = await book_repository.find()
        assert len(found_books) == len(books_to_create)

    @pytest.mark.asyncio()
    async def test_find_books_with_filter(self, async_motor_database: AsyncDatabase[Any]) -> None:
        """Test finding books with filter.

        Args:
            async_motor_database (AsyncDatabase): The async motor database.
        """
        await beanie.init_beanie(database=async_motor_database, document_models=[BookDocument])  # pyright: ignore
        book_repository = BookRepository(database=async_motor_database)

        # Create multiple books
        books_to_create = [
            BookEntity(
                id=uuid4(),
                title=BookName("The Hobbit"),
                book_type=BookType.FANTASY,
            ),
            BookEntity(
                id=uuid4(),
                title=BookName("The Lord of the Rings"),
                book_type=BookType.FANTASY,
            ),
            BookEntity(
                id=uuid4(),
                title=BookName("1984"),
                book_type=BookType.SCIENCE_FICTION,
            ),
        ]

        for book in books_to_create:
            await book_repository.insert(entity=book)

        # Find only fantasy books
        fantasy_books = await book_repository.find({"book_type": BookType.FANTASY})
        assert len(fantasy_books) == 2  # noqa: PLR2004
        assert all(book.book_type == BookType.FANTASY for book in fantasy_books)

    @pytest.mark.asyncio()
    async def test_find_books_with_pagination(self, async_motor_database: AsyncDatabase[Any]) -> None:
        """Test finding books with pagination.

        Args:
            async_motor_database (AsyncDatabase): The async motor database.
        """
        await beanie.init_beanie(database=async_motor_database, document_models=[BookDocument])  # pyright: ignore
        book_repository = BookRepository(database=async_motor_database)

        # Create multiple books
        books_to_create = [
            BookEntity(
                id=uuid4(),
                title=BookName(f"Book {i}"),
                book_type=BookType.THRILLER,
            )
            for i in range(5)
        ]

        for book in books_to_create:
            await book_repository.insert(entity=book)

        # Test pagination
        first_page = await book_repository.find(skip=0, limit=2)
        assert len(first_page) == 2  # noqa: PLR2004

        second_page = await book_repository.find(skip=2, limit=2)
        assert len(second_page) == 2  # noqa: PLR2004

        last_page = await book_repository.find(skip=4, limit=2)
        assert len(last_page) == 1

    @pytest.mark.asyncio()
    async def test_find_books_with_sort(self, async_motor_database: AsyncDatabase[Any]) -> None:
        """Test finding books with sorting.

        Args:
            async_motor_database (AsyncDatabase): The async motor database.
        """
        await beanie.init_beanie(database=async_motor_database, document_models=[BookDocument])  # pyright: ignore
        book_repository = BookRepository(database=async_motor_database)

        # Create books with different titles
        books_to_create = [
            BookEntity(
                id=uuid4(),
                title=BookName("C Book"),
                book_type=BookType.THRILLER,
            ),
            BookEntity(
                id=uuid4(),
                title=BookName("A Book"),
                book_type=BookType.THRILLER,
            ),
            BookEntity(
                id=uuid4(),
                title=BookName("B Book"),
                book_type=BookType.THRILLER,
            ),
        ]

        for book in books_to_create:
            await book_repository.insert(entity=book)

        # Test sorting by title ascending
        sorted_books = await book_repository.find(sort=[("title", 1)])
        assert len(sorted_books) == 3  # noqa: PLR2004
        assert sorted_books[0].title == BookName("A Book")
        assert sorted_books[1].title == BookName("B Book")
        assert sorted_books[2].title == BookName("C Book")
