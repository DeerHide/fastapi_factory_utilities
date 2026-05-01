"""Dynamic query filter model builder driven by :class:`ApiField` searchable markers."""

from __future__ import annotations

from typing import Annotated, Any, cast, get_args, get_origin, get_type_hints

from pydantic import BaseModel, ConfigDict, Field, create_model
from pydantic.fields import FieldInfo

from fastapi_factory_utilities.core.utils.pydantic_path_fields import nested_basemodel_for_annotation

from .markers import ApiField, has_searchable_flag
from .query_abstract import QueryAbstract, QueryFilterNestedAbstract
from .query_types import QueryField


def _strip_apifield_to_value_type(hint: Any) -> Any:
    """Return ``T`` from ``Annotated[T, ..., ApiField(searchable=True), ...]``."""
    ann: Any = hint
    while get_origin(ann) is Annotated:
        args = get_args(ann)
        if not args:
            break
        metadata = args[1:]
        if any(isinstance(m, ApiField) for m in metadata):
            return args[0]
        ann = args[0]
    return ann


def _field_to_create_model_spec(field_info: FieldInfo, annotation: Any) -> tuple[Any, Any]:
    """Map a Pydantic v2 :class:`FieldInfo` to a :func:`create_model` field spec."""
    if field_info.is_required():
        return (annotation, ...)
    if field_info.default_factory is not None:
        return (annotation, Field(default_factory=field_info.default_factory))
    return (annotation, field_info.default)


def _container_nested_annotation(field_info: FieldInfo, inner_model: type[QueryFilterNestedAbstract]) -> Any:
    """Pick wrapper type for a nested filter segment (preserve optionality of the container)."""
    if field_info.is_required():
        return inner_model
    return inner_model | None


class SearchableEntity(BaseModel):
    """Searchable entity that dynamically builds query filter models.

    Examples:
        Flat fields::

            class ProductEntity(SearchableEntity):
                id: Annotated[int, SearchableField]
                name: Annotated[str, SearchableField]


            class ProductQueryFilter(ProductEntity.build_query_filter_model()):
                pass

        Nested entity::

            class AddressEntity(SearchableEntity):
                city: Annotated[str, SearchableField]


            class UserEntity(SearchableEntity):
                name: Annotated[str, SearchableField]
                address: Annotated[AddressEntity, SearchableField]


            UserQueryFilter = UserEntity.build_query_filter_model()

        Optional nested container::

            class UserEntityOptional(SearchableEntity):
                name: Annotated[str, SearchableField]
                address: Annotated[AddressEntity | None, SearchableField] = None
    """

    @classmethod
    def build_query_filter_model(cls) -> type[QueryAbstract]:
        """Build the root query filter model (subclasses :class:`QueryAbstract`)."""
        return cast(type[QueryAbstract], cls._build_query_filter_model(as_root=True, building=frozenset()))

    @classmethod
    def build_nested_query_filter_model(
        cls, *, building: frozenset[type[SearchableEntity]]
    ) -> type[QueryFilterNestedAbstract]:
        """Build the nested filter segment model (no pagination or sort fields)."""
        return cast(
            type[QueryFilterNestedAbstract],
            cls._build_query_filter_model(as_root=False, building=building),
        )

    @classmethod
    def _build_query_filter_model(
        cls,
        *,
        as_root: bool,
        building: frozenset[type[SearchableEntity]],
    ) -> type[QueryAbstract] | type[QueryFilterNestedAbstract]:
        """Build a query filter model or a nested segment model."""
        if cls in building:
            msg = f"Circular SearchableEntity graph: {cls.__name__!r} appears in its own nested searchable chain."
            raise ValueError(msg)
        next_building = building | frozenset({cls})

        model_name = f"{cls.__name__}QueryFilter" if as_root else f"{cls.__name__}QueryFilterSegment"

        hints: dict[str, Any] = get_type_hints(cls, include_extras=True)

        annotated_searchable: list[str] = []
        for field_name, hint in hints.items():
            if get_origin(hint) is Annotated:
                metadata = get_args(hint)[1:]
                if has_searchable_flag(metadata):
                    annotated_searchable.append(field_name)

        searchable = list(dict.fromkeys(annotated_searchable))
        model_fields_map: dict[str, FieldInfo] = dict(cls.model_fields.items())
        fields: dict[str, tuple[Any, Any]] = {}

        for field_name in searchable:
            try:
                field_info = model_fields_map[field_name]
            except KeyError as exc:
                msg = f"Field {field_name!r} is not defined on {cls.__name__}."
                raise ValueError(msg) from exc

            stripped = _strip_apifield_to_value_type(hints[field_name])
            nested_cls = nested_basemodel_for_annotation(
                stripped,
                exclude=(QueryAbstract, QueryFilterNestedAbstract),
            )

            if nested_cls is not None:
                if not issubclass(nested_cls, SearchableEntity):
                    msg = (
                        f"Field {field_name!r} on {cls.__name__} nests type {nested_cls.__name__!r}; "
                        "nested searchable fields must use a type that subclasses SearchableEntity."
                    )
                    raise ValueError(msg) from None
                inner_model = nested_cls.build_nested_query_filter_model(building=next_building)
                inner_ann = _container_nested_annotation(field_info, inner_model)
                fields[field_name] = _field_to_create_model_spec(field_info, inner_ann)
            else:
                value_type = stripped
                fields[field_name] = (QueryField[value_type] | None, None)  # type: ignore[valid-type]

        if as_root:
            model = create_model(
                model_name,
                __config__=ConfigDict(extra="ignore", arbitrary_types_allowed=True),
                __base__=QueryAbstract,
                **cast(dict[str, Any], fields),
            )
        else:
            model = create_model(  # type: ignore[misc]
                model_name,
                __base__=QueryFilterNestedAbstract,  # type: ignore[arg-type]
                **cast(dict[str, Any], fields),
            )

        model.__doc__ = (
            f"Query filter for {cls.__name__}" if as_root else f"Nested query filter segment for {cls.__name__}"
        )
        return model
