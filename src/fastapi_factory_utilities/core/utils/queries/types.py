"""Provides the types for the query utilities."""

import re
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, GetCoreSchemaHandler, GetJsonSchemaHandler, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

from .enums import QueryFieldOperatorEnum, QuerySortDirectionEnum


class QueryFieldName(str):
    """Query field name type."""

    MIN_LENGTH: int = 2
    MAX_LENGTH: int = 128

    REGEX: ClassVar[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9_\.\-]+$")

    @classmethod
    def validate(cls, value: str) -> str:
        """Validate the query field name."""
        if not cls.MIN_LENGTH <= len(value) <= cls.MAX_LENGTH:
            raise ValueError(f"Query field name must be between {cls.MIN_LENGTH} and {cls.MAX_LENGTH} characters long.")
        if not cls.REGEX.match(value):
            raise ValueError(
                "Query field name must contain only alphanumeric characters, underscores, hyphens, and dots."
            )
        return value

    def __new__(cls, value: str) -> "QueryFieldName":
        """Create a new instance of QueryFieldName."""
        return super().__new__(cls, cls.validate(value))

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: Any, _handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:  # pylint: disable=invalid-name
        """Get the core schema for the QueryFieldName type."""
        return core_schema.no_info_after_validator_function(
            cls, core_schema.str_schema(min_length=cls.MIN_LENGTH, max_length=cls.MAX_LENGTH, pattern=cls.REGEX.pattern)
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: core_schema.CoreSchema,  # pylint: disable=redefined-outer-name
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Get the JSON schema for the QueryFieldName type."""
        field_schema = handler(core_schema)
        field_schema.update(type="string", description="Query field name")
        return field_schema


class RawQueryFieldName(str):
    """Raw query field type."""

    MIN_LENGTH: int = 2
    MAX_LENGTH: int = 128

    REGEX: ClassVar[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9_\-\.\[\]]+$")

    @classmethod
    def validate(cls, value: str) -> str:
        """Validate the raw query field."""
        if not cls.MIN_LENGTH <= len(value) <= cls.MAX_LENGTH:
            raise ValueError(f"Raw query field must be between {cls.MIN_LENGTH} and {cls.MAX_LENGTH} characters long.")
        if not cls.REGEX.match(value):
            raise ValueError(
                "Raw query field must contain only alphanumeric characters,"
                " underscores, hyphens, dots, and square brackets."
            )
        return value

    def __new__(cls, value: str) -> "RawQueryFieldName":
        """Create a new instance of RawQueryFieldName."""
        return super().__new__(cls, cls.validate(value))

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source: Any,  # pylint: disable=invalid-name
        _handler: GetCoreSchemaHandler,  # pylint: disable=invalid-name
    ) -> core_schema.CoreSchema:
        """Get the core schema for the RawQueryFieldName type."""
        return core_schema.no_info_after_validator_function(cls, core_schema.str_schema())

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: core_schema.CoreSchema,  # pylint: disable=invalid-name
        _handler: GetJsonSchemaHandler,  # pylint: disable=invalid-name
    ) -> JsonSchemaValue:
        """Get the JSON schema for the RawQueryFieldName type."""
        return {"type": "string", "description": "Raw query field"}


T = TypeVar("T")


class QueryFieldOperation(BaseModel, Generic[T]):
    """Query field operation type."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    operator: QueryFieldOperatorEnum
    value: T


class QueryField(BaseModel, Generic[T]):
    """Query field type."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    name: QueryFieldName
    operations: list[QueryFieldOperation[T]] = Field(default_factory=list)

    @staticmethod
    def extract_field_and_operator_from_query_field(query_field: str) -> tuple[QueryFieldName, QueryFieldOperatorEnum]:
        """Parse a raw query parameter name into base field name and operator."""
        if "[" in query_field:
            if query_field.count("[") != 1 or not query_field.endswith("]"):
                raise ValueError("Malformed bracket operator in query field name.")
            field_part, rest = query_field.split("[", 1)
            operator_str = rest[:-1].strip()
            field_stripped = field_part.strip()
            if not field_stripped or not operator_str:
                raise ValueError("Empty field name or operator in bracket form.")
            try:
                operator = QueryFieldOperatorEnum(operator_str)
            except ValueError as exc:
                raise ValueError(f"Unknown query field operator: {operator_str!r}.") from exc
            return QueryFieldName(field_stripped), operator
        if "]" in query_field:
            raise ValueError("Malformed query field name: stray ']'.")
        return QueryFieldName(query_field.strip()), QueryFieldOperatorEnum.EQ


class RawQuerySort(str):
    """Raw query sort type."""

    MIN_LENGTH: int = 2
    MAX_LENGTH: int = 128

    REGEX: ClassVar[re.Pattern[str]] = re.compile(r"^[(\-|+)]?[a-zA-Z0-9_\-\.]+$")

    @classmethod
    def validate(cls, value: str) -> str:
        """Validate the raw query sort."""
        if not cls.MIN_LENGTH <= len(value) <= cls.MAX_LENGTH:
            raise ValueError(f"Raw query sort must be between {cls.MIN_LENGTH} and {cls.MAX_LENGTH} characters long.")
        if not cls.REGEX.match(value):
            raise ValueError(
                "Raw query sort must contain only alphanumeric characters, underscores, hyphens, and dots."
            )
        return value

    def __new__(cls, value: str) -> "RawQuerySort":
        """Create a new instance of RawQuerySort."""
        return super().__new__(cls, cls.validate(value))

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source: Any,  # pylint: disable=invalid-name
        _handler: GetCoreSchemaHandler,  # pylint: disable=invalid-name
    ) -> core_schema.CoreSchema:
        """Get the core schema for the RawQuerySort type."""
        return core_schema.no_info_after_validator_function(cls, core_schema.str_schema())

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: core_schema.CoreSchema,  # pylint: disable=invalid-name
        _handler: GetJsonSchemaHandler,  # pylint: disable=invalid-name
    ) -> JsonSchemaValue:
        """Get the JSON schema for the RawQuerySort type."""
        return {"type": "string", "description": "Raw query sort"}


class QuerySort(BaseModel):
    """Query sort type."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    name: QueryFieldName
    direction: QuerySortDirectionEnum

    @staticmethod
    def _raw_sort_to_parts(raw: str) -> dict[str, Any]:
        if raw.startswith("-"):
            return {"name": QueryFieldName(raw[1:]), "direction": QuerySortDirectionEnum.DESCENDING}
        if raw.startswith("+"):
            return {"name": QueryFieldName(raw[1:]), "direction": QuerySortDirectionEnum.ASCENDING}
        return {"name": QueryFieldName(raw), "direction": QuerySortDirectionEnum.ASCENDING}

    @model_validator(mode="before")
    @classmethod
    def _from_raw_sort(cls, data: Any) -> Any:
        if isinstance(data, RawQuerySort):
            return cls._raw_sort_to_parts(str(data))
        if isinstance(data, str):
            return cls._raw_sort_to_parts(data)
        return data
