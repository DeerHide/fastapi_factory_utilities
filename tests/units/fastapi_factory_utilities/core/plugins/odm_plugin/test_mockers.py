"""Unit tests for ODM plugin mockers."""
# pylint: disable=protected-access  # Testing internal implementation

import asyncio
import datetime
from collections.abc import Mapping
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import pytest
from beanie import SortDirection
from beanie.operators import Exists, In, NotIn, RegEx
from pydantic import Field

from fastapi_factory_utilities.core.plugins.odm_plugin.documents import BaseDocument
from fastapi_factory_utilities.core.plugins.odm_plugin.exceptions import (
    OperationError,
    UnableToCreateEntityDueToDuplicateKeyError,
)
from fastapi_factory_utilities.core.plugins.odm_plugin.helpers import PersistedEntity
from fastapi_factory_utilities.core.plugins.odm_plugin.mockers import (
    AbstractRepositoryInMemory,
    managed_session,
)

# Test constants
TEST_VALUE_42 = 42
TEST_VALUE_10 = 10
TEST_VALUE_20 = 20
TEST_VALUE_30 = 30
TEST_VALUE_200 = 200
EXPECTED_ENTITY_COUNT_2 = 2
EXPECTED_ENTITY_COUNT_3 = 3
SKIP_ONE_ENTITY = 1


# Test data classes
class ConcreteDocument(BaseDocument):
    """Test document class."""

    name: str = Field(description="Name field.")
    category: str | None = Field(default=None, description="Category field for filtering tests.")
    value: int = Field(default=0, description="Value field for sorting tests.")


class ConcreteEntity(PersistedEntity):
    """Test entity class with additional fields."""

    name: str = Field(description="Name field.")
    category: str | None = Field(default=None, description="Category field for filtering tests.")
    value: int = Field(default=0, description="Value field for sorting tests.")


class ConcreteRepositoryInMemory(AbstractRepositoryInMemory[ConcreteDocument, ConcreteEntity]):
    """Concrete implementation of AbstractRepositoryInMemory for testing."""

    pass


class TestManagedSession:
    """Tests for managed_session decorator."""

    async def test_decorator_preserves_function_metadata(self) -> None:
        """Test decorator preserves function name and docstring via functools.wraps."""

        # Arrange
        @managed_session()
        async def my_function_name(*_args: Any, **_kwargs: Any) -> int:
            """This is the docstring."""
            return TEST_VALUE_42

        # Assert
        assert my_function_name.__name__ == "my_function_name"
        assert my_function_name.__doc__ == "This is the docstring."

    async def test_decorator_with_session_provided(self) -> None:
        """Test decorator passes through when session is in kwargs."""
        # Arrange
        call_count = 0

        @managed_session()
        async def test_func(*_args: Any, **kwargs: Any) -> int:
            nonlocal call_count
            call_count += 1
            assert "session" in kwargs
            return TEST_VALUE_42

        class MockRepo:
            """Mock repository for testing."""

            @asynccontextmanager
            async def get_session(self) -> Any:
                """Mock get_session."""
                yield None

        repo = MockRepo()

        # Act
        result = await test_func(repo, session=None)

        # Assert
        assert result == TEST_VALUE_42
        assert call_count == 1

    async def test_decorator_without_session_provided(self) -> None:
        """Test decorator creates session when not provided."""
        # Arrange
        call_count = 0
        session_created = False

        @managed_session()
        async def test_func(*_args: Any, **kwargs: Any) -> int:
            nonlocal call_count, session_created
            call_count += 1
            assert "session" in kwargs
            session_created = True
            return TEST_VALUE_42

        class MockRepo:
            """Mock repository for testing."""

            @asynccontextmanager
            async def get_session(self) -> Any:
                """Mock get_session."""
                yield None

        repo = MockRepo()

        # Act
        result = await test_func(repo)

        # Assert
        assert result == TEST_VALUE_42
        assert call_count == 1
        assert session_created is True

    async def test_decorator_with_async_function(self) -> None:
        """Test decorator works with async functions."""

        # Arrange
        @managed_session()
        async def async_test_func(*_args: Any, **_kwargs: Any) -> str:
            return "async_result"

        class MockRepo:
            """Mock repository for testing."""

            @asynccontextmanager
            async def get_session(self) -> Any:
                """Mock get_session."""
                yield None

        repo = MockRepo()

        # Act
        result = await async_test_func(repo)

        # Assert
        assert result == "async_result"


