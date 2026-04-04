"""Unit tests for query types and resolver (strict parsing, coercion, aggregation)."""

from __future__ import annotations

from typing import Any, cast

import pytest
from starlette.requests import Request

from fastapi_factory_utilities.core.utils.queries.abstracts import QueryAbstract
from fastapi_factory_utilities.core.utils.queries.enums import QueryFieldOperatorEnum, QuerySortDirectionEnum
from fastapi_factory_utilities.core.utils.queries.resolvers import QueryResolver
from fastapi_factory_utilities.core.utils.queries.types import (
    QueryField,
    QueryFieldName,
    QuerySort,
    RawQueryFieldName,
    RawQuerySort,
)


def _request(query_string: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": query_string.encode("utf-8"),
        }
    )


class _SampleQuery(QueryAbstract):
    """Concrete query model for :meth:`QueryResolver.from_model` tests."""

    label: str | None = None
    score: int | None = None


class TestQueryFieldExtract:
    """Tests for :meth:`QueryField.extract_field_and_operator_from_query_field`."""

    @pytest.mark.parametrize(
        ("raw", "expected_name", "expected_op"),
        [
            ("field1", "field1", QueryFieldOperatorEnum.EQ),
            ("object1.field1", "object1.field1", QueryFieldOperatorEnum.EQ),
            ("field1[gt]", "field1", QueryFieldOperatorEnum.GT),
            ("field1[lt]", "field1", QueryFieldOperatorEnum.LT),
            ("field1[gte]", "field1", QueryFieldOperatorEnum.GTE),
            ("field1[lte]", "field1", QueryFieldOperatorEnum.LTE),
            ("field1[eq]", "field1", QueryFieldOperatorEnum.EQ),
            ("field1[neq]", "field1", QueryFieldOperatorEnum.NEQ),
            ("field1[in]", "field1", QueryFieldOperatorEnum.IN),
            ("field1[nin]", "field1", QueryFieldOperatorEnum.NIN),
            ("field1[contains]", "field1", QueryFieldOperatorEnum.CONTAINS),
            ("field1[not_contains]", "field1", QueryFieldOperatorEnum.NOT_CONTAINS),
            ("field1[starts_with]", "field1", QueryFieldOperatorEnum.STARTS_WITH),
            ("field1[ends_with]", "field1", QueryFieldOperatorEnum.ENDS_WITH),
        ],
    )
    def test_operators(self, raw: str, expected_name: str, expected_op: QueryFieldOperatorEnum) -> None:
        """Each documented operator maps to the correct enum."""
        name, op = QueryField.extract_field_and_operator_from_query_field(raw)
        assert str(name) == expected_name
        assert op is expected_op

    @pytest.mark.parametrize(
        "bad",
        [
            "field[",
            "field]",
            "field[gt",
            "fieldgt]",
            "field[[gt]]",
            "field[badop]",
            "field[gt]extra",
        ],
    )
    def test_malformed_or_unknown_operator(self, bad: str) -> None:
        """Malformed bracket forms or unknown operators raise ``ValueError``."""
        with pytest.raises(ValueError):
            QueryField.extract_field_and_operator_from_query_field(bad)


class TestQueryFieldNameAndRaw:
    """Validation for field name types."""

    def test_query_field_name_validates_on_construction(self) -> None:
        """``QueryFieldName`` enforces length and character rules."""
        QueryFieldName("ab")
        with pytest.raises(ValueError):
            QueryFieldName("a")
        with pytest.raises(ValueError):
            QueryFieldName("bad name")

    def test_raw_query_field_name_rejects_invalid(self) -> None:
        """``RawQueryFieldName`` rejects invalid characters."""
        RawQueryFieldName("ok[in]")
        with pytest.raises(ValueError):
            RawQueryFieldName("no spaces")


class TestQuerySort:
    """Tests for sort parsing."""

    @pytest.mark.parametrize(
        ("raw", "name", "direction"),
        [
            ("name", "name", QuerySortDirectionEnum.ASCENDING),
            ("-name", "name", QuerySortDirectionEnum.DESCENDING),
            ("+age", "age", QuerySortDirectionEnum.ASCENDING),
        ],
    )
    def test_directions(self, raw: str, name: str, direction: QuerySortDirectionEnum) -> None:
        """Prefix sets ascending or descending; default is ascending."""
        qs = QuerySort(RawQuerySort(raw))
        assert str(qs.name) == name
        assert qs.direction is direction

    def test_raw_query_sort_invalid(self) -> None:
        """Invalid raw sort strings are rejected."""
        with pytest.raises(ValueError):
            RawQuerySort("+")


