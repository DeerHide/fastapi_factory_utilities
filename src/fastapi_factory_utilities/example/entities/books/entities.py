"""Provides the Book entity."""

from pydantic import Field

from fastapi_factory_utilities.core.plugins.odm_plugin.helpers import PersistedEntity

from .enums import BookType
from .types import BookEntityId, BookName


class BookEntity(PersistedEntity[BookEntityId]):
    """Book entity."""

    title: BookName = Field(title="Title of the book")
    book_type: BookType = Field(title="Type of book")
