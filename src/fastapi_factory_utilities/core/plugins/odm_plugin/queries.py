"""Queries for the ODM plugin.

Translates :class:`~fastapi_factory_utilities.core.utils.api.QueryAbstract`
instances into MongoDB match documents and Beanie ``find`` keyword arguments.

Merge rules for multiple :class:`~fastapi_factory_utilities.core.utils.api.QueryFieldOperation`
on the same path:

- Comparison operators (``$gt``, ``$lt``, ``$gte``, ``$lte``, ``$ne``) merge into one
  subdocument when keys do not conflict.
- ``$in`` / ``$nin`` merge with comparisons or each other only when keys do not conflict;
  otherwise clauses are combined with ``$and``.
- ``$not`` (from ``not_contains``) and equality (implicit ``EQ``) do not merge with other
  shapes; they produce separate conjuncts under ``$and``.
"""

from __future__ import annotations

import re
from abc import ABC
from dataclasses import dataclass
from typing import Any, Generic, Self, TypeVar

from beanie import SortDirection

from fastapi_factory_utilities.core.utils.api import (
    QueryAbstract,
    QueryFieldOperatorEnum,
    QuerySort,
    QuerySortDirectionEnum,
)

GenericQueryFilter = TypeVar("GenericQueryFilter", bound=QueryAbstract)


def _op_to_rhs(operator: QueryFieldOperatorEnum, value: Any) -> Any:  # noqa: PLR0911
    """Map a single operation to a MongoDB field RHS (scalar or operator document)."""
    if operator is QueryFieldOperatorEnum.EQ:
        return value
    if operator is QueryFieldOperatorEnum.NEQ:
        return {"$ne": value}
    if operator is QueryFieldOperatorEnum.GT:
        return {"$gt": value}
    if operator is QueryFieldOperatorEnum.LT:
        return {"$lt": value}
    if operator is QueryFieldOperatorEnum.GTE:
        return {"$gte": value}
    if operator is QueryFieldOperatorEnum.LTE:
        return {"$lte": value}
    if operator is QueryFieldOperatorEnum.IN:
        lst: list[Any] = list(value) if isinstance(value, list) else [value]
        return {"$in": lst}
    if operator is QueryFieldOperatorEnum.NIN:
        lst_nin: list[Any] = list(value) if isinstance(value, list) else [value]
        return {"$nin": lst_nin}

    escaped = re.escape(str(value))
    if operator is QueryFieldOperatorEnum.CONTAINS:
        return {"$regex": escaped, "$options": "i"}
    if operator is QueryFieldOperatorEnum.NOT_CONTAINS:
        return {"$not": {"$regex": escaped, "$options": "i"}}
    if operator is QueryFieldOperatorEnum.STARTS_WITH:
        return {"$regex": f"^{escaped}", "$options": "i"}
    if operator is QueryFieldOperatorEnum.ENDS_WITH:
        return {"$regex": f"{escaped}$", "$options": "i"}
    raise ValueError(f"Unsupported query field operator: {operator!r}")


def _mongo_field_path(name: str) -> str:
    """Map query model field names to MongoDB document paths (Beanie PK is ``_id``)."""
    return "_id" if name == "id" else name


_COMPARISON_KEYS = frozenset({"$gt", "$lt", "$gte", "$lte", "$ne"})
_ARRAY_KEYS = frozenset({"$in", "$nin"})


def _operator_dict_kind(d: dict[str, Any]) -> str:
    """Classify operator RHS for safe merging (same-kind only)."""
    keys = set(d)
    if "$not" in keys:
        return "not"
    if "$regex" in keys or "$options" in keys:
        return "regex"
    if keys & _ARRAY_KEYS:
        return "array"
    if keys <= _COMPARISON_KEYS:
        return "comparison"
    return "mixed"


def _try_merge_operator_dicts(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any] | None:
    """Merge two operator RHS dicts if kinds match and keys do not disagree."""
    if _operator_dict_kind(a) != _operator_dict_kind(b):
        return None
    if _operator_dict_kind(a) in ("not", "regex"):
        return None
    for key in set(a) & set(b):
        if a[key] != b[key]:
            return None
    return {**a, **b}


