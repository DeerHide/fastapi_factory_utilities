"""Integration tests: ODMQueryBuilder with Beanie and MongoDB."""

from __future__ import annotations

import datetime
from http import HTTPStatus
from typing import Annotated, Any
from uuid import UUID, uuid4

import pytest
from beanie import init_beanie  # pyright: ignore[reportUnknownVariableType]
from fastapi import FastAPI, Query, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field
from pymongo.asynchronous.database import AsyncDatabase
from starlette.requests import Request as StarletteRequest

from fastapi_factory_utilities.core.plugins.odm_plugin.documents import BaseDocument
from fastapi_factory_utilities.core.plugins.odm_plugin.queries import ODMQueryBuilder
from fastapi_factory_utilities.core.plugins.odm_plugin.repositories import AbstractRepository
from fastapi_factory_utilities.core.utils.paginations import PaginationPageOffset, PaginationSize
from fastapi_factory_utilities.core.utils.queries import (
    QueryAbstract,
    QueryField,
    QueryFieldName,
    QueryFieldOperation,
    QueryFieldOperatorEnum,
    QueryResolver,
    QuerySort,
    RawQuerySort,
)


class DocumentODMQueryIT(BaseDocument):
    """Beanie document for ODM query builder integration tests."""

    my_field: str = Field(description="Label field.")
    score: int = Field(default=0, description="Numeric field for range filters.")
    object1: dict[str, str] = Field(default_factory=dict, description="Nested map for dotted-path filters.")


class EntityODMQueryIT(BaseModel):
    """Entity paired with :class:`DocumentODMQueryIT`."""

    id: UUID
    my_field: str
    score: int = 0
    object1: dict[str, str] = Field(default_factory=dict)

    revision_id: UUID | None = Field(default=None)
    created_at: datetime.datetime | None = Field(default=None)
    updated_at: datetime.datetime | None = Field(default=None)


class RepositoryODMQueryIT(AbstractRepository[DocumentODMQueryIT, EntityODMQueryIT]):
    """Repository for query builder IT."""

    pass


class ItemQuery(QueryAbstract):
    """HTTP query model: filters align with document field names."""

    score: QueryField[int] | None = Field(default=None)
    my_field: QueryField[str] | None = Field(default=None)


