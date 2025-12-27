"""Provides services for books."""

from uuid import UUID

from fastapi import Request
from opentelemetry import metrics

from fastapi_factory_utilities.core.plugins.odm_plugin.depends import (
    depends_odm_database,
)
from fastapi_factory_utilities.core.plugins.opentelemetry_plugin.helpers import (
    trace_span,
)
from fastapi_factory_utilities.example.entities.books import BookEntity
from fastapi_factory_utilities.example.models.books.repository import BookRepository


class BookService:
    """Provides services for books."""

    # Metrics Definitions
    METER_COUNTER_BOOK_GET_NAME: str = "book_get"
    METER_COUNTER_BOOK_ADD_NAME: str = "book_add"
    METER_COUNTER_BOOK_REMOVE_NAME: str = "book_remove"
    METER_COUNTER_BOOK_UPDATE_NAME: str = "book_update"
    # ====================

    meter: metrics.Meter = metrics.get_meter(__name__)

    METER_COUNTER_BOOK_GET: metrics.Counter = meter.create_counter(
        name=METER_COUNTER_BOOK_GET_NAME, description="The number of books retrieved."
    )
    METER_COUNTER_BOOK_ADD: metrics.Counter = meter.create_counter(
        name=METER_COUNTER_BOOK_ADD_NAME,
        description="The number of books added.",
    )
    METER_COUNTER_BOOK_REMOVE: metrics.Counter = meter.create_counter(
        name=METER_COUNTER_BOOK_REMOVE_NAME,
        description="The number of books removed.",
    )
    METER_COUNTER_BOOK_UPDATE: metrics.Counter = meter.create_counter(
        name=METER_COUNTER_BOOK_UPDATE_NAME,
        description="The number of books updated.",
    )

    def __init__(
        self,
        book_repository: BookRepository,
    ) -> None:
        """Initialize the service.

        Args:
            book_repository: The book repository.
        """
        self.book_repository: BookRepository = book_repository

    @trace_span(name="Add Book")
    async def add_book(self, book: BookEntity) -> BookEntity:
        """Add a book.

        Args:
            book: The book to add.

        Returns:
            The created book entity.

        Raises:
            UnableToCreateEntityDueToDuplicateKeyError: If a book with the same title already exists.
            OperationError: If the operation fails.
        """
        created_book: BookEntity = await self.book_repository.insert(entity=book)
        self.METER_COUNTER_BOOK_ADD.add(amount=1)
        return created_book

    async def get_book(self, book_id: UUID) -> BookEntity:
        """Get a book.

        Args:
            book_id: The book id.

        Returns:
            The book entity.

        Raises:
            ValueError: If the book does not exist.
            OperationError: If the operation fails.
        """
        book: BookEntity | None = await self.book_repository.get_one_by_id(entity_id=book_id)

        if book is None:
            raise ValueError(f"Book with id {book_id} does not exist.")

        self.METER_COUNTER_BOOK_GET.add(amount=1, attributes={"book_count": 1})
        return book

    async def get_all_books(self) -> list[BookEntity]:
        """Get all books.

        Returns:
            All books.

        Raises:
            OperationError: If the operation fails.
        """
        books: list[BookEntity] = await self.book_repository.find()
        self.METER_COUNTER_BOOK_GET.add(amount=1, attributes={"book_count": len(books)})
        return books

    @trace_span(name="Remove Book")
    async def remove_book(self, book_id: UUID) -> None:
        """Remove a book.

        Args:
            book_id: The book id.

        Raises:
            ValueError: If the book does not exist.
            OperationError: If the operation fails.
        """
        await self.book_repository.delete_one_by_id(entity_id=book_id, raise_if_not_found=True)

        self.METER_COUNTER_BOOK_REMOVE.add(amount=1)

    @trace_span(name="Update Book")
    async def update_book(self, book: BookEntity) -> BookEntity:
        """Update a book.

        Args:
            book: The book to update.

        Returns:
            The updated book entity.

        Raises:
            ValueError: If the book does not exist.
            OperationError: If the operation fails.
        """
        # Check if book exists
        existing_book: BookEntity | None = await self.book_repository.get_one_by_id(entity_id=book.id)

        if existing_book is None:
            raise ValueError(f"Book with id {book.id} does not exist.")

        updated_book: BookEntity = await self.book_repository.update(entity=book)
        self.METER_COUNTER_BOOK_UPDATE.add(amount=1)
        return updated_book


def depends_book_service(request: Request) -> BookService:
    """Provide Book Service.

    Args:
        request: FastAPI request object.

    Returns:
        BookService instance.
    """
    return BookService(book_repository=BookRepository(database=depends_odm_database(request=request)))
