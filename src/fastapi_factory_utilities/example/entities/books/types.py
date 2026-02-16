"""Provides types for the books service."""

from typing import Any, NewType, cast
from uuid import UUID

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

BookEntityId = NewType("BookEntityId", UUID)


class BookName(str):
    """Book name type."""

    MIN_LENGTH: int = 1
    MAX_LENGTH: int = 100

    def __new__(cls, value: str) -> "BookName":
        """Create a new instance of BookName."""
        return super().__new__(cls, cls.validate(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, source: type[Any], handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        """Get the Pydantic core schema for the book name.

        Args:
            source (Type[Any]): Source type.
            handler (GetCoreSchemaHandler): Handler.

        Returns:
            core_schema.CoreSchema: Core schema.
        """
        del source, handler
        return cast(
            core_schema.CoreSchema,
            core_schema.no_info_after_validator_function(
                function=cls.validate,
                schema=core_schema.str_schema(min_length=cls.MIN_LENGTH, max_length=cls.MAX_LENGTH),
            ),
        )

    @classmethod
    def validate(cls, value: str) -> str:
        """Validate the book name.

        Args:
            value (str): Book name.

        Returns:
            str: Book name.
        """
        if not cls.MIN_LENGTH <= len(value) <= cls.MAX_LENGTH:
            raise ValueError(
                f"Expected a string with length between {cls.MIN_LENGTH}" + f" and {cls.MAX_LENGTH}, got {len(value)}"
            )

        return value
