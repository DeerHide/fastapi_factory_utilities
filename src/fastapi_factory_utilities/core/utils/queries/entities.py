"""Entities for the query utilities."""

from typing import Any, ClassVar, Self, cast, get_type_hints

from pydantic import BaseModel, ConfigDict, create_model, model_validator

from fastapi_factory_utilities.core.utils.pydantic_path_fields import (
    raise_if_dotted_path_prefix_conflict,
    resolve_leaf_annotation_and_field_info,
)

from .types import QueryField


class QueryFilterAbstract(BaseModel):
    """Query filter abstract."""

    @model_validator(mode="after")
    def validate_query_filter(self) -> Self:
        """Validate the query filter.

        Rules:
        - Ensure all attributes are optional.
        - Ensure all attributes are QueryField[T] | None type.
        """
        valid_field_names = frozenset(type(self).model_fields.keys())
        for field in self.model_fields_set:
            if field not in valid_field_names:
                raise ValueError(f"Field {field} is not a valid searchable field.")
            value = getattr(self, field)
            if value is not None and not isinstance(value, QueryField):
                raise ValueError(f"Field {field} is not a QueryField[T] | None type.")
        return self


class SearchableEntity(BaseModel):
    """Searcheable entity."""

    SEARCHABLE_FIELDS: ClassVar[list[str]] = []

    @classmethod
    def build_query_filter_model(cls) -> type[QueryFilterAbstract]:
        """Build the query filter model.

        Returns:
            type[QueryFilterAbstract]: The query filter model.

        Raises:
            ValueError: If a field is not a valid searchable field.
        """
        model_name: str = f"{cls.__name__}QueryFilter"
        hints: dict[str, Any] = get_type_hints(cls)
        searchable = list(cls.SEARCHABLE_FIELDS)
        raise_if_dotted_path_prefix_conflict(searchable)
        fields: dict[str, tuple[Any, Any]] = {}

        for field in searchable:
            if "." in field:
                resolve_leaf_annotation_and_field_info(
                    cls,
                    field,
                    include_extras=False,
                )
            else:
                try:
                    hints[field]
                except KeyError as exc:
                    raise ValueError(f"Field {field} is not a valid searchable field.") from exc
            fields[field] = (QueryField[Any] | None, None)

        model = create_model(
            model_name,
            __config__=ConfigDict(extra="ignore", arbitrary_types_allowed=True),
            __base__=QueryFilterAbstract,
            **cast(Any, fields),
        )
        model.__doc__ = f"Query filter for {cls.__name__}"
        return model
