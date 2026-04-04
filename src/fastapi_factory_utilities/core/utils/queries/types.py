"""Provides the types for the query utilities."""

import re
from typing import Any, ClassVar, Generic, TypeVar, override

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
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


class QueryField(Generic[T]):
    """Query field type."""

    __hash__ = None  # type: ignore[assignment]

    @classmethod
    def extract_field_and_operator_from_query_field(
        cls, query_field: str
    ) -> tuple[QueryFieldName, QueryFieldOperatorEnum]:
        """Extract the field and operator from the query field."""
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

    def __init__(self, raw_query_field: RawQueryFieldName, value: T) -> None:
        """Initialize the QueryField."""
        self._name: QueryFieldName
        self._operator: QueryFieldOperatorEnum
        self._value: T
        self._name, self._operator = self.extract_field_and_operator_from_query_field(query_field=raw_query_field)
        self._value = value

    @property
    def name(self) -> QueryFieldName:
        """Get the name of the query field."""
        return self._name

    @property
    def operator(self) -> QueryFieldOperatorEnum:
        """Get the operator of the query field."""
        return self._operator

    @property
    def value(self) -> T:
        """Get the value of the query field."""
        return self._value

    def __str__(self) -> str:
        """Get the string representation of the query field."""
        return f"{self.name}[{self.operator}]={self.value}"

    def __repr__(self) -> str:
        """Get the representation of the query field."""
        return f"QueryField(name={self.name}, operator={self.operator}, value={self.value})"

    def __eq__(self, other: object) -> bool:
        """Return whether another field matches name, operator, and value."""
        if not isinstance(other, QueryField):
            return NotImplemented
        return self.name == other.name and self.operator == other.operator and self.value == other.value

    @override
    def __dict__(self) -> dict[str, Any]:  # type: ignore[override]
        """Get the dictionary representation of the query field."""
        return {
            "name": self.name,
            "operator": self.operator,
            "value": self.value,
        }

    @classmethod
    def _serialize_query_field(cls, instance: "QueryField[T]") -> dict[str, Any]:
        """Serialize ``QueryField`` to a JSON-compatible dict for Pydantic / FastAPI."""
        return {
            "name": str(instance.name),
            "operator": instance.operator.value,
            "value": instance.value,
        }

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source: Any,  # pylint: disable=invalid-name
        _handler: GetCoreSchemaHandler,  # pylint: disable=invalid-name
    ) -> core_schema.CoreSchema:
        """Core schema: accept ``QueryField`` instances or dicts; serialize to a JSON object."""
        ser_schema = core_schema.plain_serializer_function_ser_schema(
            cls._serialize_query_field,
            return_schema=core_schema.dict_schema(
                keys_schema=core_schema.str_schema(),
                values_schema=core_schema.any_schema(),
            ),
        )
        from_dict = core_schema.no_info_after_validator_function(
            lambda value: cls(RawQueryFieldName(value["name"]), value["value"]),
            core_schema.dict_schema(
                keys_schema=core_schema.str_schema(),
                values_schema=core_schema.any_schema(),
            ),
            serialization=ser_schema,
        )
        return core_schema.union_schema(
            [
                core_schema.is_instance_schema(cls, serialization=ser_schema),
                from_dict,
            ],
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: core_schema.CoreSchema,  # pylint: disable=invalid-name
        _handler: GetJsonSchemaHandler,  # pylint: disable=invalid-name
    ) -> JsonSchemaValue:
        """Get the JSON schema for the ``QueryField`` type."""
        return {
            "type": "object",
            "description": "Query field.",
            "properties": {
                "name": {"type": "string", "description": "Query field name."},
                "operator": {
                    "type": "string",
                    "description": "Query field operator.",
                    "enum": [operator.value for operator in QueryFieldOperatorEnum],
                },
                "value": {"description": "Filter value."},
            },
            "required": ["name", "operator", "value"],
        }


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


