"""Repository contract suite — mongomock + real Mongo, FFU tests only.

Not published. The ``core.testing`` package was deleted after a trial adoption
in audit_backend failed to collapse service fixtures to configuration.
"""

from __future__ import annotations

import datetime
from collections.abc import Callable
from types import MethodType
from typing import Any
from uuid import UUID, uuid4

import pytest
from beanie import SortDirection, init_beanie
from pydantic import BaseModel, Field
from pymongo.asynchronous.database import AsyncDatabase

from fastapi_factory_utilities.core.plugins.odm_plugin.documents import BaseDocument
from fastapi_factory_utilities.core.plugins.odm_plugin.exceptions import (
    UnableToCreateEntityDueToDuplicateKeyError,
)
from fastapi_factory_utilities.core.plugins.odm_plugin.repositories import AbstractRepository


class ContractDocument(BaseDocument):
    """Document used by the shared repository contract suite."""

    my_field: str = Field(description="Primary string field.")
    category: str | None = Field(default=None, description="Optional filter field.")

    class Settings:
        """Beanie settings."""

        name = "ffu_contract_documents"
        use_revision = True


class ContractEntity(BaseModel):
    """Entity used by the shared repository contract suite."""

    id: UUID
    my_field: str
    category: str | None = None
    revision_id: UUID | None = Field(default=None)
    created_at: datetime.datetime | None = Field(default=None)
    updated_at: datetime.datetime | None = Field(default=None)


class ContractRepository(AbstractRepository[ContractDocument, ContractEntity]):
    """Repository under test for the shared contract suite."""


def make_contract_entity(**kwargs: Any) -> ContractEntity:
    """Build a :class:`ContractEntity` for contract tests."""
    return ContractEntity(
        id=kwargs.get("id", uuid4()),
        my_field=kwargs.get("my_field", "field"),
        category=kwargs.get("category"),
    )


class _FalsyNoOpSession:
    """Session stand-in that slips past mongomock's truthy ``if session:`` guards."""

    def __bool__(self) -> bool:
        """Return False so mongomock treats the session as absent."""
        return False

    async def end_session(self) -> None:
        """No-op end_session matching pymongo's async API."""
        return None


def _patch_async_mongo_mock_client(client: Any) -> Any:
    """Add missing ``aconnect`` / ``aclose`` / ``start_session`` to a mock client."""

    async def _aconnect(self: Any) -> Any:
        return self

    async def _aclose(self: Any) -> None:

        return None

    def _start_session(self: Any, **_kwargs: Any) -> _FalsyNoOpSession:

        return _FalsyNoOpSession()

    client.aconnect = MethodType(_aconnect, client)
    client.aclose = MethodType(_aclose, client)
    client.start_session = MethodType(_start_session, client)
    return client


def _patch_async_mongo_mock_database(database: Any) -> Any:
    """Strip Beanie kwargs mongomock rejects from ``list_collection_names``."""
    original = database.list_collection_names

    async def _list_collection_names(*args: Any, **kwargs: Any) -> list[str]:
        kwargs.pop("authorizedCollections", None)
        kwargs.pop("nameOnly", None)
        result = original(*args, **kwargs)
        if hasattr(result, "__await__"):
            return await result
        return result

    database.list_collection_names = _list_collection_names
    return database


def build_mongomock_database(database_name: str | None = None) -> AsyncDatabase[Any]:
    """Build a mongomock-backed ``AsyncDatabase`` for the contract suite."""
    from pymongo_async_mock import AsyncMongoMockClient  # noqa: PLC0415

    client = _patch_async_mongo_mock_client(AsyncMongoMockClient())
    name = database_name or f"test_{uuid4()!s}"
    return _patch_async_mongo_mock_database(client[name])


async def init_contract_mongomock() -> ContractRepository:
    """Initialize Beanie on mongomock and return a :class:`ContractRepository`."""
    database = build_mongomock_database()
    await init_beanie(database=database, document_models=[ContractDocument])
    return ContractRepository(database=database)


