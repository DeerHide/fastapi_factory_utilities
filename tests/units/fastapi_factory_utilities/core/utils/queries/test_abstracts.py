"""Provides tests for the query abstract."""

from http import HTTPStatus
from typing import Annotated

from fastapi import FastAPI, Query, Request
from fastapi.testclient import TestClient
from pydantic import Field
from pytest import fixture

from fastapi_factory_utilities.core.utils.paginations import PaginationPageOffset, PaginationSize
from fastapi_factory_utilities.core.utils.queries import (
    QueryAbstract,
    QueryField,
    QueryFieldName,
    QueryResolver,
    QuerySort,
    RawQueryFieldName,
    RawQuerySort,
)


class TestQueryAbstract:
    """Tests for the query fields."""

    class SampleQuery(QueryAbstract):
        """Sample query."""

        name: QueryField[str] | None = Field(default=None)
        age: QueryField[int] | None = Field(default=None)
        email: QueryField[str] | None = Field(default=None)

    @fixture(name="simple_fastapi_app")
    def simple_fastapi_app_fixture(self) -> FastAPI:
        """Create a simple FastAPI app."""
        app = FastAPI()

        def get_query_fields(
            request: Request,
            page: Annotated[PaginationPageOffset, Query()] = PaginationPageOffset.default(),
            page_size: Annotated[PaginationSize, Query()] = PaginationSize.default(),
        ) -> TestQueryAbstract.SampleQuery:
            """Get the query fields."""
            resolver = QueryResolver(raise_on_unauthorized_field=True)
            resolver.from_model(model=self.SampleQuery)
            resolver.resolve(request=request)
            query_model = self.SampleQuery(
                **resolver.fields,  # type: ignore
                page=page,
                page_size=page_size,
                sorts=resolver.sorts,
            )
            return query_model

        app.get("/")(get_query_fields)

        return app

    def test_from_model_resolver_exposes_fields_on_property(self, simple_fastapi_app: FastAPI) -> None:
        """``from_model`` + :meth:`QueryResolver.resolve` fills :attr:`QueryResolver.fields` by base name."""
        client = TestClient(simple_fastapi_app)
        with client:
            response = client.get("/?page=1&page_size=10&sort=name&name=Ada&email=ada@example.com")
            content: TestQueryAbstract.SampleQuery = TestQueryAbstract.SampleQuery.model_validate(
                response.json(), extra="ignore"
            )
            assert response.status_code == HTTPStatus.OK
            assert content.page == PaginationPageOffset(1)
            assert content.page_size == PaginationSize(10)
            assert content.sorts == [QuerySort(value=RawQuerySort("name"))]
            assert content.get_fields() == {
                QueryFieldName("name"): QueryField(raw_query_field=RawQueryFieldName("name"), value="Ada"),
                QueryFieldName("email"): QueryField(
                    raw_query_field=RawQueryFieldName("email"), value="ada@example.com"
                ),
            }
