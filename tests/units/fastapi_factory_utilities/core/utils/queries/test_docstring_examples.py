"""Unit tests mirroring examples in ``queries.__init__`` module docstring."""

from __future__ import annotations

from typing import Any

import pytest
from starlette.requests import Request

from fastapi_factory_utilities.core.utils.queries.enums import QueryFieldOperatorEnum, QuerySortDirectionEnum
from fastapi_factory_utilities.core.utils.queries.resolvers import QueryResolver
from fastapi_factory_utilities.core.utils.queries.types import QueryField, QueryFieldName


def _request(query_string: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/resources",
            "headers": [],
            "query_string": query_string.encode("utf-8"),
        }
    )


def _resolver_with_filter_fields() -> QueryResolver:
    """Authorize ``field1`` and dotted ``object1.field1`` as in the docstring."""
    resolver = QueryResolver()
    resolver.add_authorized_field(QueryFieldName("field1"), str)
    resolver.add_authorized_field(QueryFieldName("object1.field1"), str)
    return resolver


class TestDocstringFilterExamples:
    """Each row matches a filtering line in ``queries.__init__`` docstring."""

    @pytest.mark.parametrize(
        ("query", "expected_base_name", "expected_op", "expected_value"),
        [
            # GET /api/v1/resources?field1=value1
            ("field1=value1", "field1", QueryFieldOperatorEnum.EQ, "value1"),
            # GET /api/v1/resources?object1.field1=value1
            ("object1.field1=value1", "object1.field1", QueryFieldOperatorEnum.EQ, "value1"),
            # GET /api/v1/resources?field1[gt]=value1
            ("field1[gt]=value1", "field1", QueryFieldOperatorEnum.GT, "value1"),
            # GET /api/v1/resources?field1[lt]=value1
            ("field1[lt]=value1", "field1", QueryFieldOperatorEnum.LT, "value1"),
            # GET /api/v1/resources?field1[gte]=value1
            ("field1[gte]=value1", "field1", QueryFieldOperatorEnum.GTE, "value1"),
            # GET /api/v1/resources?field1[lte]=value1
            ("field1[lte]=value1", "field1", QueryFieldOperatorEnum.LTE, "value1"),
            # GET /api/v1/resources?field1[eq]=value1
            ("field1[eq]=value1", "field1", QueryFieldOperatorEnum.EQ, "value1"),
            # GET /api/v1/resources?field1[neq]=value1
            ("field1[neq]=value1", "field1", QueryFieldOperatorEnum.NEQ, "value1"),
            # GET ... field1[in]=value1&field1[in]=value2&field1[in]=value3
            (
                "field1[in]=value1&field1[in]=value2&field1[in]=value3",
                "field1",
                QueryFieldOperatorEnum.IN,
                ["value1", "value2", "value3"],
            ),
            # GET ... field1[nin]=value1&field1[nin]=value2&field1[nin]=value3
            (
                "field1[nin]=value1&field1[nin]=value2&field1[nin]=value3",
                "field1",
                QueryFieldOperatorEnum.NIN,
                ["value1", "value2", "value3"],
            ),
            # GET /api/v1/resources?field1[contains]=value1
            ("field1[contains]=value1", "field1", QueryFieldOperatorEnum.CONTAINS, "value1"),
            # GET /api/v1/resources?field1[not_contains]=value1
            ("field1[not_contains]=value1", "field1", QueryFieldOperatorEnum.NOT_CONTAINS, "value1"),
            # GET /api/v1/resources?field1[starts_with]=value1
            ("field1[starts_with]=value1", "field1", QueryFieldOperatorEnum.STARTS_WITH, "value1"),
            # GET /api/v1/resources?field1[ends_with]=value1
            ("field1[ends_with]=value1", "field1", QueryFieldOperatorEnum.ENDS_WITH, "value1"),
        ],
    )
    def test_docstring_filter_example(
        self,
        query: str,
        expected_base_name: str,
        expected_op: QueryFieldOperatorEnum,
        expected_value: str | list[str],
    ) -> None:
        """Assert resolver output matches the docstring example for ``query``."""
        resolver = _resolver_with_filter_fields()
        resolver.resolve(_request(query))
        key = QueryFieldName(expected_base_name)
        assert set(resolver.fields) == {key}
        field: QueryField[Any] = resolver.fields[key]
        assert field.operations[0].operator is expected_op
        assert field.operations[0].value == expected_value


class TestDocstringSortExamples:
    """Sorting lines in ``queries.__init__`` (``users`` path is illustrative only)."""

    def _resolver_with_sort_fields(self) -> QueryResolver:
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("name"), str)
        resolver.add_authorized_field(QueryFieldName("age"), int)
        return resolver

    def test_sort_name_ascending_default(self) -> None:
        """GET /api/v1/users?sort=name — single ascending sort, no filter fields."""
        # GET /api/v1/users?sort=name
        resolver = self._resolver_with_sort_fields()
        resolver.resolve(_request("sort=name"))
        assert len(resolver.sorts) == 1
        assert str(resolver.sorts[0].name) == "name"
        assert resolver.sorts[0].direction is QuerySortDirectionEnum.ASCENDING
        assert not resolver.fields

    def test_sort_minus_name_plus_age(self) -> None:
        """GET /api/v1/users?sort=-name&sort=+age — two sorts with explicit directions."""
        # GET /api/v1/users?sort=-name&sort=+age  (+ encoded for query strings)
        resolver = self._resolver_with_sort_fields()
        resolver.resolve(_request("sort=-name&sort=%2Bage"))
        assert len(resolver.sorts) == 2  # noqa: PLR2004
        assert str(resolver.sorts[0].name) == "name"
        assert resolver.sorts[0].direction is QuerySortDirectionEnum.DESCENDING
        assert str(resolver.sorts[1].name) == "age"
        assert resolver.sorts[1].direction is QuerySortDirectionEnum.ASCENDING
