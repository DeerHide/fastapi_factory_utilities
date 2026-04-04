"""Provides resolvers for the query utilities."""

from types import NoneType, UnionType
from typing import Any, ClassVar, Self, Union, get_args, get_origin

from fastapi import Request

from .abstracts import QueryAbstract
from .enums import QueryFieldOperatorEnum
from .types import QueryField, QueryFieldName, QuerySort, RawQueryFieldName, RawQuerySort


def _annotation_to_field_type(annotation: Any) -> type:
    """Pick a concrete ``type`` from a field annotation for coercion defaults."""
    if annotation is None:
        return str
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is not None and args and (origin is Union or origin is UnionType):
        non_none = tuple(a for a in args if a is not NoneType)
        if len(non_none) == 1 and isinstance(non_none[0], type):
            return non_none[0]
        return str
    if isinstance(annotation, type):
        return annotation
    return str


def _coerce_scalar(item: str, field_type: type) -> Any:
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
    raise TypeError(f"Unsupported field_type for query coercion: {field_type!r}.")


def _coerce_value(value: str | list[str], field_type: type) -> Any:
    """Coerce a scalar or list (``in`` / ``nin``) of query strings."""
    if isinstance(value, list):
        return [_coerce_scalar(v, field_type) for v in value]
    return _coerce_scalar(value, field_type)


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

    def add_authorized_field(self, field_name: QueryFieldName, field_type: type = str) -> Self:
        """Add an authorized field.

        Args:
            field_name (QueryFieldName): The name of the field.
            field_type (type): The type of the field. Defaults to str.

        Raises:
            ValueError: If the field is already authorized.
        """
        if field_name in self._authorized_fields:
            raise ValueError(f"Field {field_name} already authorized")
        self._authorized_fields[field_name] = field_type
        return self

    def from_model(self, model: QueryAbstract | type[QueryAbstract]) -> Self:
        """Register authorized fields from a :class:`QueryAbstract` subclass.

        Args:
            model (QueryAbstract | type[QueryAbstract]): The model class or instance to read fields from.
        """
        cls = model if isinstance(model, type) else type(model)
        for field_name, field_info in cls.model_fields.items():
            if field_name in self.EXCLUDED_FIELDS:
                continue
            field_type = _annotation_to_field_type(field_info.annotation)
            self.add_authorized_field(field_name=QueryFieldName(field_name), field_type=field_type)
        return self

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
        value is a :class:`QueryField` built from the last matching raw key for that base name.
        Values are coerced using the type from :meth:`add_authorized_field`. Duplicate raw keys
        for operators other than ``in`` / ``nin`` keep the last value.

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
            field = QueryField(raw_query_field=RawQueryFieldName(raw_key), value=aggregated_value)
            base_name: QueryFieldName = field.name
            if base_name not in self._authorized_fields:
                if self._raise_on_unauthorized_field:
                    raise ValueError(f"Unauthorized field: {base_name}")
                continue
            field_type = self._authorized_fields[base_name]
            coerced = _coerce_value(aggregated_value, field_type)
            fields[base_name] = QueryField(raw_query_field=RawQueryFieldName(raw_key), value=coerced)

        self._fields = fields

        sorts: list[QuerySort] = []
        for raw_sort in self._collect_sort_query_values(request.query_params):
            qs = QuerySort(RawQuerySort(raw_sort))
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
