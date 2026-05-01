"""End-to-end tests for :class:`QueryResolver` over a FastAPI app."""

from http import HTTPStatus
from typing import Annotated, Any, TypedDict, cast

from fastapi import FastAPI, Query, Request
from fastapi.testclient import TestClient
from pytest import fixture

from fastapi_factory_utilities.core.utils.api import (
    PaginationPageOffset,
    PaginationSize,
    QueryField,
    QueryFieldName,
    QueryResolver,
    RawQuerySort,
)


class _QueryFieldsEndpointResult(TypedDict):
    """Return shape for the test route so Pydantic serializes ``QueryField`` values."""

    page: PaginationPageOffset
    page_size: PaginationSize
    sort: list[RawQuerySort]
    fields: dict[str, QueryField[Any]]


class TestQueryFields:
    """Tests for the query fields."""

    @fixture(name="simple_fastapi_app")
    def simple_fastapi_app_fixture(self) -> FastAPI:
        """Create a simple FastAPI app."""
        app = FastAPI()

        def get_query_fields(
            page: Annotated[PaginationPageOffset, Query()],
            page_size: Annotated[PaginationSize, Query()],
            sort: Annotated[list[RawQuerySort], Query()],
            request: Request,
        ) -> _QueryFieldsEndpointResult:
            """Get the query fields."""
            resolver = QueryResolver(raise_on_unauthorized_field=True)
            resolver.add_authorized_field(field_name=QueryFieldName("name"), field_type=str)
            resolver.resolve(request=request)
            fields: dict[str, QueryField[Any]] = cast(dict[str, QueryField[Any]], resolver.fields)
            return {
                "page": page,
                "page_size": page_size,
                "sort": sort,
                "fields": fields,
            }

        app.get("/")(get_query_fields)

        return app

    @fixture(name="simple_fastapi_app_permissive")
    def simple_fastapi_app_permissive_fixture(self) -> FastAPI:
        """FastAPI app that drops unauthorized query fields instead of raising."""
        app = FastAPI()

        def get_query_fields(
            page: Annotated[PaginationPageOffset, Query()],
            page_size: Annotated[PaginationSize, Query()],
            sort: Annotated[list[RawQuerySort], Query()],
            request: Request,
        ) -> _QueryFieldsEndpointResult:
            """Get the query fields."""
            resolver = QueryResolver(raise_on_unauthorized_field=False)
            resolver.add_authorized_field(field_name=QueryFieldName("name"), field_type=str)
            resolver.resolve(request=request)
            fields: dict[str, QueryField[Any]] = cast(dict[str, QueryField[Any]], resolver.fields)
            return {
                "page": page,
                "page_size": page_size,
                "sort": sort,
                "fields": fields,
            }

        app.get("/")(get_query_fields)

        return app

    def test_simple_fastapi_app(self, simple_fastapi_app: FastAPI) -> None:
        """Test the simple FastAPI app."""
        client = TestClient(simple_fastapi_app)
        with client:
            response = client.get("/?page=1&page_size=10&sort=name&name=John")
            assert response.status_code == HTTPStatus.OK
            assert response.json() == {
                "page": 1,
                "page_size": 10,
                "sort": ["name"],
                "fields": {
                    "name": {"name": "name", "operations": [{"operator": "eq", "value": "John"}]},
                },
            }

    def test_simple_fastapi_app_with_unauthorized_field(self, simple_fastapi_app_permissive: FastAPI) -> None:
        """Test the simple FastAPI app with an unauthorized field."""
        client = TestClient(simple_fastapi_app_permissive)
        with client:
            response = client.get("/?page=1&page_size=10&sort=name&toto=test")
            assert response.status_code == HTTPStatus.OK
            assert response.json() == {
                "page": 1,
                "page_size": 10,
                "sort": ["name"],
                "fields": {},
            }

    @fixture(name="extended_fastapi_app")
    def extended_fastapi_app_fixture(self) -> FastAPI:
        """App with several authorized filter fields for bracket and ``in`` queries."""
        app = FastAPI()

        def get_query_fields(
            page: Annotated[PaginationPageOffset, Query()],
            page_size: Annotated[PaginationSize, Query()],
            sort: Annotated[list[RawQuerySort], Query()],
            request: Request,
        ) -> _QueryFieldsEndpointResult:
            """Get the query fields."""
            resolver = QueryResolver(raise_on_unauthorized_field=True)
            resolver.add_authorized_field(field_name=QueryFieldName("name"), field_type=str)
            resolver.add_authorized_field(field_name=QueryFieldName("age"), field_type=int)
            resolver.add_authorized_field(field_name=QueryFieldName("id"), field_type=int)
            resolver.resolve(request=request)
            fields: dict[str, QueryField[Any]] = cast(dict[str, QueryField[Any]], resolver.fields)
            return {
                "page": page,
                "page_size": page_size,
                "sort": sort,
                "fields": fields,
            }

        app.get("/")(get_query_fields)
        return app

    def test_sort_ascending_descending_prefixes(self, extended_fastapi_app: FastAPI) -> None:
        """``sort=-name`` and ascending ``sort=+age`` (``+`` as ``%2B``) preserve tokens."""
        client = TestClient(extended_fastapi_app)
        with client:
            response = client.get("/?page=1&page_size=10&sort=-name&sort=%2Bage")
            assert response.status_code == HTTPStatus.OK
            body = response.json()
            assert body["sort"] == ["-name", "+age"]

    def test_bracket_operator_and_coercion(self, extended_fastapi_app: FastAPI) -> None:
        """Bracket operators are keyed by raw param name; integers are coerced."""
        client = TestClient(extended_fastapi_app)
        with client:
            response = client.get("/?page=1&page_size=10&sort=name&age[gt]=21")
            assert response.status_code == HTTPStatus.OK
            assert response.json()["fields"] == {
                "age": {"name": "age", "operations": [{"operator": "gt", "value": 21}]},
            }

    def test_same_base_field_multiple_operators(self, extended_fastapi_app: FastAPI) -> None:
        """``age[gt]`` and ``age[lt]`` both appear under one ``age`` field as two operations."""
        client = TestClient(extended_fastapi_app)
        with client:
            response = client.get("/?page=1&page_size=10&sort=name&age[gt]=21&age[lt]=30")
            assert response.status_code == HTTPStatus.OK
            assert response.json()["fields"] == {
                "age": {
                    "name": "age",
                    "operations": [
                        {"operator": "gt", "value": 21},
                        {"operator": "lt", "value": 30},
                    ],
                },
            }

    def test_in_operator_list_coercion(self, extended_fastapi_app: FastAPI) -> None:
        """Repeated ``id[in]=`` yields a coerced list of integers."""
        client = TestClient(extended_fastapi_app)
        with client:
            response = client.get("/?page=1&page_size=10&sort=name&id[in]=7&id[in]=8&id[in]=9")
            assert response.status_code == HTTPStatus.OK
            assert response.json()["fields"] == {
                "id": {"name": "id", "operations": [{"operator": "in", "value": [7, 8, 9]}]},
            }
