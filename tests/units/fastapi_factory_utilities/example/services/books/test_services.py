"""Test the services module."""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from fastapi_factory_utilities.example.entities.books import (
    BookEntity,
    BookName,
    BookType,
)
from fastapi_factory_utilities.example.models.books.repository import BookRepository
from fastapi_factory_utilities.example.services.books.services import BookService


class TestBookService:
    """Test the BookService class."""

    @pytest.mark.asyncio()
    async def test_get_all_books(self) -> None:
        """Test get_all_books."""
        mock_repo: MagicMock = MagicMock(spec=BookRepository)
        mock_repo.find = AsyncMock(return_value=[])

        book_service = BookService(book_repository=mock_repo)
        books: list[BookEntity] = await book_service.get_all_books()

        assert len(books) == 0
        mock_repo.find.assert_called_once()

    @pytest.mark.asyncio()
    async def test_get_book(self) -> None:
        """Test get_book."""
        book_id: UUID = uuid4()
        test_book: BookEntity = BookEntity(
            id=book_id,
            title=BookName("Test Book"),
            book_type=BookType.FANTASY,
        )

        mock_repo: MagicMock = MagicMock(spec=BookRepository)
        mock_repo.get_one_by_id = AsyncMock(return_value=test_book)

        book_service = BookService(book_repository=mock_repo)
        book: BookEntity = await book_service.get_book(book_id=book_id)

        assert book == test_book
        mock_repo.get_one_by_id.assert_called_once_with(entity_id=book_id)

    @pytest.mark.asyncio()
    async def test_add_book(self) -> None:
        """Test add_book."""
        test_book: BookEntity = BookEntity(title=BookName("Test Book"), book_type=BookType.FANTASY)

        mock_repo: MagicMock = MagicMock(spec=BookRepository)
        mock_repo.insert = AsyncMock(return_value=test_book)

        book_service = BookService(book_repository=mock_repo)
        created_book: BookEntity = await book_service.add_book(book=test_book)

        assert created_book == test_book
        mock_repo.insert.assert_called_once_with(entity=test_book)

    @pytest.mark.asyncio()
    async def test_get_book_not_found(self) -> None:
        """Test get_book with a book that does not exist."""
        book_id: UUID = uuid4()

        mock_repo: MagicMock = MagicMock(spec=BookRepository)
        mock_repo.get_one_by_id = AsyncMock(return_value=None)

        book_service = BookService(book_repository=mock_repo)

        with pytest.raises(ValueError, match=f"Book with id {book_id} does not exist."):
            await book_service.get_book(book_id=book_id)

        mock_repo.get_one_by_id.assert_called_once_with(entity_id=book_id)

    @pytest.mark.asyncio()
    async def test_remove_book(self) -> None:
        """Test remove_book."""
        book_id: UUID = uuid4()

        mock_repo: MagicMock = MagicMock(spec=BookRepository)
        mock_repo.delete_one_by_id = AsyncMock(return_value=None)

        book_service = BookService(book_repository=mock_repo)
        await book_service.remove_book(book_id=book_id)

        mock_repo.delete_one_by_id.assert_called_once_with(entity_id=book_id, raise_if_not_found=True)

    @pytest.mark.asyncio()
    async def test_remove_book_does_not_exist(self) -> None:
        """Test remove_book with a book that does not exist."""
        book_id: UUID = uuid4()

        mock_repo: MagicMock = MagicMock(spec=BookRepository)
        mock_repo.delete_one_by_id = AsyncMock(side_effect=ValueError(f"Failed to find document with ID {book_id}"))

        book_service = BookService(book_repository=mock_repo)

        with pytest.raises(ValueError):
            await book_service.remove_book(book_id=book_id)

        mock_repo.delete_one_by_id.assert_called_once_with(entity_id=book_id, raise_if_not_found=True)

    @pytest.mark.asyncio()
    async def test_update_book(self) -> None:
        """Test update_book."""
        book_id: UUID = uuid4()
        existing_book: BookEntity = BookEntity(
            id=book_id,
            title=BookName("Original Title"),
            book_type=BookType.MYSTERY,
        )
        updated_book: BookEntity = BookEntity(
            id=book_id,
            title=BookName("Updated Title"),
            book_type=BookType.FANTASY,
        )

        mock_repo: MagicMock = MagicMock(spec=BookRepository)
        mock_repo.get_one_by_id = AsyncMock(return_value=existing_book)
        mock_repo.update = AsyncMock(return_value=updated_book)

        book_service = BookService(book_repository=mock_repo)
        result: BookEntity = await book_service.update_book(book=updated_book)

        assert result == updated_book
        mock_repo.get_one_by_id.assert_called_once_with(entity_id=book_id)
        mock_repo.update.assert_called_once_with(entity=updated_book)

    @pytest.mark.asyncio()
    async def test_update_book_does_not_exist(self) -> None:
        """Test update_book with a book that does not exist."""
        book_id: UUID = uuid4()
        book: BookEntity = BookEntity(
            id=book_id,
            title=BookName("Updated Title"),
            book_type=BookType.FANTASY,
        )

        mock_repo: MagicMock = MagicMock(spec=BookRepository)
        mock_repo.get_one_by_id = AsyncMock(return_value=None)

        book_service = BookService(book_repository=mock_repo)

        with pytest.raises(ValueError, match=f"Book with id {book.id} does not exist."):
            await book_service.update_book(book=book)

        mock_repo.get_one_by_id.assert_called_once_with(entity_id=book_id)
        # update should not be called since the book doesn't exist
        assert not mock_repo.update.called
