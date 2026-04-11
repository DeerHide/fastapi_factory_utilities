"""Provides resolvers for the query utilities."""

import uuid
from types import NoneType, UnionType
from typing import Annotated, Any, ClassVar, Self, Union, get_args, get_origin

from fastapi import Request
from pydantic import AliasChoices, BaseModel

from .abstracts import QueryAbstract
from .enums import QueryFieldOperatorEnum
from .types import QueryField, QueryFieldName, QueryFieldOperation, QuerySort, RawQueryFieldName, RawQuerySort


def _annotation_to_field_type(annotation: Any) -> Any:  # noqa: PLR0911
    """Pick a coercion target from a field annotation (``type``, ``typing.NewType``, etc.)."""
    if annotation is None:
        return str
    while get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]
    origin_qf = get_origin(annotation)
    args_qf = get_args(annotation)
    if origin_qf is not None and isinstance(origin_qf, type) and issubclass(origin_qf, QueryField) and args_qf:
        return _annotation_to_field_type(args_qf[0])
    if isinstance(annotation, type) and issubclass(annotation, QueryField):
        meta = getattr(annotation, "__pydantic_generic_metadata__", None) or {}
        gargs = meta.get("args") or ()
        if gargs:
            return _annotation_to_field_type(gargs[0])
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is not None and args and (origin is Union or origin is UnionType):
        non_none = tuple(a for a in args if a is not NoneType)
        if len(non_none) == 1:
            return _annotation_to_field_type(non_none[0])
        return str
    # typing.NewType is a callable, not a ``type``; _coerce_scalar uses ``__supertype__``.
    if getattr(annotation, "__supertype__", None) is not None:
        return annotation
    if isinstance(annotation, type):
        return annotation
    return str


def _coerce_scalar(item: str, field_type: Any) -> Any:  # noqa: PLR0911
    """Coerce a single query string to ``field_type``."""
    if field_type is str:
        return item
    if field_type is int:
        try:
            return int(item, 10)
        except ValueError as exc:
            raise ValueError(f"Invalid integer query value: {item!r}.") from exc
    if field_type is float:
        try:
            return float(item)
        except ValueError as exc:
            raise ValueError(f"Invalid float query value: {item!r}.") from exc
    if field_type is bool:
        lower = item.lower()
        if lower in ("true", "1", "yes"):
            return True
        if lower in ("false", "0", "no"):
            return False
        raise ValueError(f"Invalid boolean query value: {item!r}.")
    if field_type is uuid.UUID:
        try:
            return uuid.UUID(item)
        except ValueError as exc:
            raise ValueError(f"Invalid UUID query value: {item!r}.") from exc
    supertype = getattr(field_type, "__supertype__", None)
    if supertype is not None:
        # ``typing.NewType`` (any supertype we already support: str, int, UUID, …).
        coerced = _coerce_scalar(item, supertype)
        return field_type(coerced)
    raise TypeError(f"Unsupported field_type for query coercion: {field_type!r}.")


def _coerce_value(value: str | list[str], field_type: type) -> Any:
    """Coerce a scalar or list (``in`` / ``nin``) of query strings."""
    if isinstance(value, list):
        return [_coerce_scalar(v, field_type) for v in value]
    return _coerce_scalar(value, field_type)


def _unwrap_structure_annotation(annotation: Any) -> Any:
    """Strip ``Annotated``, single-branch optional unions, and ``QueryField[T]`` down to ``T``."""
    if annotation is None:
        return None
    ann: Any = annotation
    while get_origin(ann) is Annotated:
        ann = get_args(ann)[0]
    origin_qf = get_origin(ann)
    args_qf = get_args(ann)
    if origin_qf is not None and isinstance(origin_qf, type) and issubclass(origin_qf, QueryField) and args_qf:
        return _unwrap_structure_annotation(args_qf[0])
    if isinstance(ann, type) and issubclass(ann, QueryField):
        meta = getattr(ann, "__pydantic_generic_metadata__", None) or {}
        gargs = meta.get("args") or ()
        if gargs:
            return _unwrap_structure_annotation(gargs[0])
    origin = get_origin(ann)
    args = get_args(ann)
    if origin is not None and args and (origin is Union or origin is UnionType):
        non_none = tuple(a for a in args if a is not NoneType)
        if len(non_none) == 1:
            return _unwrap_structure_annotation(non_none[0])
    return ann


def _string_tokens_from_validation_alias(alias: Any) -> list[str]:
    """Flatten ``validation_alias`` to string keys usable in query parameter names."""
    if alias is None:
        return []
    if isinstance(alias, str):
        return [alias]
    if isinstance(alias, AliasChoices):
        out: list[str] = []
        for choice in alias.choices:
            out.extend(_string_tokens_from_validation_alias(choice))
        return out
    return []


