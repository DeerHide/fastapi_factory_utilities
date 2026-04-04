"""Provides the abstract classes for the query utilities.

Examples of Usage:

class ResourceQueryModel(QueryAbstract):

    name: QueryField[str] | None = Field(default=None, min_length=2, max_length=128)
    age: QueryField[int] | None = Field(default=None, gt=0, lt=100)
    email: QueryField[str] | None = Field(default=None, format="email")

"""

from abc import ABC
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, computed_field

from fastapi_factory_utilities.core.utils.paginations import PaginationPageOffset, PaginationSize, resolve_offset

from .types import QueryField, QueryFieldName, QuerySort, RawQueryFieldName


class QueryAbstract(BaseModel, ABC):
    """Abstract base class for the query utilities."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    page: PaginationPageOffset = Field(default=PaginationPageOffset.default())
    page_size: PaginationSize = Field(default=PaginationSize.default())

    sorts: list[QuerySort] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def offset(self) -> int:
        """Get the offset."""
        return resolve_offset(page_offset=self.page, page_size=self.page_size)

    def get_fields(self) -> dict[QueryFieldName, QueryField[Any]]:
        """Get the fields.

        Returns:
            dict[QueryFieldName, QueryField[Any]]: The fields as a dictionary of query fields.
        """
        excluded = frozenset({"page", "page_size", "sorts"})
        result: dict[QueryFieldName, QueryField[Any]] = {}
        for key in self.model_fields_set:
            if key in excluded:
                continue
            value = getattr(self, key)
            if value is None:
                continue
            if isinstance(value, QueryField):
                result[QueryFieldName(key)] = value
            else:
                result[QueryFieldName(key)] = QueryField(raw_query_field=RawQueryFieldName(key), value=value)
        return result