class TestCoerceValue:
    """Coercion is exercised via :meth:`QueryResolver.resolve`."""

    def test_scalar_and_list_int_via_resolver(self) -> None:
        """Scalar and ``[in]`` list values coerce to ``int``."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("num"), int)
        resolver.add_authorized_field(QueryFieldName("ids"), int)
        req = _request("num=42&ids[in]=1&ids[in]=2&ids[in]=3")
        resolver.resolve(req)
        fields = cast(dict[str, QueryField[Any]], resolver.fields)
        assert fields["num"].value == 42  # noqa: PLR2004
        assert fields["ids"].value == [1, 2, 3]

    def test_bool_via_resolver(self) -> None:
        """``true`` / ``0`` coerce to booleans."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("active"), bool)
        resolver.resolve(_request("active=true"))
        assert cast(dict[str, QueryField[Any]], resolver.fields)["active"].value is True
        r2 = QueryResolver()
        r2.add_authorized_field(QueryFieldName("active"), bool)
        r2.resolve(_request("active=0"))
        assert cast(dict[str, QueryField[Any]], r2.fields)["active"].value is False

    def test_invalid_int_raises_via_resolver(self) -> None:
        """Non-numeric string for ``int`` field raises ``ValueError``."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("count"), int)
        with pytest.raises(ValueError, match="Invalid integer"):
            resolver.resolve(_request("count=x"))


class TestQueryResolver:
    """Tests for :class:`QueryResolver`."""

    def test_in_collects_multiple_values(self) -> None:
        """Repeated ``field[in]=`` keys produce a list of strings then coercion."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("field1"), int)
        req = _request("field1[in]=1&field1[in]=2&field1[in]=3")
        resolver.resolve(req)
        fields = cast(dict[str, QueryField[Any]], resolver.fields)
        assert list(fields.keys()) == ["field1"]
        assert fields["field1"].operator is QueryFieldOperatorEnum.IN
        assert fields["field1"].value == [1, 2, 3]

    def test_non_in_last_value_wins(self) -> None:
        """Duplicate keys for non-list operators keep the last value."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("status"), str)
        req = _request("status=a&status=b")
        resolver.resolve(req)
        fields = cast(dict[str, QueryField[Any]], resolver.fields)
        assert fields["status"].value == "b"

    def test_range_two_raw_keys(self) -> None:
        """Same base field with two operators: :attr:`fields` is keyed by base name; last raw key wins."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("age"), int)
        req = _request("age[gt]=10&age[lt]=20")
        resolver.resolve(req)
        fields = cast(dict[str, QueryField[Any]], resolver.fields)
        assert set(fields) == {"age"}
        assert fields["age"].operator is QueryFieldOperatorEnum.LT
        assert fields["age"].value == 20  # noqa: PLR2004

    def test_unauthorized_strict_raises(self) -> None:
        """Strict mode raises for unknown base field names."""
        resolver = QueryResolver(raise_on_unauthorized_field=True)
        resolver.add_authorized_field(QueryFieldName("name"), str)
        req = _request("other=x")
        with pytest.raises(ValueError, match="Unauthorized field"):
            resolver.resolve(req)

    def test_unauthorized_permissive_drops(self) -> None:
        """Permissive mode omits unknown fields."""
        resolver = QueryResolver(raise_on_unauthorized_field=False)
        resolver.add_authorized_field(QueryFieldName("name"), str)
        req = _request("name=ok&other=x")
        resolver.resolve(req)
        fields = cast(dict[str, QueryField[Any]], resolver.fields)
        assert set(fields) == {"name"}
        assert fields["name"].value == "ok"

    def test_excluded_params_not_in_fields(self) -> None:
        """Pagination and sort keys are not returned as filters; ``sort`` fills :attr:`sorts`."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("name"), str)
        req = _request("page=2&page_size=5&sort=name&name=Ann")
        resolver.resolve(req)
        fields = cast(dict[str, QueryField[Any]], resolver.fields)
        assert set(fields) == {"name"}
        assert len(resolver.sorts) == 1
        assert str(resolver.sorts[0].name) == "name"
        assert resolver.sorts[0].direction is QuerySortDirectionEnum.ASCENDING

    def test_multiple_sort_preserves_order_and_direction(self) -> None:
        """Repeated ``sort`` parameters stay ordered; ``-`` / ``+`` set direction."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("name"), str)
        resolver.add_authorized_field(QueryFieldName("age"), int)
        req = _request("sort=-name&sort=%2Bage")
        resolver.resolve(req)
        assert len(resolver.sorts) == 2  # noqa: PLR2004
        assert str(resolver.sorts[0].name) == "name"
        assert resolver.sorts[0].direction is QuerySortDirectionEnum.DESCENDING
        assert str(resolver.sorts[1].name) == "age"
        assert resolver.sorts[1].direction is QuerySortDirectionEnum.ASCENDING

    def test_unauthorized_sort_strict_raises(self) -> None:
        """Strict mode raises for sort tokens whose field is not authorized."""
        resolver = QueryResolver(raise_on_unauthorized_field=True)
        resolver.add_authorized_field(QueryFieldName("name"), str)
        req = _request("sort=other")
        with pytest.raises(ValueError, match="Unauthorized sort field"):
            resolver.resolve(req)

    def test_unauthorized_sort_permissive_drops_token(self) -> None:
        """Permissive mode keeps authorized sort tokens and drops unknown ones."""
        resolver = QueryResolver(raise_on_unauthorized_field=False)
        resolver.add_authorized_field(QueryFieldName("name"), str)
        req = _request("sort=name&sort=other")
        resolver.resolve(req)
        assert len(resolver.sorts) == 1
        assert str(resolver.sorts[0].name) == "name"

    def test_from_model_registers_types(self) -> None:
        """``from_model`` reads field names and unwraps optional annotations."""
        resolver = QueryResolver().from_model(_SampleQuery)
        req = _request("label=hi&score=7&page=1&page_size=10")
        resolver.resolve(req)
        fields = cast(dict[str, QueryField[Any]], resolver.fields)
        assert fields["label"].value == "hi"
        assert fields["score"].value == 7  # noqa: PLR2004

    def test_coerce_failure_raises(self) -> None:
        """Invalid value for declared ``int`` field raises ``ValueError``."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("count"), int)
        req = _request("count=notint")
        with pytest.raises(ValueError, match="Invalid integer"):
            resolver.resolve(req)
