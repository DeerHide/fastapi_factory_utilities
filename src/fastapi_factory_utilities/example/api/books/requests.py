"""Provides the request objects for the books API."""

from pydantic import BaseModel, Field

from fastapi_factory_utilities.example.entities.books import BookName, BookType


class BookCreateRequest(BaseModel):
    """Book creation request model."""

    title: BookName = Field(title="Title of the book", description="The title of the book to create")
    book_type: BookType = Field(title="Type of book", description="The genre/type of the book")


class BookUpdateRequest(BaseModel):
    """Book update request model."""

    title: BookName = Field(title="Title of the book", description="The updated title of the book")
    book_type: BookType = Field(title="Type of book", description="The updated genre/type of the book")