def _populate_by_name(model_cls: type[BaseModel]) -> bool:
    """Whether the model accepts input by Python field name as well as alias."""
    cfg = getattr(model_cls, "model_config", None)
    if cfg is None:
        return False
    return bool(cfg.get("populate_by_name", False))


def _query_name_segments_for_field(model_cls: type[BaseModel], field_name: str, field_info: Any) -> list[str]:
    """Segments for one model field (before joining with parent prefix)."""
    alias_strings = _string_tokens_from_validation_alias(field_info.validation_alias)
    ordered_unique = list(dict.fromkeys(alias_strings))
    if not ordered_unique:
        return [field_name]
    if _populate_by_name(model_cls) and field_name not in ordered_unique:
        return [*ordered_unique, field_name]
    return ordered_unique


def _nested_filter_model_type(annotation: Any) -> type[BaseModel] | None:
    """Return a nested ``BaseModel`` (not :class:`QueryAbstract`) to walk, or ``None`` for a leaf."""
    ann = _unwrap_structure_annotation(annotation)
    if ann is None:
        return None
    if isinstance(ann, type) and issubclass(ann, BaseModel) and not issubclass(ann, QueryAbstract):
        return ann
    origin = get_origin(ann)
    args = get_args(ann) if origin is not None else ()
    if origin is not None and args and (origin is Union or origin is UnionType):
        candidates: list[type[BaseModel]] = []
        for a in args:
            if a is NoneType:
                continue
            inner = _unwrap_structure_annotation(a)
            if isinstance(inner, type) and issubclass(inner, BaseModel) and not issubclass(inner, QueryAbstract):
                candidates.append(inner)
        if len(candidates) == 1:
            return candidates[0]
        return None
    return None


