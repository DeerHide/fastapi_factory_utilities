"""Entities for the query utilities."""

from typing import Any, ClassVar, cast, get_type_hints

from pydantic import BaseModel, ConfigDict, create_model

from fastapi_factory_utilities.core.utils.pydantic_path_fields import (
    raise_if_dotted_path_prefix_conflict,
    resolve_leaf_annotation_and_field_info,
)

from .abstracts import QueryAbstract
from .types import QueryField


class SearchableEntity(BaseModel):
    """Searcheable entity."""

    SEARCHABLE_FIELDS: ClassVar[list[str]] = []

    @classmethod
    def build_query_filter_model(cls) -> type[QueryAbstract]:
        """Build the query filter model.

        Returns:
            type[QueryAbstract]: The query filter model.

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
            __base__=QueryAbstract,
            **cast(Any, fields),
        )
        model.__doc__ = f"Query filter for {cls.__name__}"
        return model
