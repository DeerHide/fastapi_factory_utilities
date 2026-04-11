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

from .enums import QueryFieldOperatorEnum
from .types import QueryField, QueryFieldName, QueryFieldOperation, QuerySort


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

        Keys match each :class:`QueryField` :attr:`~QueryField.name` (e.g. dotted paths from the
        resolver). Nested filter models (:class:`pydantic.BaseModel` subclasses other than
        :class:`QueryAbstract`) are walked recursively.

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
                result[value.name] = value
            elif isinstance(value, BaseModel) and not isinstance(value, QueryAbstract):
                result.update(QueryAbstract._nested_query_fields_from_model(value))
            else:
                result[QueryFieldName(key)] = QueryField(
                    name=QueryFieldName(key),
                    operations=[
                        QueryFieldOperation(operator=QueryFieldOperatorEnum.EQ, value=value),
                    ],
                )
        return result

    @staticmethod
    def _nested_query_fields_from_model(nested: BaseModel) -> dict[QueryFieldName, QueryField[Any]]:
        """Collect :class:`QueryField` instances from a nested filter model by ``QueryField.name``."""
        acc: dict[QueryFieldName, QueryField[Any]] = {}
        for sub_key in nested.model_fields_set:
            sub_val = getattr(nested, sub_key, None)
            if sub_val is None:
                continue
            if isinstance(sub_val, QueryField):
                acc[sub_val.name] = sub_val
            elif isinstance(sub_val, BaseModel) and not isinstance(sub_val, QueryAbstract):
                acc.update(QueryAbstract._nested_query_fields_from_model(sub_val))
        return acc


class QueryFilterNestedAbstract(BaseModel, ABC):
    """Base for nested filter groups (dotted query keys under a parent field).

    Use for hand-authored nested segments on :class:`QueryAbstract`, or rely on
    :meth:`SearchableEntity.build_query_filter_model` which builds inner types that subclass this
    class. Unlike :class:`QueryAbstract`, this type has no pagination or sort fields.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