class QueryResolver:
    """Resolver for the query."""

    EXCLUDED_FIELDS: ClassVar[list[str]] = ["page", "page_size", "sort", "sorts"]

    def __init__(self, raise_on_unauthorized_field: bool = True) -> None:
        """Initialize the QueryFilterResolver.

        Args:
            raise_on_unauthorized_field (bool): Whether to raise an exception if an unauthorized field is provided.
        """
        self._raise_on_unauthorized_field: bool = raise_on_unauthorized_field
        self._authorized_fields: dict[QueryFieldName, type] = {}

        self._fields: dict[QueryFieldName, QueryField[Any]] = {}
        self._sorts: list[QuerySort] = []

    def add_authorized_field(self, field_name: QueryFieldName, field_type: Any = str) -> Self:
        """Add an authorized field.

        Args:
            field_name (QueryFieldName): The name of the field.
            field_type: The type or ``typing.NewType`` wrapper used to coerce query values. Defaults to ``str``.

        Raises:
            ValueError: If the field is already authorized.
        """
        if field_name in self._authorized_fields:
            raise ValueError(f"Field {field_name} already authorized")
        self._authorized_fields[field_name] = field_type
        return self

    def from_model(self, model: QueryAbstract | type[QueryAbstract]) -> Self:
        """Register authorized fields from a :class:`QueryAbstract` subclass.

        Authorized names match **query string** keys (after bracket parsing), not only Python
        attribute names:

        - **Nested filter models**: a field whose type is a :class:`pydantic.BaseModel` subclass
          other than :class:`QueryAbstract` is walked recursively. Each leaf registers as
          ``parent.child...`` using the parent field's name segments and the child's segments,
          joined with ``.``. Cycles in the model graph are skipped to avoid infinite recursion.
        - **Aliases**: for each field, string :attr:`~pydantic.fields.FieldInfo.validation_alias`
          values (including inside :class:`~pydantic.AliasChoices`) define extra segments at that
          level. If the model has ``populate_by_name=True``, the Python field name is also
          registered when aliases are present.
        - **Unions**: if a union has exactly one non-optional nested filter model branch, that
          model is walked; otherwise the field is treated as a leaf (coercion follows the union
          rules in :func:`_annotation_to_field_type`).
        - **Dynamic maps** (``dict``, ``Mapping``, ambiguous unions, etc.) are not expanded; use
          ``validation_alias`` on a leaf field or :meth:`add_authorized_field` for dotted keys that
          are not structurally enumerable.

        Args:
            model (QueryAbstract | type[QueryAbstract]): The model class or instance to read fields from.
        """
        cls = model if isinstance(model, type) else type(model)
        self._register_authorized_from_model_class(cls, prefix=(), entered=frozenset())
        return self

    def _register_authorized_from_model_class(
        self,
        model_cls: type[BaseModel],
        *,
        prefix: tuple[str, ...],
        entered: frozenset[type],
    ) -> None:
        if model_cls in entered:
            return
        entered_here = entered | {model_cls}
        excluded = frozenset(self.EXCLUDED_FIELDS)
        for field_name, field_info in model_cls.model_fields.items():
            if field_name in excluded:
                continue
            segments = _query_name_segments_for_field(model_cls, field_name, field_info)
            nested_cls = _nested_filter_model_type(field_info.annotation)
            if nested_cls is not None:
                for seg in segments:
                    self._register_authorized_from_model_class(
                        nested_cls,
                        prefix=(*prefix, seg),
                        entered=entered_here,
                    )
            else:
                field_type = _annotation_to_field_type(field_info.annotation)
                for seg in segments:
                    full = ".".join((*prefix, seg)) if prefix else seg
                    self.add_authorized_field(field_name=QueryFieldName(full), field_type=field_type)

    @staticmethod
    def _aggregate_raw_query_params(query_params: Any) -> dict[str, str | list[str]]:
        """Merge duplicate keys: ``in`` / ``nin`` collect values; others last-wins."""
        excluded = frozenset(QueryResolver.EXCLUDED_FIELDS)
        buckets: dict[str, list[str]] = {}
        key_meta: dict[str, QueryFieldOperatorEnum] = {}
        for raw_key, raw_value in query_params.multi_items():
            if raw_key in excluded:
                continue
            validated_key = str(RawQueryFieldName(raw_key))
            _, operator = QueryField.extract_field_and_operator_from_query_field(validated_key)
            key_meta[validated_key] = operator
            buckets.setdefault(validated_key, []).append(raw_value)

        aggregated: dict[str, str | list[str]] = {}
        for key, values in buckets.items():
            operator = key_meta[key]
            if operator in (QueryFieldOperatorEnum.IN, QueryFieldOperatorEnum.NIN):
                aggregated[key] = values
            else:
                aggregated[key] = values[-1]
        return aggregated

    @staticmethod
    def _collect_sort_query_values(query_params: Any) -> list[str]:
        """Return ``sort`` query values in request order (repeated keys preserved)."""
        return [raw_value for raw_key, raw_value in query_params.multi_items() if raw_key == "sort"]

    def resolve(self, request: Request) -> None:
        """Resolve filter fields and sort tokens from the request query string.

        Populates :attr:`fields` keyed by base field name (e.g. ``age`` for ``age[gt]``). Each
        value is a :class:`QueryField` whose :attr:`~QueryField.operations` list collects every
        distinct raw parameter name for that base field, in first-seen request order (e.g.
        ``age[gt]`` and ``age[lt]`` both appear as separate operations). Values are coerced using
        the type from :meth:`add_authorized_field`. Duplicate raw keys for operators other than
        ``in`` / ``nin`` keep the last value (see :meth:`_aggregate_raw_query_params`).

        Populates :attr:`sorts` from repeated ``sort`` parameters, in order, each parsed as a
        :class:`QuerySort`. Sort field names must appear in the authorized field set unless the
        resolver was constructed with ``raise_on_unauthorized_field=False``, in which case
        unknown sort tokens are skipped.

        Args:
            request (Request): The request.
        """
        raw_fields = self._aggregate_raw_query_params(request.query_params)

        fields: dict[QueryFieldName, QueryField[Any]] = {}
        for raw_key, aggregated_value in raw_fields.items():
            base_name, operator = QueryField.extract_field_and_operator_from_query_field(
                str(RawQueryFieldName(raw_key))
            )
            if base_name not in self._authorized_fields:
                if self._raise_on_unauthorized_field:
                    raise ValueError(f"Unauthorized field: {base_name}")
                continue
            field_type = self._authorized_fields[base_name]
            coerced = _coerce_value(aggregated_value, field_type)
            op = QueryFieldOperation(operator=operator, value=coerced)
            existing = fields.get(base_name)
            if existing is None:
                fields[base_name] = QueryField(name=base_name, operations=[op])
            else:
                fields[base_name] = existing.model_copy(
                    update={"operations": [*existing.operations, op]},
                )

        self._fields = fields

        sorts: list[QuerySort] = []
        for raw_sort in self._collect_sort_query_values(request.query_params):
            qs = QuerySort.model_validate(RawQuerySort(raw_sort))
            if qs.name not in self._authorized_fields:
                if self._raise_on_unauthorized_field:
                    raise ValueError(f"Unauthorized sort field: {qs.name}")
                continue
            sorts.append(qs)
        self._sorts = sorts

    @property
    def fields(self) -> dict[QueryFieldName, QueryField[Any]]:
        """Get the fields."""
        return self._fields

    @property
    def sorts(self) -> list[QuerySort]:
        """Get the sorts."""
        return self._sorts
