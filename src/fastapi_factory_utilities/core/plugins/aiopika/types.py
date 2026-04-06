"""Provides the types for the Aiopika plugin."""

import re
from typing import Any, ClassVar, Self

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema


class PartStr(str):
    """Routing key part string.

    Topic-style wildcard ``*`` (single segment) is allowed for listener routing patterns.
    """

    pattern: ClassVar[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9\-\_]+$")
    min_length: ClassVar[int] = 3
    max_length: ClassVar[int] = 32
    WILDCARD: ClassVar[str] = "*"

    @classmethod
    def validate(cls, value: str) -> str:
        """Validate the routing key part string."""
        if value == cls.WILDCARD:
            return value
        if not cls.pattern.match(value):
            raise ValueError("Routing key part string must match the pattern.")
        if len(value) < cls.min_length:
            raise ValueError("Routing key part string must be at least 3 characters long.")
        if len(value) > cls.max_length:
            raise ValueError("Routing key part string must be at most 32 characters long.")
        return value

    def __new__(cls, value: str) -> Self:
        """Create a new routing key part string."""
        return super().__new__(cls, cls.validate(value))

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source: type[Any],  # pylint: disable=unused-argument, invalid-name
        _handler: GetCoreSchemaHandler,  # pylint: disable=unused-argument, invalid-name
    ) -> core_schema.CoreSchema:
        """Get the core schema for the RoutingKeyPartStr type."""
        return core_schema.no_info_after_validator_function(cls, core_schema.str_schema())

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: core_schema.CoreSchema,  # pylint: disable=redefined-outer-name
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Get the JSON schema for the RoutingKeyPartStr type."""
        field_schema = handler(core_schema)
        field_schema.update(type="string", format="routing-key-part")
        return field_schema


class AbstractName(str):
    """Abstract name (dotted segments; ``*`` allowed per segment for topic patterns)."""

    PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9\-\_\.\*]+$")
    MIN_LENGTH: ClassVar[int] = 3
    MAX_LENGTH: ClassVar[int] = 255

    @classmethod
    def validate(cls, value: str) -> str:
        """Validate the routing key."""
        if not cls.PATTERN.match(value):
            raise ValueError("Routing key must match the pattern.")
        if len(value) < cls.MIN_LENGTH:
            raise ValueError(f"Routing key must be at least {cls.MIN_LENGTH} characters long.")
        if len(value) > cls.MAX_LENGTH:
            raise ValueError(f"Routing key must be at most {cls.MAX_LENGTH} characters long.")
        return value

    def __new__(cls, value: str) -> Self:
        """Create a new routing key."""
        return super().__new__(cls, cls.validate(value))

    def __init__(self, value: str) -> None:
        """Initialize the routing key."""
        self._value: str = self.validate(value)
        self._parts: list[PartStr] = [PartStr(part) for part in self._value.split(".")]

    def __str__(self) -> str:
        """Get the string representation of the routing key."""
        return self._value

    def __eq__(self, other: object) -> bool:
        """Compare two names for equality."""
        if not isinstance(other, AbstractName):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        """Get the hash of the routing key."""
        return hash(self._value)

    def __len__(self) -> int:
        """Get the length of the routing key."""
        return len(self._value)

    def __contains__(self, item: object) -> bool:
        """Check if the routing key contains the item."""
        if not isinstance(item, str):
            return False
        return item in self._value

    def get_parts(self) -> list[PartStr]:
        """Get the parts of the routing key."""
        return self._parts

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source: type[Any],  # pylint: disable=unused-argument, invalid-name
        _handler: GetCoreSchemaHandler,  # pylint: disable=unused-argument, invalid-name
    ) -> core_schema.CoreSchema:
        """Get the core schema for the RoutingKey type."""
        return core_schema.no_info_after_validator_function(cls, core_schema.str_schema())

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: core_schema.CoreSchema,  # pylint: disable=redefined-outer-name
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Get the JSON schema for the RoutingKey type."""
        field_schema = handler(core_schema)
        field_schema.update(type="string", format="routing-key-part")
        return field_schema


class RoutingKey(AbstractName):
    """Routing key."""


class QueueName(AbstractName):
    """Queue name."""


class ExchangeName(AbstractName):
    """Exchange name."""