class Object1Filter(BaseModel):
    """Nested filter group: authorizes ``object1.field1`` via :meth:`QueryResolver.from_model`."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    field1: QueryField[str] | None = Field(default=None)


class DotPathItemQuery(QueryAbstract):
    """Query model for ``object1.field1``-style params (nested filter + dotted Mongo path)."""

    object1: Object1Filter | None = Field(default=None)


def _item_query_from_resolver(
    resolver: QueryResolver,
    page: PaginationPageOffset,
    page_size: PaginationSize,
) -> ItemQuery:
    """Build :class:`ItemQuery` without validating ``QueryField`` values (supports ``in`` / ``nin`` lists)."""
    filter_kw: dict[str, Any] = {str(name): field for name, field in resolver.fields.items()}
    return ItemQuery.model_construct(
        page=page,
        page_size=page_size,
        sorts=resolver.sorts,
        **filter_kw,  # type: ignore[arg-type]
    )


def _built_find_json(query_model: ItemQuery) -> dict[str, Any]:
    """JSON-serializable snapshot of :meth:`ODMQueryBuilder.build` for assertions."""
    built = ODMQueryBuilder[ItemQuery]().set_query_filter(query_model).build()
    return {
        "mongo_filter": built.mongo_filter,
        "skip": built.skip,
        "limit": built.limit,
        "sort": [(f, d.name) for f, d in built.sort] if built.sort else None,
    }


def _request_from_query_string(query_string: str) -> StarletteRequest:
    return StarletteRequest(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": query_string.encode("utf-8"),
        }
    )


@pytest.mark.asyncio()
async def test_find_with_resolver_range_on_score(async_motor_database: AsyncDatabase[Any]) -> None:
    """Resolver collects score[gt] and score[lt]; builder merges; find returns matching rows."""
    await init_beanie(database=async_motor_database, document_models=[DocumentODMQueryIT])
    repository = RepositoryODMQueryIT(database=async_motor_database)

    for score in (1, 5, 10):
        await repository.insert(entity=EntityODMQueryIT(id=uuid4(), my_field=f"row_{score}", score=score))

    req = _request_from_query_string("score[gt]=2&score[lt]=9&page=0&page_size=50")
    resolver = QueryResolver(raise_on_unauthorized_field=True)
    resolver.from_model(ItemQuery)
    resolver.resolve(req)

    fields_kw = {str(name): field for name, field in resolver.fields.items()}
    query_model = ItemQuery(
        **fields_kw,
        page=PaginationPageOffset(0),
        page_size=PaginationSize(50),
        sorts=resolver.sorts,
    )

    built = ODMQueryBuilder[ItemQuery]().set_query_filter(query_model).build()
    found = await repository.find(
        built.mongo_filter,
        skip=built.skip,
        limit=built.limit,
        sort=built.sort,
    )

    assert len(found) == 1
    assert found[0].score == 5  # noqa: PLR2004
    assert found[0].my_field == "row_5"


@pytest.mark.asyncio()
async def test_find_contains_sort_and_pagination(async_motor_database: AsyncDatabase[Any]) -> None:
    """String contains filter, sort, and skip/limit end-to-end."""
    await init_beanie(database=async_motor_database, document_models=[DocumentODMQueryIT])
    repository = RepositoryODMQueryIT(database=async_motor_database)

    await repository.insert(entity=EntityODMQueryIT(id=uuid4(), my_field="apple", score=1))
    await repository.insert(entity=EntityODMQueryIT(id=uuid4(), my_field="application", score=2))
    await repository.insert(entity=EntityODMQueryIT(id=uuid4(), my_field="banana", score=3))

    field = QueryField(
        name=QueryFieldName("my_field"),
        operations=[QueryFieldOperation(operator=QueryFieldOperatorEnum.CONTAINS, value="app")],
    )
    query_model = ItemQuery(
        page=PaginationPageOffset(0),
        page_size=PaginationSize(1),
        sorts=[QuerySort.model_validate(RawQuerySort("-score"))],
        my_field=field,
    )

    built = ODMQueryBuilder[ItemQuery]().set_query_filter(query_model).build()
    first = await repository.find(
        built.mongo_filter,
        skip=built.skip,
        limit=built.limit,
        sort=built.sort,
    )
    assert len(first) == 1
    assert first[0].my_field == "application"
    assert first[0].score == 2  # noqa: PLR2004

    built_page2 = (
        ODMQueryBuilder[ItemQuery]()
        .set_query_filter(
            ItemQuery(
                page=PaginationPageOffset(1),
                page_size=PaginationSize(1),
                sorts=[QuerySort.model_validate(RawQuerySort("-score"))],
                my_field=field,
            )
        )
        .build()
    )
    second = await repository.find(
        built_page2.mongo_filter,
        skip=built_page2.skip,
        limit=built_page2.limit,
        sort=built_page2.sort,
    )
    assert len(second) == 1
    assert second[0].my_field == "apple"


@pytest.mark.parametrize(
    ("extra_query", "expected_mongo_filter", "expected_sort"),
    [
        pytest.param("my_field=plain", {"my_field": "plain"}, None, id="eq_implicit"),
        pytest.param(
            "score[gt]=2&score[lt]=8",
            {"score": {"$gt": 2, "$lt": 8}},
            None,
            id="gt_and_lt",
        ),
        pytest.param("score[gte]=5", {"score": {"$gte": 5}}, None, id="gte"),
        pytest.param("score[lte]=5", {"score": {"$lte": 5}}, None, id="lte"),
        pytest.param("score[eq]=7", {"score": 7}, None, id="eq_bracket"),
        pytest.param("score[neq]=7", {"score": {"$ne": 7}}, None, id="neq"),
        pytest.param(
            "score[in]=1&score[in]=4",
            {"score": {"$in": [1, 4]}},
            None,
            id="in",
        ),
        pytest.param(
            "score[nin]=0&score[nin]=9",
            {"score": {"$nin": [0, 9]}},
            None,
            id="nin",
        ),
        pytest.param(
            "my_field[contains]=pp",
            {"my_field": {"$regex": "pp", "$options": "i"}},
            None,
            id="contains",
        ),
        pytest.param(
            "my_field[not_contains]=zz",
            {"my_field": {"$not": {"$regex": "zz", "$options": "i"}}},
            None,
            id="not_contains",
        ),
        pytest.param(
            "my_field[starts_with]=pre",
            {"my_field": {"$regex": "^pre", "$options": "i"}},
            None,
            id="starts_with",
        ),
        pytest.param(
            "my_field[ends_with]=fix",
            {"my_field": {"$regex": "fix$", "$options": "i"}},
            None,
            id="ends_with",
        ),
        pytest.param("sort=my_field", {}, [["my_field", "ASCENDING"]], id="sort_asc_default"),
        pytest.param(
            "sort=-my_field&sort=%2Bscore",
            {},
            [["my_field", "DESCENDING"], ["score", "ASCENDING"]],
            id="sort_minus_and_plus",
        ),
        pytest.param(
            "score[gte]=5&sort=-score",
            {"score": {"$gte": 5}},
            [["score", "DESCENDING"]],
            id="filter_plus_sort",
        ),
    ],
)
def test_queries_init_docstring_examples_fastapi_to_mongo(
    extra_query: str,
    expected_mongo_filter: dict[str, Any],
    expected_sort: list[list[str]] | None,
) -> None:
    """Cover filtering and sorting patterns from ``core.utils.queries`` module docstring (lines 5-21)."""
    app = FastAPI()

    def get_items(
        request: Request,
        page: Annotated[PaginationPageOffset, Query()] = PaginationPageOffset.default(),
        page_size: Annotated[PaginationSize, Query()] = PaginationSize.default(),
    ) -> dict[str, Any]:
        resolver = QueryResolver(raise_on_unauthorized_field=True)
        resolver.from_model(ItemQuery)
        resolver.resolve(request)
        query_model = _item_query_from_resolver(resolver, page, page_size)
        return _built_find_json(query_model)

    app.get("/items")(get_items)

    client = TestClient(app)
    response = client.get(f"/items?{extra_query}&page=0&page_size=20")
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body["mongo_filter"] == expected_mongo_filter
    assert body["skip"] == 0
    assert body["limit"] == 20  # noqa: PLR2004
    assert body["sort"] == expected_sort


def test_queries_init_dotted_field_name_fastapi_to_mongo() -> None:
    """``object1.field1=value`` from the module docstring maps to a dotted Mongo path."""
    app = FastAPI()

    def get_items(
        request: Request,
        page: Annotated[PaginationPageOffset, Query()] = PaginationPageOffset.default(),
        page_size: Annotated[PaginationSize, Query()] = PaginationSize.default(),
    ) -> dict[str, Any]:
        resolver = QueryResolver(raise_on_unauthorized_field=True)
        resolver.from_model(DotPathItemQuery)
        resolver.resolve(request)
        qm = DotPathItemQuery.model_construct(
            page=page,
            page_size=page_size,
            sorts=resolver.sorts,
            object1=Object1Filter.model_construct(
                field1=resolver.fields.get(QueryFieldName("object1.field1")),
            ),
        )
        built = ODMQueryBuilder[DotPathItemQuery]().set_query_filter(qm).build()
        return {
            "mongo_filter": built.mongo_filter,
            "skip": built.skip,
            "limit": built.limit,
            "sort": [(f, d.name) for f, d in built.sort] if built.sort else None,
        }

    app.get("/items")(get_items)

    client = TestClient(app)
    response = client.get("/items?object1.field1=nested-value&page=0&page_size=20")
    assert response.status_code == HTTPStatus.OK
    assert response.json()["mongo_filter"] == {"object1.field1": "nested-value"}


@pytest.mark.asyncio()
async def test_find_dotted_object1_field1_matches_nested_document(async_motor_database: AsyncDatabase[Any]) -> None:
    """End-to-end: filter on ``object1.field1`` returns documents with matching nested map."""
    await init_beanie(database=async_motor_database, document_models=[DocumentODMQueryIT])
    repository = RepositoryODMQueryIT(database=async_motor_database)

    await repository.insert(
        entity=EntityODMQueryIT(
            id=uuid4(),
            my_field="a",
            score=1,
            object1={"field1": "match-me"},
        )
    )
    await repository.insert(
        entity=EntityODMQueryIT(
            id=uuid4(),
            my_field="b",
            score=2,
            object1={"field1": "other"},
        )
    )

    req = _request_from_query_string("object1.field1=match-me&page=0&page_size=50")
    resolver = QueryResolver(raise_on_unauthorized_field=True)
    resolver.from_model(DotPathItemQuery)
    resolver.resolve(req)

    qm = DotPathItemQuery.model_construct(
        page=PaginationPageOffset(0),
        page_size=PaginationSize(50),
        sorts=resolver.sorts,
        object1=Object1Filter.model_construct(field1=resolver.fields[QueryFieldName("object1.field1")]),
    )
    built = ODMQueryBuilder[DotPathItemQuery]().set_query_filter(qm).build()
    found = await repository.find(
        built.mongo_filter,
        skip=built.skip,
        limit=built.limit,
        sort=built.sort,
    )

    assert len(found) == 1
    assert found[0].my_field == "a"
    assert found[0].object1.get("field1") == "match-me"
