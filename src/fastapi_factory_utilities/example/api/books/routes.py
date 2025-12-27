"""Provides the Books API."""

from http import HTTPStatus
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response

from fastapi_factory_utilities.example.entities.books import BookEntity
from fastapi_factory_utilities.example.services.books import (
    BookService,
    depends_book_service,
)

from .requests import BookCreateRequest, BookUpdateRequest
from .responses import BookListReponse, BookResponseModel

api_v1_books_router: APIRouter = APIRouter(prefix="/books")
api_v2_books_router: APIRouter = APIRouter(prefix="/books")


@api_v1_books_router.get(path="", response_model=BookListReponse)
async def get_books(
    books_service: BookService = Depends(depends_book_service),
) -> BookListReponse:
    """Get all books.

    Args:
        books_service: Book service.

    Returns:
        List of books.
    """
    books: list[BookEntity] = await books_service.get_all_books()

    return BookListReponse(
        books=cast(
            list[BookResponseModel],
            map(lambda book: BookResponseModel(**book.model_dump()), books),
        ),
        size=len(books),
    )


@api_v1_books_router.get(path="/{book_id}", response_model=BookResponseModel)
async def get_book(
    book_id: UUID,
    books_service: BookService = Depends(depends_book_service),
) -> BookResponseModel:
    """Get a book.

    Args:
        book_id: Book id.
        books_service: Book service.

    Returns:
        Book.

    Raises:
        HTTPException: 404 if book not found.
    """
    try:
        book: BookEntity = await books_service.get_book(book_id)
        return BookResponseModel(**book.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(e)) from e


@api_v1_books_router.post(path="", response_model=BookResponseModel, status_code=HTTPStatus.CREATED)
async def create_book(
    request: BookCreateRequest,
    books_service: BookService = Depends(depends_book_service),
) -> BookResponseModel:
    """Create a new book.

    Args:
        request: Book creation request.
        books_service: Book service.

    Returns:
        Created book.
    """
    book_entity: BookEntity = BookEntity(
        title=request.title,
        book_type=request.book_type,
    )

    created_book: BookEntity = await books_service.add_book(book=book_entity)

    return BookResponseModel(**created_book.model_dump())


@api_v1_books_router.put(path="/{book_id}", response_model=BookResponseModel)
async def update_book(
    book_id: UUID,
    request: BookUpdateRequest,
    books_service: BookService = Depends(depends_book_service),
) -> BookResponseModel:
    """Update an existing book.

    Args:
        book_id: Book id.
        request: Book update request.
        books_service: Book service.

    Returns:
        Updated book.

    Raises:
        HTTPException: 404 if book not found.
    """
    try:
        book_entity: BookEntity = await books_service.get_book(book_id=book_id)
        updated_book_entity: BookEntity = book_entity.model_copy(
            update={"title": request.title, "book_type": request.book_type}
        )
        updated_book: BookEntity = await books_service.update_book(book=updated_book_entity)

        return BookResponseModel(**updated_book.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(e)) from e


@api_v1_books_router.delete(path="/{book_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_book(
    book_id: UUID,
    books_service: BookService = Depends(depends_book_service),
) -> Response:
    """Delete a book.

    Args:
        book_id: Book id.
        books_service: Book service.

    Returns:
        No content response.

    Raises:
        HTTPException: 404 if book not found.
    """
    try:
        await books_service.remove_book(book_id=book_id)
        return Response(status_code=HTTPStatus.NO_CONTENT)
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(e)) from e