class RepositoryContract:
    """Abstract contract for :class:`AbstractRepository` behavior.

    Subclass in a test module and provide ``repository`` / ``new_entity`` fixtures.
    """

    async def test_insert_then_get_by_id(
        self,
        repository: AbstractRepository[Any, Any],
        new_entity: Callable[..., Any],
    ) -> None:
        """Insert persists the entity and get_one_by_id round-trips it."""
        entity = new_entity(my_field="hello")
        created = await repository.insert(entity=entity)
        found = await repository.get_one_by_id(entity_id=created.id)
        assert found is not None
        assert found.id == created.id
        assert found.my_field == "hello"
        assert created.created_at is not None
        assert created.updated_at is not None

    async def test_get_missing_returns_none(
        self,
        repository: AbstractRepository[Any, Any],
    ) -> None:
        """Missing IDs return None rather than raising."""
        found = await repository.get_one_by_id(entity_id=uuid4())
        assert found is None

    async def test_update_changes_field(
        self,
        repository: AbstractRepository[Any, Any],
        new_entity: Callable[..., Any],
    ) -> None:
        """Update persists field changes."""
        created = await repository.insert(entity=new_entity(my_field="before"))
        created.my_field = "after"
        updated = await repository.update(entity=created)
        assert updated.my_field == "after"
        found = await repository.get_one_by_id(entity_id=created.id)
        assert found is not None
        assert found.my_field == "after"

    async def test_delete_one_by_id(
        self,
        repository: AbstractRepository[Any, Any],
        new_entity: Callable[..., Any],
    ) -> None:
        """Delete removes the entity."""
        created = await repository.insert(entity=new_entity(my_field="gone"))
        await repository.delete_one_by_id(entity_id=created.id)
        assert await repository.get_one_by_id(entity_id=created.id) is None

    async def test_delete_missing_raises_when_requested(
        self,
        repository: AbstractRepository[Any, Any],
    ) -> None:
        """delete_one_by_id raises ValueError when raise_if_not_found=True."""
        with pytest.raises(ValueError):
            await repository.delete_one_by_id(entity_id=uuid4(), raise_if_not_found=True)

    async def test_duplicate_key_raises(
        self,
        repository: AbstractRepository[Any, Any],
        new_entity: Callable[..., Any],
    ) -> None:
        """Inserting the same id twice raises UnableToCreateEntityDueToDuplicateKeyError."""
        entity_id: UUID = uuid4()
        await repository.insert(entity=new_entity(id=entity_id, my_field="first"))
        with pytest.raises(UnableToCreateEntityDueToDuplicateKeyError):
            await repository.insert(entity=new_entity(id=entity_id, my_field="second"))

    async def test_find_filter_sort_skip_limit(
        self,
        repository: AbstractRepository[Any, Any],
        new_entity: Callable[..., Any],
    ) -> None:
        """Find supports equality filter, sort, skip, and limit."""
        for my_field, category in (("C", "A"), ("A", "A"), ("B", "B")):
            await repository.insert(entity=new_entity(my_field=my_field, category=category))

        filtered = await repository.find({"category": "A"})
        assert len(filtered) == 2  # noqa: PLR2004
        assert all(entity.category == "A" for entity in filtered)

        sorted_entities = await repository.find(sort=[("my_field", SortDirection.ASCENDING)])
        assert [entity.my_field for entity in sorted_entities] == ["A", "B", "C"]

        page = await repository.find(skip=1, limit=1, sort=[("my_field", SortDirection.ASCENDING)])
        assert len(page) == 1
        assert page[0].my_field == "B"

    async def test_count_all_and_filtered(
        self,
        repository: AbstractRepository[Any, Any],
        new_entity: Callable[..., Any],
    ) -> None:
        """Count matches find filters."""
        await repository.insert(entity=new_entity(my_field="1", category="A"))
        await repository.insert(entity=new_entity(my_field="2", category="A"))
        await repository.insert(entity=new_entity(my_field="3", category="B"))
        assert await repository.count() == 3  # noqa: PLR2004
        assert await repository.count({"category": "A"}) == 2  # noqa: PLR2004
        assert await repository.count({"category": "missing"}) == 0

    async def test_collection_name(
        self,
        repository: AbstractRepository[Any, Any],
    ) -> None:
        """collection_name is a non-empty string."""
        assert isinstance(repository.collection_name, str)
        assert repository.collection_name != ""