def _merge_values_for_path(path: str, rhss: list[Any]) -> dict[str, Any]:  # noqa: PLR0911
    """Combine several RHS values for the same MongoDB path into one filter fragment."""
    if not rhss:
        return {}
    if len(rhss) == 1:
        return {path: rhss[0]}

    scalars = [r for r in rhss if not isinstance(r, dict)]
    dicts: list[dict[str, Any]] = [r for r in rhss if isinstance(r, dict)]

    merged_dict: dict[str, Any] | None = None
    for d in dicts:
        if merged_dict is None:
            merged_dict = dict(d)
            continue
        trial = _try_merge_operator_dicts(merged_dict, d)
        if trial is None:
            return {"$and": [{path: r} for r in rhss]}
        merged_dict = trial

    if len(scalars) > 1:
        return {"$and": [{path: s} for s in scalars]}
    if len(scalars) == 1 and merged_dict is not None:
        return {"$and": [{path: scalars[0]}, {path: merged_dict}]}
    if len(scalars) == 1:
        return {path: scalars[0]}
    assert merged_dict is not None
    return {path: merged_dict}


def _build_mongo_filter(query_filter: QueryAbstract) -> dict[str, Any]:
    fields = query_filter.get_fields()
    if not fields:
        return {}

    path_to_rhss: dict[str, list[Any]] = {}
    for field in fields.values():
        path = _mongo_field_path(str(field.name))
        for op in field.operations:
            path_to_rhss.setdefault(path, []).append(_op_to_rhs(op.operator, op.value))

    fragments: list[dict[str, Any]] = []
    for path, rhss in path_to_rhss.items():
        fragments.append(_merge_values_for_path(path, rhss))

    return _merge_root_fragments(fragments)


def _merge_root_fragments(fragments: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge per-path fragments into one match document (implicit AND across paths)."""
    direct: dict[str, Any] = {}
    and_chunks: list[dict[str, Any]] = []

    for frag in fragments:
        if not frag:
            continue
        if set(frag) == {"$and"}:
            and_chunks.extend(frag["$and"])
            continue
        for key, val in frag.items():
            if key == "$and":
                and_chunks.extend(val)
            elif key in direct:
                and_chunks.append({key: direct.pop(key)})
                and_chunks.append({key: val})
            else:
                direct[key] = val

    if not and_chunks:
        return direct
    if direct:
        return {"$and": [{k: v} for k, v in direct.items()] + and_chunks}
    if len(and_chunks) == 1:
        return and_chunks[0]
    return {"$and": and_chunks}


def _sort_to_beanie(sorts: list[QuerySort]) -> list[tuple[str, SortDirection]]:
    result: list[tuple[str, SortDirection]] = []
    for s in sorts:
        direction = (
            SortDirection.DESCENDING if s.direction is QuerySortDirectionEnum.DESCENDING else SortDirection.ASCENDING
        )
        result.append((str(s.name), direction))
    return result


@dataclass(frozen=True, slots=True)
class ODMFindQuery:
    """MongoDB match document and Beanie ``find`` pagination/sort kwargs."""

    mongo_filter: dict[str, Any]
    skip: int
    limit: int
    sort: list[tuple[str, SortDirection]] | None


class ODMQueryBuilder(ABC, Generic[GenericQueryFilter]):
    """Build MongoDB filters and Beanie find parameters from :class:`QueryAbstract`."""

    def __init__(self) -> None:
        """Initialize the ODM query builder."""
        self._query_filter: GenericQueryFilter | None = None

    def set_query_filter(self, query_filter: GenericQueryFilter) -> Self:
        """Set the query filter."""
        self._query_filter = query_filter
        return self

    def build(self) -> ODMFindQuery:
        """Build the MongoDB query and find kwargs."""
        assert self._query_filter is not None, "Query filter is not set"
        qf = self._query_filter
        mongo_filter = _build_mongo_filter(qf)
        sorts = qf.sorts
        sort_arg: list[tuple[str, SortDirection]] | None = _sort_to_beanie(sorts) if sorts else None
        return ODMFindQuery(
            mongo_filter=mongo_filter,
            skip=qf.offset,
            limit=int(qf.page_size),
            sort=sort_arg,
        )

    def build_filter_only(self) -> dict[str, Any]:
        """Return only the MongoDB match document."""
        return self.build().mongo_filter