class TestAbstractRepositoryInMemory:
    """Tests for AbstractRepositoryInMemory class."""

    def test_init_with_no_entities(self) -> None:
        """Test initialization with empty entities list."""
        # Act
        repository = ConcreteRepositoryInMemory()

        # Assert
        assert not repository._entities  # pyright: ignore[reportPrivateUsage]

    def test_init_with_entities(self) -> None:
        """Test initialization with pre-populated entities."""
        # Arrange
        entity1 = ConcreteEntity(name="Entity 1", value=TEST_VALUE_10)
        entity2 = ConcreteEntity(name="Entity 2", value=TEST_VALUE_20)
        entities = [entity1, entity2]

        # Act
        repository = ConcreteRepositoryInMemory(entities=entities)

        # Assert
        assert len(repository._entities) == EXPECTED_ENTITY_COUNT_2  # pyright: ignore[reportPrivateUsage]
        assert repository._entities[entity1.id] == entity1  # pyright: ignore[reportPrivateUsage]
        assert repository._entities[entity2.id] == entity2  # pyright: ignore[reportPrivateUsage]

    def test_init_retrieves_generic_types(self) -> None:
        """Test generic type retrieval from __orig_bases__."""
        # Act
        repository = ConcreteRepositoryInMemory()

        # Assert
        assert repository._document_type == ConcreteDocument  # pyright: ignore[reportPrivateUsage]
        assert repository._entity_type == ConcreteEntity  # pyright: ignore[reportPrivateUsage]

    async def test_get_session(self) -> None:
        """Test session context manager works correctly."""
        # Arrange
        repository = ConcreteRepositoryInMemory()

        # Act & Assert
        async with repository.get_session() as session:
            assert session is None

    async def test_insert_creates_entity(self) -> None:
        """Test insert creates entity with timestamps."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity = ConcreteEntity(name="Test Entity", value=100)

        # Act
        result = await repository.insert(entity=entity)

        # Assert
        assert result.id == entity.id
        assert result.name == entity.name
        assert result.created_at is not None
        assert result.updated_at is not None
        assert len(repository._entities) == 1  # pyright: ignore[reportPrivateUsage]

    async def test_insert_sets_created_at_and_updated_at(self) -> None:
        """Test timestamps are set correctly on the returned entity."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity = ConcreteEntity(name="Test Entity", value=100)
        before_insert = datetime.datetime.now(tz=datetime.UTC)

        # Act
        result = await repository.insert(entity=entity)

        # Assert - check the returned entity has timestamps
        after_insert = datetime.datetime.now(tz=datetime.UTC)
        assert result.created_at is not None
        assert result.updated_at is not None
        assert result.created_at == result.updated_at
        assert before_insert <= result.created_at <= after_insert

    async def test_insert_stores_entity_in_memory(self) -> None:
        """Test entity is stored in _entities dict."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity = ConcreteEntity(name="Test Entity", value=100)

        # Act
        result = await repository.insert(entity=entity)

        # Assert - both returned and stored entities should have timestamps
        stored_entity = repository._entities[entity.id]  # pyright: ignore[reportPrivateUsage]
        assert stored_entity.id == entity.id
        assert stored_entity.name == entity.name
        assert stored_entity.created_at is not None
        assert stored_entity.updated_at is not None
        assert result.created_at == stored_entity.created_at
        assert result.updated_at == stored_entity.updated_at

    async def test_insert_raises_duplicate_key_error(self) -> None:
        """Test insert raises UnableToCreateEntityDueToDuplicateKeyError when ID already exists."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity = ConcreteEntity(name="Test Entity", value=100)
        await repository.insert(entity=entity)

        # Act & Assert
        with pytest.raises(UnableToCreateEntityDueToDuplicateKeyError) as exc_info:
            await repository.insert(entity=entity)

        assert str(entity.id) in str(exc_info.value)

    async def test_insert_with_session(self) -> None:
        """Test insert works with session parameter."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity = ConcreteEntity(name="Test Entity", value=100)

        # Act
        result = await repository.insert(entity=entity, session=None)

        # Assert
        assert result.id == entity.id
        assert len(repository._entities) == 1  # pyright: ignore[reportPrivateUsage]

    async def test_update_modifies_entity(self) -> None:
        """Test update modifies existing entity."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity = ConcreteEntity(name="Original Name", value=100)
        await repository.insert(entity=entity)
        stored_entity = repository._entities[entity.id]  # pyright: ignore[reportPrivateUsage]
        original_created_at = stored_entity.created_at

        # Wait a bit to ensure updated_at is different
        await asyncio.sleep(0.01)

        # Create updated entity with preserved created_at from stored entity
        updated_entity = ConcreteEntity(
            id=entity.id, name="Updated Name", value=TEST_VALUE_200, created_at=original_created_at
        )

        # Act
        result = await repository.update(entity=updated_entity)

        # Assert
        assert result.id == entity.id
        assert result.name == "Updated Name"
        assert result.value == TEST_VALUE_200
        assert result.created_at == original_created_at

    async def test_update_sets_updated_at(self) -> None:
        """Test updated_at is updated but created_at is preserved."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity = ConcreteEntity(name="Test Entity", value=100)
        await repository.insert(entity=entity)
        stored_entity = repository._entities[entity.id]  # pyright: ignore[reportPrivateUsage]
        original_created_at = stored_entity.created_at
        original_updated_at = stored_entity.updated_at

        # Wait a bit to ensure updated_at is different
        await asyncio.sleep(0.01)

        # Create updated entity with preserved created_at from stored entity
        updated_entity = ConcreteEntity(
            id=entity.id, name="Updated Name", value=TEST_VALUE_200, created_at=original_created_at
        )

        # Act
        result = await repository.update(entity=updated_entity)

        # Assert
        assert result.created_at == original_created_at
        assert result.updated_at > original_updated_at

    async def test_update_raises_operation_error_when_not_found(self) -> None:
        """Test update raises OperationError when entity ID doesn't exist."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity = ConcreteEntity(id=uuid4(), name="Non-existent Entity", value=100)

        # Act & Assert
        with pytest.raises(OperationError) as exc_info:
            await repository.update(entity=entity)

        assert str(entity.id) in str(exc_info.value)

    async def test_update_with_session(self) -> None:
        """Test update works with session parameter."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity = ConcreteEntity(name="Test Entity", value=100)
        await repository.insert(entity=entity)

        updated_entity = ConcreteEntity(id=entity.id, name="Updated Name", value=200)

        # Act
        result = await repository.update(entity=updated_entity, session=None)

        # Assert
        assert result.name == "Updated Name"

    async def test_get_one_by_id_returns_entity(self) -> None:
        """Test get returns correct entity."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity = ConcreteEntity(name="Test Entity", value=100)
        await repository.insert(entity=entity)

        # Act
        result = await repository.get_one_by_id(entity_id=entity.id)

        # Assert
        assert result is not None
        assert result.id == entity.id
        assert result.name == entity.name

    async def test_get_one_by_id_returns_none(self) -> None:
        """Test get returns None for non-existent ID."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        non_existent_id = uuid4()

        # Act
        result = await repository.get_one_by_id(entity_id=non_existent_id)

        # Assert
        assert result is None

    async def test_get_one_by_id_with_session(self) -> None:
        """Test get works with session parameter."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity = ConcreteEntity(name="Test Entity", value=100)
        await repository.insert(entity=entity)

        # Act
        result = await repository.get_one_by_id(entity_id=entity.id, session=None)

        # Assert
        assert result is not None
        assert result.id == entity.id

    async def test_delete_one_by_id_removes_entity(self) -> None:
        """Test delete removes entity from memory."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity = ConcreteEntity(name="Test Entity", value=100)
        await repository.insert(entity=entity)
        assert len(repository._entities) == 1  # pyright: ignore[reportPrivateUsage]

        # Act
        await repository.delete_one_by_id(entity_id=entity.id)

        # Assert
        assert len(repository._entities) == 0  # pyright: ignore[reportPrivateUsage]
        assert entity.id not in repository._entities  # pyright: ignore[reportPrivateUsage]

    async def test_delete_one_by_id_does_not_raise_when_not_found_by_default(self) -> None:
        """Test delete does not raise when entity ID doesn't exist by default."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        non_existent_id = uuid4()

        # Act & Assert - should not raise
        await repository.delete_one_by_id(entity_id=non_existent_id)

    async def test_delete_one_by_id_raises_operation_error_when_not_found_and_flag_set(self) -> None:
        """Test delete raises OperationError when entity ID doesn't exist and raise_if_not_found is True."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        non_existent_id = uuid4()

        # Act & Assert
        with pytest.raises(OperationError) as exc_info:
            await repository.delete_one_by_id(entity_id=non_existent_id, raise_if_not_found=True)

        assert str(non_existent_id) in str(exc_info.value)

    async def test_delete_one_by_id_with_session(self) -> None:
        """Test delete works with session parameter."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity = ConcreteEntity(name="Test Entity", value=100)
        await repository.insert(entity=entity)

        # Act
        await repository.delete_one_by_id(entity_id=entity.id, session=None)

        # Assert
        assert len(repository._entities) == 0  # pyright: ignore[reportPrivateUsage]

    async def test_delete_one_by_id_with_raise_if_not_found_false(self) -> None:
        """Test delete with raise_if_not_found=False explicitly."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity = ConcreteEntity(name="Test Entity", value=100)
        await repository.insert(entity=entity)

        # Act - delete existing entity
        await repository.delete_one_by_id(entity_id=entity.id, raise_if_not_found=False)

        # Assert
        assert len(repository._entities) == 0  # pyright: ignore[reportPrivateUsage]

    async def test_find_returns_all_entities(self) -> None:
        """Test find returns all entities when no filters."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity1 = ConcreteEntity(name="Entity 1", value=TEST_VALUE_10)
        entity2 = ConcreteEntity(name="Entity 2", value=TEST_VALUE_20)
        entity3 = ConcreteEntity(name="Entity 3", value=TEST_VALUE_30)
        await repository.insert(entity=entity1)
        await repository.insert(entity=entity2)
        await repository.insert(entity=entity3)

        # Act
        results = await repository.find()

        # Assert
        assert len(results) == EXPECTED_ENTITY_COUNT_3
        assert {r.id for r in results} == {entity1.id, entity2.id, entity3.id}

    async def test_find_with_mapping_filter(self) -> None:
        """Test find filters by Mapping arguments."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity1 = ConcreteEntity(name="Entity 1", category="A", value=TEST_VALUE_10)
        entity2 = ConcreteEntity(name="Entity 2", category="B", value=TEST_VALUE_20)
        entity3 = ConcreteEntity(name="Entity 3", category="A", value=TEST_VALUE_30)
        await repository.insert(entity=entity1)
        await repository.insert(entity=entity2)
        await repository.insert(entity=entity3)

        # Act
        filter_dict: Mapping[str, Any] = {"category": "A"}
        results = await repository.find(filter_dict)

        # Assert
        assert len(results) == EXPECTED_ENTITY_COUNT_2
        assert all(r.category == "A" for r in results)
        assert {r.id for r in results} == {entity1.id, entity3.id}

    async def test_find_with_bool_filter(self) -> None:
        """Test find filters by bool arguments."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity1 = ConcreteEntity(name="Entity 1", value=TEST_VALUE_10)
        entity2 = ConcreteEntity(name="Entity 2", value=TEST_VALUE_20)
        await repository.insert(entity=entity1)
        await repository.insert(entity=entity2)

        # Act
        results = await repository.find(True)

        # Assert
        assert len(results) == EXPECTED_ENTITY_COUNT_2

    async def test_find_with_multiple_filters(self) -> None:
        """Test find applies multiple filters correctly."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity1 = ConcreteEntity(name="Entity 1", category="A", value=TEST_VALUE_10)
        entity2 = ConcreteEntity(name="Entity 2", category="B", value=TEST_VALUE_20)
        entity3 = ConcreteEntity(name="Entity 3", category="A", value=TEST_VALUE_30)
        await repository.insert(entity=entity1)
        await repository.insert(entity=entity2)
        await repository.insert(entity=entity3)

        # Act
        filter1: Mapping[str, Any] = {"category": "A"}
        filter2: Mapping[str, Any] = {"value": TEST_VALUE_10}
        results = await repository.find(filter1, filter2)

        # Assert
        assert len(results) == 1
        assert results[0].id == entity1.id

    async def test_find_with_sort_ascending(self) -> None:
        """Test find sorts ascending correctly."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity1 = ConcreteEntity(name="Entity 1", value=TEST_VALUE_30)
        entity2 = ConcreteEntity(name="Entity 2", value=TEST_VALUE_10)
        entity3 = ConcreteEntity(name="Entity 3", value=TEST_VALUE_20)
        await repository.insert(entity=entity1)
        await repository.insert(entity=entity2)
        await repository.insert(entity=entity3)

        # Act
        sort_order = [("value", SortDirection.ASCENDING)]
        results = await repository.find(sort=sort_order)

        # Assert
        assert len(results) == EXPECTED_ENTITY_COUNT_3
        assert results[0].value == TEST_VALUE_10
        assert results[1].value == TEST_VALUE_20
        assert results[2].value == TEST_VALUE_30

    async def test_find_with_sort_descending(self) -> None:
        """Test find sorts descending correctly."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity1 = ConcreteEntity(name="Entity 1", value=TEST_VALUE_30)
        entity2 = ConcreteEntity(name="Entity 2", value=TEST_VALUE_10)
        entity3 = ConcreteEntity(name="Entity 3", value=TEST_VALUE_20)
        await repository.insert(entity=entity1)
        await repository.insert(entity=entity2)
        await repository.insert(entity=entity3)

        # Act
        sort_order = [("value", SortDirection.DESCENDING)]
        results = await repository.find(sort=sort_order)

        # Assert
        assert len(results) == EXPECTED_ENTITY_COUNT_3
        assert results[0].value == TEST_VALUE_30
        assert results[1].value == TEST_VALUE_20
        assert results[2].value == TEST_VALUE_10

    async def test_find_with_skip(self) -> None:
        """Test find skips correct number of entities."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity1 = ConcreteEntity(name="Entity 1", value=TEST_VALUE_10)
        entity2 = ConcreteEntity(name="Entity 2", value=TEST_VALUE_20)
        entity3 = ConcreteEntity(name="Entity 3", value=TEST_VALUE_30)
        await repository.insert(entity=entity1)
        await repository.insert(entity=entity2)
        await repository.insert(entity=entity3)

        # Act
        results = await repository.find(skip=EXPECTED_ENTITY_COUNT_2)

        # Assert
        assert len(results) == 1

    async def test_find_with_limit(self) -> None:
        """Test find limits results correctly."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity1 = ConcreteEntity(name="Entity 1", value=TEST_VALUE_10)
        entity2 = ConcreteEntity(name="Entity 2", value=TEST_VALUE_20)
        entity3 = ConcreteEntity(name="Entity 3", value=TEST_VALUE_30)
        await repository.insert(entity=entity1)
        await repository.insert(entity=entity2)
        await repository.insert(entity=entity3)

        # Act
        results = await repository.find(limit=EXPECTED_ENTITY_COUNT_2)

        # Assert
        assert len(results) == EXPECTED_ENTITY_COUNT_2

    async def test_find_with_skip_and_limit(self) -> None:
        """Test find combines skip and limit correctly."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity1 = ConcreteEntity(name="Entity 1", value=TEST_VALUE_10)
        entity2 = ConcreteEntity(name="Entity 2", value=TEST_VALUE_20)
        entity3 = ConcreteEntity(name="Entity 3", value=TEST_VALUE_30)
        entity4 = ConcreteEntity(name="Entity 4", value=40)
        await repository.insert(entity=entity1)
        await repository.insert(entity=entity2)
        await repository.insert(entity=entity3)
        await repository.insert(entity=entity4)

        # Act
        results = await repository.find(skip=SKIP_ONE_ENTITY, limit=EXPECTED_ENTITY_COUNT_2)

        # Assert
        assert len(results) == EXPECTED_ENTITY_COUNT_2

    async def test_find_with_all_parameters(self) -> None:
        """Test find works with filters, sort, skip, and limit together."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity1 = ConcreteEntity(name="Entity 1", category="A", value=TEST_VALUE_10)
        entity2 = ConcreteEntity(name="Entity 2", category="A", value=TEST_VALUE_20)
        entity3 = ConcreteEntity(name="Entity 3", category="A", value=TEST_VALUE_30)
        entity4 = ConcreteEntity(name="Entity 4", category="B", value=40)
        await repository.insert(entity=entity1)
        await repository.insert(entity=entity2)
        await repository.insert(entity=entity3)
        await repository.insert(entity=entity4)

        # Act
        filter_dict: Mapping[str, Any] = {"category": "A"}
        sort_order = [("value", SortDirection.DESCENDING)]
        results = await repository.find(filter_dict, sort=sort_order, skip=SKIP_ONE_ENTITY, limit=SKIP_ONE_ENTITY)

        # Assert
        assert len(results) == 1
        assert results[0].value == TEST_VALUE_20

    async def test_find_returns_deepcopy(self) -> None:
        """Test find returns deep copy (entities are independent)."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity = ConcreteEntity(name="Original Name", value=100)
        await repository.insert(entity=entity)

        # Act
        results = await repository.find()
        result_entity = results[0]
        result_entity.name = "Modified Name"

        # Assert
        stored_entity = repository._entities[entity.id]  # pyright: ignore[reportPrivateUsage]
        assert stored_entity.name == "Original Name"
        assert result_entity.name == "Modified Name"

    async def test_find_with_session(self) -> None:
        """Test find works with session parameter."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity1 = ConcreteEntity(name="Entity 1", value=TEST_VALUE_10)
        entity2 = ConcreteEntity(name="Entity 2", value=TEST_VALUE_20)
        await repository.insert(entity=entity1)
        await repository.insert(entity=entity2)

        # Act
        results = await repository.find(session=None)

        # Assert
        assert len(results) == EXPECTED_ENTITY_COUNT_2

    async def test_find_normal_usage(self) -> None:
        """Test find normal usage with Beanie query expression syntax."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity1 = ConcreteEntity(name="Entity 1", value=TEST_VALUE_10)
        entity2 = ConcreteEntity(name="Entity 2", value=TEST_VALUE_20)
        await repository.insert(entity=entity1)
        await repository.insert(entity=entity2)

        # Act
        results = await repository.find(ConcreteDocument.value == TEST_VALUE_10)

        # Assert
        assert len(results) == 1
        assert results[0].id == entity1.id

    async def test_find_with_beanie_in_operator(self) -> None:
        """Test find with Beanie's In operator."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity1 = ConcreteEntity(name="Entity 1", category="A", value=TEST_VALUE_10)
        entity2 = ConcreteEntity(name="Entity 2", category="B", value=TEST_VALUE_20)
        entity3 = ConcreteEntity(name="Entity 3", category="C", value=TEST_VALUE_30)
        await repository.insert(entity=entity1)
        await repository.insert(entity=entity2)
        await repository.insert(entity=entity3)

        # Act
        results = await repository.find(In(ConcreteDocument.category, ["A", "C"]))

        # Assert
        assert len(results) == EXPECTED_ENTITY_COUNT_2
        assert {r.id for r in results} == {entity1.id, entity3.id}

    async def test_find_with_beanie_notin_operator(self) -> None:
        """Test find with Beanie's NotIn operator."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity1 = ConcreteEntity(name="Entity 1", category="A", value=TEST_VALUE_10)
        entity2 = ConcreteEntity(name="Entity 2", category="B", value=TEST_VALUE_20)
        entity3 = ConcreteEntity(name="Entity 3", category="C", value=TEST_VALUE_30)
        await repository.insert(entity=entity1)
        await repository.insert(entity=entity2)
        await repository.insert(entity=entity3)

        # Act
        results = await repository.find(NotIn(ConcreteDocument.category, ["B"]))

        # Assert
        assert len(results) == EXPECTED_ENTITY_COUNT_2
        assert {r.id for r in results} == {entity1.id, entity3.id}

    async def test_find_with_beanie_regex_operator(self) -> None:
        """Test find with Beanie's RegEx operator."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity1 = ConcreteEntity(name="Entity One", value=TEST_VALUE_10)
        entity2 = ConcreteEntity(name="Entity Two", value=TEST_VALUE_20)
        entity3 = ConcreteEntity(name="Something Else", value=TEST_VALUE_30)
        await repository.insert(entity=entity1)
        await repository.insert(entity=entity2)
        await repository.insert(entity=entity3)

        # Act
        results = await repository.find(RegEx(ConcreteDocument.name, "^Entity", "i"))

        # Assert
        assert len(results) == EXPECTED_ENTITY_COUNT_2
        assert {r.id for r in results} == {entity1.id, entity2.id}

    async def test_find_with_beanie_exists_operator(self) -> None:
        """Test find with Beanie's Exists operator."""
        # Arrange
        repository = ConcreteRepositoryInMemory()
        entity1 = ConcreteEntity(name="Entity 1", category="A", value=TEST_VALUE_10)
        entity2 = ConcreteEntity(name="Entity 2", category=None, value=TEST_VALUE_20)
        await repository.insert(entity=entity1)
        await repository.insert(entity=entity2)

        # Act
        results = await repository.find(Exists(ConcreteDocument.category, True))

        # Assert
        assert len(results) == 1
        assert results[0].id == entity1.id
