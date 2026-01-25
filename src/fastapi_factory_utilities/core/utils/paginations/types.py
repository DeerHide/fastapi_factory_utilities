"""Provides the types for the pagination utilities."""

from typing import Any

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema


class PaginationSize(int):
    """Pagination size type."""

    MIN_VALUE: int = 1
    MAX_VALUE: int = 200
    DEFAULT_VALUE: int = 50

    def __new__(cls, value: int) -> "PaginationSize":
        """Create a new instance of PaginationSize."""
        return super().__new__(cls, cls.validate(value))

    @classmethod
    def validate(cls, value: int) -> int:
        """Validate the pagination size."""
        if not cls.MIN_VALUE <= value <= cls.MAX_VALUE:
            raise ValueError(f"Invalid pagination size: {value}")
        return value

    @classmethod
    def default(cls) -> "PaginationSize":
        """Get the default pagination size."""
        return cls(cls.DEFAULT_VALUE)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,  # pylint: disable=unused-argument
        handler: GetCoreSchemaHandler,  # pylint: disable=unused-argument
    ) -> CoreSchema:
        """Get the core schema for the PaginationSize type."""
        return core_schema.no_info_after_validator_function(cls, handler(int))

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: core_schema.CoreSchema,  # pylint: disable=redefined-outer-name,unused-argument
        handler: GetJsonSchemaHandler,  # pylint: disable=unused-argument
    ) -> JsonSchemaValue:
        """Get the JSON schema for the PaginationSize type."""
        return {
            "type": "integer",
            "minimum": cls.MIN_VALUE,
            "maximum": cls.MAX_VALUE,
            "default": cls.DEFAULT_VALUE,
            "description": "Pagination size",
        }


class PaginationPageOffset(int):
    """Pagination page offset type."""

    MIN_VALUE: int = 0
    DEFAULT_VALUE: int = 0

    def __new__(cls, value: int) -> "PaginationPageOffset":
        """Create a new instance of PaginationPageOffset."""
        return super().__new__(cls, cls.validate(value))

    @classmethod
    def validate(cls, value: int) -> int:
        """Validate the pagination page offset."""
        if not cls.MIN_VALUE <= value:
            raise ValueError(f"Invalid pagination page offset: {value}")
        return value

    @classmethod
    def default(cls) -> "PaginationPageOffset":
        """Get the default pagination page offset."""
        return cls(cls.DEFAULT_VALUE)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,  # pylint: disable=unused-argument
        handler: GetCoreSchemaHandler,  # pylint: disable=unused-argument
    ) -> CoreSchema:
        """Get the core schema for the PaginationPageOffset type."""
        return core_schema.no_info_after_validator_function(cls, handler(int))

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: core_schema.CoreSchema,  # pylint: disable=redefined-outer-name,unused-argument
        handler: GetJsonSchemaHandler,  # pylint: disable=unused-argument
    ) -> JsonSchemaValue:
        """Get the JSON schema for the PaginationPageOffset type."""
        return {
            "type": "integer",
            "minimum": cls.MIN_VALUE,
            "default": cls.DEFAULT_VALUE,
            "description": "Pagination page offset",
        }
