"""Unit tests for ODM query builder (Mongo filter + Beanie find kwargs)."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from beanie import SortDirection
from pydantic import Field, ValidationError

from fastapi_factory_utilities.core.plugins.odm_plugin.queries import ODMFindQuery, ODMQueryBuilder
from fastapi_factory_utilities.core.utils.api import (
    PaginationPageOffset,
    PaginationSize,
    QueryAbstract,
    QueryField,
    QueryFieldName,
    QueryFieldOperation,
    QueryFieldOperatorEnum,
    QuerySort,
    RawQuerySort,
)


class _UuidIdQuery(QueryAbstract):
    """Query model with typed UUID ``id`` (matches realm-isolated filters)."""

    id: QueryField[UUID] | None = Field(default=None)


class _BaseQuery(QueryAbstract):
    """Concrete query model for builder tests."""

    title: str | None = None
    id: QueryField[Any] | None = Field(default=None)
    count: QueryField[int] | None = Field(default=None)
    label: QueryField[str] | None = Field(default=None)
    flex: QueryField[Any] | None = Field(default=None)


_Builder = ODMQueryBuilder[_BaseQuery]


def _q(**kwargs: object) -> _BaseQuery:
    """Build query with defaults for pagination/sort."""
    data: dict[str, object] = {"page": 0, "page_size": 10, "sorts": []}
    data.update(kwargs)
    return _BaseQuery.model_validate(data)


def test_build_empty_filter_and_sort_none() -> None:
    """No filter fields yields empty match; no sorts yields sort None."""
    built = _Builder().set_query_filter(_q()).build()
    assert not built.mongo_filter
    assert built.sort is None
    assert built.skip == 0
    assert built.limit == 10  # noqa: PLR2004


def test_pagination_skip_limit() -> None:
    """Offset and limit follow QueryAbstract."""
    built = _Builder().set_query_filter(_q(page=PaginationPageOffset(3), page_size=PaginationSize(25))).build()
    assert built.skip == 75  # noqa: PLR2004
    assert built.limit == 25  # noqa: PLR2004


def test_plain_scalar_field_becomes_eq() -> None:
    """get_fields wraps bare values as EQ QueryField."""
    built = _Builder().set_query_filter(_q(title="hello")).build()
    assert built.mongo_filter == {"title": "hello"}


def test_id_field_maps_to_mongo_primary_key() -> None:
    """Filter field ``id`` becomes ``_id`` in the match document (Beanie storage)."""
    field = QueryField(
        name=QueryFieldName("id"),
        operations=[QueryFieldOperation(operator=QueryFieldOperatorEnum.EQ, value="pk-value")],
    )
    built = _Builder().set_query_filter(_q(id=field)).build()
    assert built.mongo_filter == {"_id": "pk-value"}


def test_id_field_in_operator_uses_primary_key_path() -> None:
    """Merged and operator RHS shapes keep ``_id`` as the path key."""
    field = QueryField(
        name=QueryFieldName("id"),
        operations=[QueryFieldOperation(operator=QueryFieldOperatorEnum.IN, value=["a", "b"])],
    )
    built = _Builder().set_query_filter(_q(id=field)).build()
    assert built.mongo_filter == {"_id": {"$in": ["a", "b"]}}


def test_query_field_uuid_in_accepts_uuid_list() -> None:
    """``QueryField[UUID]`` allows a list of UUIDs for ``in`` (Pydantic + ODM path)."""
    u1, u2 = uuid4(), uuid4()
    field = QueryField(
        name=QueryFieldName("id"),
        operations=[QueryFieldOperation(operator=QueryFieldOperatorEnum.IN, value=[u1, u2])],
    )
    q = _UuidIdQuery.model_validate({"page": 0, "page_size": 10, "sorts": [], "id": field})
    built = ODMQueryBuilder[_UuidIdQuery]().set_query_filter(q).build()
    assert built.mongo_filter == {"_id": {"$in": [u1, u2]}}


def test_query_field_uuid_nin_accepts_uuid_list() -> None:
    """``QueryField[UUID]`` allows a list of UUIDs for ``nin``."""
    u1 = uuid4()
    field = QueryField(
        name=QueryFieldName("id"),
        operations=[QueryFieldOperation(operator=QueryFieldOperatorEnum.NIN, value=[u1])],
    )
    q = _UuidIdQuery.model_validate({"page": 0, "page_size": 10, "sorts": [], "id": field})
    built = ODMQueryBuilder[_UuidIdQuery]().set_query_filter(q).build()
    assert built.mongo_filter == {"_id": {"$nin": [u1]}}


def test_query_field_uuid_in_accepts_scalar_uuid() -> None:
    """``IN`` with a single UUID still validates on ``QueryField[UUID]``."""
    u = uuid4()
    field = QueryField(
        name=QueryFieldName("id"),
        operations=[QueryFieldOperation(operator=QueryFieldOperatorEnum.IN, value=u)],
    )
    q = _UuidIdQuery.model_validate({"page": 0, "page_size": 10, "sorts": [], "id": field})
    built = ODMQueryBuilder[_UuidIdQuery]().set_query_filter(q).build()
    assert built.mongo_filter == {"_id": {"$in": [u]}}


def test_query_field_uuid_eq_rejects_list() -> None:
    """Operators other than ``in`` / ``nin`` must not use a list ``value``."""
    u = uuid4()
    with pytest.raises(ValidationError, match="list value is only allowed"):
        QueryFieldOperation[UUID](operator=QueryFieldOperatorEnum.EQ, value=[u])


@pytest.mark.parametrize(
    ("operator", "value", "expected_rhs"),
    [
        (QueryFieldOperatorEnum.EQ, "v", "v"),
        (QueryFieldOperatorEnum.NEQ, 1, {"$ne": 1}),
        (QueryFieldOperatorEnum.GT, 2, {"$gt": 2}),
        (QueryFieldOperatorEnum.LT, 3, {"$lt": 3}),
        (QueryFieldOperatorEnum.GTE, 4, {"$gte": 4}),
        (QueryFieldOperatorEnum.LTE, 5, {"$lte": 5}),
        (QueryFieldOperatorEnum.IN, [1, 2], {"$in": [1, 2]}),
        (QueryFieldOperatorEnum.NIN, ["a"], {"$nin": ["a"]}),
    ],
)
def test_single_operation_operators(
    operator: QueryFieldOperatorEnum,
    value: object,
    expected_rhs: object,
) -> None:
    """Each comparison/list operator maps to the expected Mongo RHS."""
    field = QueryField(
        name=QueryFieldName("flex"),
        operations=[QueryFieldOperation(operator=operator, value=value)],
    )
    built = _Builder().set_query_filter(_q(flex=field)).build()
    assert built.mongo_filter == {"flex": expected_rhs}


def test_in_coerces_scalar_to_single_element_list() -> None:
    """IN with a scalar becomes a one-element $in list."""
    field = QueryField(
        name=QueryFieldName("count"),
        operations=[QueryFieldOperation(operator=QueryFieldOperatorEnum.IN, value=7)],
    )
    built = _Builder().set_query_filter(_q(count=field)).build()
    assert built.mongo_filter == {"count": {"$in": [7]}}


def test_contains_starts_ends_regex() -> None:
    """String match operators use escaped regex and case-insensitive option."""
    contains = QueryField(
        name=QueryFieldName("label"),
        operations=[QueryFieldOperation(operator=QueryFieldOperatorEnum.CONTAINS, value="a+b")],
    )
    built_c = _Builder().set_query_filter(_q(label=contains)).build()
    assert built_c.mongo_filter["label"]["$options"] == "i"
    assert built_c.mongo_filter["label"]["$regex"] == "a\\+b"

    starts = QueryField(
        name=QueryFieldName("label"),
        operations=[QueryFieldOperation(operator=QueryFieldOperatorEnum.STARTS_WITH, value="pre")],
    )
    built_s = _Builder().set_query_filter(_q(label=starts)).build()
    assert built_s.mongo_filter["label"]["$regex"] == "^pre"
    assert built_s.mongo_filter["label"]["$options"] == "i"

    ends = QueryField(
        name=QueryFieldName("label"),
        operations=[QueryFieldOperation(operator=QueryFieldOperatorEnum.ENDS_WITH, value="suf")],
    )
    built_e = _Builder().set_query_filter(_q(label=ends)).build()
    assert built_e.mongo_filter["label"]["$regex"] == "suf$"
    assert built_e.mongo_filter["label"]["$options"] == "i"


def test_not_contains_uses_not_regex() -> None:
    """NOT_CONTAINS uses $not with regex."""
    field = QueryField(
        name=QueryFieldName("label"),
        operations=[QueryFieldOperation(operator=QueryFieldOperatorEnum.NOT_CONTAINS, value="x")],
    )
    built = _Builder().set_query_filter(_q(label=field)).build()
    assert built.mongo_filter["label"] == {"$not": {"$regex": "x", "$options": "i"}}


def test_merge_gt_lt_same_path() -> None:
    """Multiple comparison ops on one field merge into one subdocument."""
    field = QueryField(
        name=QueryFieldName("count"),
        operations=[
            QueryFieldOperation(operator=QueryFieldOperatorEnum.GT, value=5),
            QueryFieldOperation(operator=QueryFieldOperatorEnum.LT, value=20),
        ],
    )
    built = _Builder().set_query_filter(_q(count=field)).build()
    assert built.mongo_filter == {"count": {"$gt": 5, "$lt": 20}}


def test_eq_plus_comparison_uses_and() -> None:
    """EQ combined with operators on the same path becomes $and."""
    field = QueryField(
        name=QueryFieldName("count"),
        operations=[
            QueryFieldOperation(operator=QueryFieldOperatorEnum.EQ, value=10),
            QueryFieldOperation(operator=QueryFieldOperatorEnum.GT, value=5),
        ],
    )
    built = _Builder().set_query_filter(_q(count=field)).build()
    assert built.mongo_filter == {"$and": [{"count": 10}, {"count": {"$gt": 5}}]}


def test_regex_plus_comparison_uses_and() -> None:
    """Regex RHS cannot merge with $gt; use $and."""
    ops: list[QueryFieldOperation[Any]] = [
        QueryFieldOperation(operator=QueryFieldOperatorEnum.GT, value=5),
        QueryFieldOperation(operator=QueryFieldOperatorEnum.CONTAINS, value="a"),
    ]
    field: QueryField[Any] = QueryField(name=QueryFieldName("flex"), operations=ops)
    built = _Builder().set_query_filter(_q(flex=field)).build()
    assert "$and" in built.mongo_filter
    clauses = built.mongo_filter["$and"]
    assert {"flex": {"$gt": 5}} in clauses
    assert any("flex" in c and "$regex" in c["flex"] for c in clauses)


def test_multiple_paths_implicit_and() -> None:
    """Different field paths appear as sibling keys."""
    count_field = QueryField(
        name=QueryFieldName("count"),
        operations=[QueryFieldOperation(operator=QueryFieldOperatorEnum.GTE, value=1)],
    )
    built = _Builder().set_query_filter(_q(title="hi", count=count_field)).build()
    assert built.mongo_filter == {"title": "hi", "count": {"$gte": 1}}


def test_sort_mapping() -> None:
    """QuerySort maps to Beanie SortDirection and field order is preserved."""
    sorts = [
        QuerySort.model_validate(RawQuerySort("title")),
        QuerySort.model_validate(RawQuerySort("-count")),
    ]
    built = _Builder().set_query_filter(_q(sorts=sorts)).build()
    assert built.sort == [
        ("title", SortDirection.ASCENDING),
        ("count", SortDirection.DESCENDING),
    ]


def test_build_filter_only_alias() -> None:
    """build_filter_only matches build().mongo_filter."""
    field = QueryField(
        name=QueryFieldName("count"),
        operations=[QueryFieldOperation(operator=QueryFieldOperatorEnum.EQ, value=3)],
    )
    b = _Builder().set_query_filter(_q(count=field))
    assert b.build_filter_only() == b.build().mongo_filter == {"count": 3}


def test_odm_find_query_is_frozen_dataclass() -> None:
    """ODMFindQuery exposes the planned attributes."""
    fq = ODMFindQuery(mongo_filter={"a": 1}, skip=0, limit=5, sort=None)
    assert fq.mongo_filter == {"a": 1}
    assert fq.skip == 0
    assert fq.limit == 5  # noqa: PLR2004
    assert fq.sort is None
