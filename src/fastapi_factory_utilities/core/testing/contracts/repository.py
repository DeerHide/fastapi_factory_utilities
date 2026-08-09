"""Shared repository contract suite.

Subclass and provide fixtures:

* ``repository`` — an :class:`~fastapi_factory_utilities.core.plugins.odm_plugin.repositories.AbstractRepository`
  instance whose Beanie document models are already initialized.
* ``new_entity`` — a callable ``(**kwargs) -> entity`` that builds a fresh entity.
  Recognized kwargs: ``my_field``, ``category``, ``id``.

The library CI runs this suite against both the mongomock-backed fake and a real
MongoDB testcontainer. Divergence is a build failure.
"""

from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

import pytest
from beanie import SortDirection

from fastapi_factory_utilities.core.plugins.odm_plugin.exceptions import (
    UnableToCreateEntityDueToDuplicateKeyError,
)
from fastapi_factory_utilities.core.plugins.odm_plugin.repositories import AbstractRepository


class RepositoryContract:
    """Abstract contract for :class:`AbstractRepository` behavior.

    Subclass in a test module and provide ``repository`` / ``new_entity`` fixtures
    (do not override methods here — define pytest fixtures on the subclass).
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