class QuerySort:
    """Query sort type."""

    @classmethod
    def extract_field_and_order_from_query_sort(cls, query_sort: str) -> tuple[QueryFieldName, QuerySortDirectionEnum]:
        """Extract the field and order from the query sort."""
        if query_sort.startswith("-"):
            return QueryFieldName(query_sort[1:]), QuerySortDirectionEnum.DESCENDING
        if query_sort.startswith("+"):
            return QueryFieldName(query_sort[1:]), QuerySortDirectionEnum.ASCENDING
        return QueryFieldName(query_sort), QuerySortDirectionEnum.ASCENDING

    def __init__(self, value: RawQuerySort) -> None:
        """Initialize the QuerySort."""
        self._name: QueryFieldName
        self._direction: QuerySortDirectionEnum
        self._name, self._direction = self.extract_field_and_order_from_query_sort(query_sort=value)

    @property
    def name(self) -> QueryFieldName:
        """Get the name of the query sort."""
        return self._name

    @property
    def direction(self) -> QuerySortDirectionEnum:
        """Get the direction of the query sort."""
        return self._direction

    def __str__(self) -> str:
        """Get the string representation of the query sort."""
        return f"{self.name}[{self.direction}]"

    def __repr__(self) -> str:
        """Get the representation of the query sort."""
        return f"QuerySort(name={self.name}, direction={self.direction})"

    def __eq__(self, other: object) -> bool:
        """Return whether another sort has the same field name and direction."""
        if not isinstance(other, QuerySort):
            return NotImplemented
        return self.name == other.name and self.direction == other.direction

    def __hash__(self) -> int:
        """Hash by field name and direction."""
        return hash((self.name, self.direction))

    @override
    def __dict__(self) -> dict[str, Any]:  # type: ignore[override]
        """Get the dictionary representation of the query sort."""
        return {"name": self.name, "direction": self.direction}

    @classmethod
    def _serialize_query_sort(cls, instance: "QuerySort") -> dict[str, Any]:
        """Serialize ``QuerySort`` to a JSON-compatible dict for Pydantic / FastAPI."""
        return {
            "name": str(instance.name),
            "direction": instance.direction.value,
        }

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source: Any,  # pylint: disable=invalid-name
        _handler: GetCoreSchemaHandler,  # pylint: disable=invalid-name
    ) -> core_schema.CoreSchema:
        """Core schema: accept ``QuerySort`` instances, raw sort strings, or serialized dicts."""

        def from_dict(value: dict[str, Any]) -> QuerySort:
            name = value["name"]
            direction = value["direction"]
            if direction in (QuerySortDirectionEnum.DESCENDING, QuerySortDirectionEnum.DESCENDING.value):
                return cls(RawQuerySort(f"-{name}"))
            return cls(RawQuerySort(str(name)))

        ser_schema = core_schema.plain_serializer_function_ser_schema(
            cls._serialize_query_sort,
            return_schema=core_schema.dict_schema(
                keys_schema=core_schema.str_schema(),
                values_schema=core_schema.any_schema(),
            ),
        )
        from_str = core_schema.no_info_after_validator_function(
            lambda v: cls(RawQuerySort(v)),
            core_schema.str_schema(),
            serialization=ser_schema,
        )
        from_dict_schema = core_schema.no_info_after_validator_function(
            from_dict,
            core_schema.dict_schema(
                keys_schema=core_schema.str_schema(),
                values_schema=core_schema.any_schema(),
            ),
            serialization=ser_schema,
        )
        return core_schema.union_schema(
            [
                core_schema.is_instance_schema(cls, serialization=ser_schema),
                from_str,
                from_dict_schema,
            ],
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: core_schema.CoreSchema,  # pylint: disable=invalid-name
        _handler: GetJsonSchemaHandler,  # pylint: disable=invalid-name
    ) -> JsonSchemaValue:
        """Get the JSON schema for the QuerySort type."""
        return {
            "type": "object",
            "description": "Query sort list.",
            "properties": {
                "name": {"type": "string", "description": "Query sort name."},
                "direction": {
                    "type": "string",
                    "description": "Query sort direction.",
                    "enum": [direction.value for direction in QuerySortDirectionEnum],
                },
            },
            "required": ["name", "direction"],
        }
