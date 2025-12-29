"""Mocker for ODM plugin.

Objectives:
- Provide an implementation in memory for the Repository Class.
- This RepositoryInMemory must be a subclass of the AbstractRepository class.
- This RepositoryInMemory must be a singleton with all the data in memory.
- This RepositoryInMemory must accept generic like the real one.
"""

import datetime
import re
from abc import ABC
from collections.abc import AsyncGenerator, Callable, Mapping
from contextlib import asynccontextmanager
from copy import deepcopy
from functools import wraps
from typing import Any, Generic, TypeVar, get_args
from uuid import UUID

from beanie import SortDirection

from fastapi_factory_utilities.core.plugins.odm_plugin.documents import BaseDocument
from fastapi_factory_utilities.core.plugins.odm_plugin.exceptions import (
    OperationError,
    UnableToCreateEntityDueToDuplicateKeyError,
)
from fastapi_factory_utilities.core.plugins.odm_plugin.helpers import PersistedEntity

DocumentGenericType = TypeVar("DocumentGenericType", bound=BaseDocument)  # pylint: disable=invalid-name
EntityGenericType = TypeVar("EntityGenericType", bound=PersistedEntity)  # pylint: disable=invalid-name


class MockQueryField(str):
    """Mock field for query expressions without Beanie initialization.

    This allows Document fields to be accessed for query expressions
    (e.g., Document.field == value) without requiring full Beanie initialization.

    Inherits from str to be hashable and compatible with Beanie operators.
    """

    def __new__(cls, field_name: str) -> "MockQueryField":
        """Create a new MockQueryField instance.

        Args:
            field_name: The name of the field.

        Returns:
            A new MockQueryField instance.
        """
        instance = str.__new__(cls, field_name)
        return instance

    @property
    def field_name(self) -> str:
        """Get the field name.

        Returns:
            The field name as a string.
        """
        return str(self)

    def __hash__(self) -> int:
        """Return hash of the field name.

        Returns:
            Hash of the field name string.
        """
        return hash(str(self))

    def __eq__(self, other: Any) -> dict[str, Any]:  # type: ignore[override]
        """Support equality comparison (field == value).

        Args:
            other: The value to compare against.

        Returns:
            A dictionary filter that can be used by the in-memory repository.
        """
        return {self.field_name: other}

    def __ne__(self, other: Any) -> dict[str, Any]:  # type: ignore[override]
        """Support inequality comparison (field != value).

        Args:
            other: The value to compare against.

        Returns:
            A dictionary filter representation.
        """
        return {self.field_name: {"$ne": other}}

    def __lt__(self, other: Any) -> dict[str, Any]:  # type: ignore[override]
        """Support less than comparison (field < value).

        Args:
            other: The value to compare against.

        Returns:
            A dictionary filter representation.
        """
        return {self.field_name: {"$lt": other}}

    def __le__(self, other: Any) -> dict[str, Any]:  # type: ignore[override]
        """Support less than or equal comparison (field <= value).

        Args:
            other: The value to compare against.

        Returns:
            A dictionary filter representation.
        """
        return {self.field_name: {"$lte": other}}

    def __gt__(self, other: Any) -> dict[str, Any]:  # type: ignore[override]
        """Support greater than comparison (field > value).

        Args:
            other: The value to compare against.

        Returns:
            A dictionary filter representation.
        """
        return {self.field_name: {"$gt": other}}

    def __ge__(self, other: Any) -> dict[str, Any]:  # type: ignore[override]
        """Support greater than or equal comparison (field >= value).

        Args:
            other: The value to compare against.

        Returns:
            A dictionary filter representation.
        """
        return {self.field_name: {"$gte": other}}


def _setup_document_fields_for_mock(document_type: type[BaseDocument]) -> None:
    """Set up document fields to support query expressions without Beanie initialization.

    This function adds MockQueryField descriptors to the document class for each field,
    allowing query expressions like `Document.field == value` to work without requiring
    full Beanie initialization.

    Args:
        document_type: The document class to set up.
    """
    # Get all fields from the Pydantic model
    for field_name in document_type.model_fields:
        # Only set up fields that don't already exist as class attributes
        # (to avoid overriding Beanie's setup if it's already done)
        if not hasattr(document_type, field_name) or isinstance(getattr(document_type, field_name), property):
            setattr(document_type, field_name, MockQueryField(field_name))


def managed_session() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to manage the session.

    It will introspect the function arguments and check if the session is passed as a keyword argument.
    If it is not, it will create a new session and pass it to the function.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if "session" in kwargs:
                return await func(*args, **kwargs)

            async with args[0].get_session() as session:
                return await func(*args, **kwargs, session=session)

        return wrapper

    return decorator


class AbstractRepositoryInMemory(ABC, Generic[DocumentGenericType, EntityGenericType]):
    """Abstract repository in memory for testing purposes.

    This class provides an in-memory implementation of the repository pattern,
    allowing tests to run without requiring a real database connection.
    """

    def __init__(self, entities: list[EntityGenericType] | None = None) -> None:
        """Initialize the repository.

        Args:
            entities: Optional list of entities to pre-populate the repository with.
        """
        self._entities: dict[UUID, EntityGenericType] = {}
        if entities is not None:
            for entity in entities:
                self._entities[entity.id] = entity
        # Retrieve the generic concrete types
        generic_args: tuple[Any, ...] = get_args(self.__orig_bases__[0])  # type: ignore
        self._document_type: type[DocumentGenericType] = generic_args[0]
        self._entity_type: type[EntityGenericType] = generic_args[1]

        # Set up document fields to support query expressions without Beanie initialization
        _setup_document_fields_for_mock(self._document_type)

    def _matches_filter(  # noqa: PLR0911, PLR0912
        self, entity: EntityGenericType, filter_dict: Mapping[str, Any]
    ) -> bool:
        """Check if an entity matches a filter dictionary.

        Supports both simple equality filters and MongoDB-style operator filters.

        Args:
            entity: The entity to check.
            filter_dict: The filter dictionary (e.g., {"field": value} or {"field": {"$lt": 5}}).

        Returns:
            True if the entity matches all filter conditions, False otherwise.
        """
        for key, value in filter_dict.items():
            entity_value: Any = getattr(entity, key)

            # Check if value is a dict with MongoDB operators
            if isinstance(value, dict):
                for op_key, op_value in value.items():
                    operator: str = str(op_key)
                    if operator == "$ne":
                        if entity_value == op_value:
                            return False
                    elif operator == "$lt":
                        if entity_value >= op_value:
                            return False
                    elif operator == "$lte":
                        if entity_value > op_value:
                            return False
                    elif operator == "$gt":
                        if entity_value <= op_value:
                            return False
                    elif operator == "$gte":
                        if entity_value < op_value:
                            return False
                    elif operator == "$in":
                        if entity_value not in op_value:
                            return False
                    elif operator == "$nin":
                        if entity_value in op_value:
                            return False
                    elif operator == "$regex":
                        # Get options from the filter dict (might be in same dict)
                        options_str: str = (
                            filter_dict.get(key, {}).get("$options", "")
                            if isinstance(filter_dict.get(key), dict)
                            else ""
                        )
                        flags: int = 0
                        if "i" in options_str:
                            flags |= re.IGNORECASE
                        if "m" in options_str:
                            flags |= re.MULTILINE
                        if "s" in options_str:
                            flags |= re.DOTALL
                        pattern = re.compile(str(op_value), flags)
                        if not pattern.search(str(entity_value)):
                            return False
                    elif operator == "$exists":
                        # Check if field exists (not None) or doesn't exist (is None)
                        field_exists = entity_value is not None
                        if op_value != field_exists:
                            return False
                    elif operator == "$all":
                        # All values must be in the entity value (which should be a list/sequence)
                        if not isinstance(entity_value, (list, tuple, set)):
                            return False
                        entity_set: set[Any] = set(entity_value) if not isinstance(entity_value, set) else entity_value
                        if not all(item in entity_set for item in op_value):
                            return False
                    elif operator == "$size":
                        # Check the size of the entity value (which should be a list/sequence)
                        if not hasattr(entity_value, "__len__"):
                            return False
                        if len(entity_value) != op_value:
                            return False
                    elif operator == "$options":
                        # Options is handled together with $regex
                        continue
                    else:
                        # Unknown operator, treat as inequality
                        return False
            # Simple equality check
            elif entity_value != value:
                return False

        return True

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[None, None]:
        """Get a session context manager.

        Yields:
            None: No actual session is needed for in-memory operations.
        """
        yield

    @managed_session()
    async def insert(self, entity: EntityGenericType, session: None = None) -> EntityGenericType:  # pylint: disable=unused-argument
        """Insert an entity into the repository.

        Args:
            entity: The entity to insert.
            session: The session to use (unused in memory implementation).

        Returns:
            The created entity with timestamps set.

        Raises:
            UnableToCreateEntityDueToDuplicateKeyError: If an entity with the same ID already exists.
        """
        insert_time: datetime.datetime = datetime.datetime.now(tz=datetime.UTC)
        entity_dump: dict[str, Any] = entity.model_dump()
        entity_dump["created_at"] = insert_time
        entity_dump["updated_at"] = insert_time
        entity_created: EntityGenericType = self._entity_type(**entity_dump)

        if entity_created.id in self._entities:
            raise UnableToCreateEntityDueToDuplicateKeyError(f"Entity with ID {entity_created.id} already exists")

        self._entities[entity_created.id] = entity_created
        return entity_created

    @managed_session()
    async def update(self, entity: EntityGenericType, session: None = None) -> EntityGenericType:  # pylint: disable=unused-argument
        """Update an entity in the repository.

        Args:
            entity: The entity to update.
            session: The session to use (unused in memory implementation).

        Returns:
            The updated entity with updated_at timestamp refreshed.

        Raises:
            OperationError: If the entity does not exist in the repository.
        """
        update_time: datetime.datetime = datetime.datetime.now(tz=datetime.UTC)
        entity_dump: dict[str, Any] = entity.model_dump()
        entity_dump["updated_at"] = update_time
        entity_updated: EntityGenericType = self._entity_type(**entity_dump)

        if entity_updated.id not in self._entities:
            raise OperationError(f"Entity with ID {entity_updated.id} not found")

        self._entities[entity_updated.id] = entity_updated
        return entity_updated

    @managed_session()
    async def get_one_by_id(self, entity_id: UUID, session: None = None) -> EntityGenericType | None:  # pylint: disable=unused-argument
        """Get an entity by its ID.

        Args:
            entity_id: The ID of the entity to retrieve.
            session: The session to use (unused in memory implementation).

        Returns:
            The entity if found, None otherwise.
        """
        return self._entities.get(entity_id, None)

    @managed_session()
    async def delete_one_by_id(self, entity_id: UUID, raise_if_not_found: bool = False, session: None = None) -> None:  # pylint: disable=unused-argument
        """Delete an entity by its ID.

        Args:
            entity_id: The ID of the entity to delete.
            raise_if_not_found: If True, raises OperationError when entity is not found.
            session: The session to use (unused in memory implementation).

        Raises:
            OperationError: If the entity is not found and raise_if_not_found is True.
        """
        if entity_id not in self._entities:
            if raise_if_not_found:
                raise OperationError(f"Entity with ID {entity_id} not found")
            return
        self._entities.pop(entity_id)

    @managed_session()
    async def find(  # noqa: PLR0913  # pylint: disable=unused-argument
        self,
        *args: Any,
        projection_model: None = None,
        skip: int | None = None,
        limit: int | None = None,
        sort: None | str | list[tuple[str, SortDirection]] = None,
        session: None = None,
        ignore_cache: bool = False,
        fetch_links: bool = False,
        lazy_parse: bool = False,
        nesting_depth: int | None = None,
        nesting_depths_per_field: dict[str, int] | None = None,
        **pymongo_kwargs: Any,
    ) -> list[EntityGenericType]:
        """Find entities in the repository.

        Args:
            *args: Filter arguments. Can be Mapping for field filters, bool for boolean filters,
                   or any other type (treated as boolean).
            projection_model: Unused in memory implementation.
            skip: Number of entities to skip.
            limit: Maximum number of entities to return.
            sort: Sort order as a list of tuples (field_name, SortDirection).
            session: The session to use (unused in memory implementation).
            ignore_cache: Unused in memory implementation.
            fetch_links: Unused in memory implementation.
            lazy_parse: Unused in memory implementation.
            nesting_depth: Unused in memory implementation.
            nesting_depths_per_field: Unused in memory implementation.
            **pymongo_kwargs: Unused in memory implementation.

        Returns:
            A list of entities matching the filters, sorted, skipped, and limited as specified.
            Returns deep copies to prevent accidental modification of stored entities.
        """
        initial_list: list[EntityGenericType] = deepcopy(list(self._entities.values()))

        # Apply the filters
        if args:
            for arg in args:
                if isinstance(arg, Mapping):
                    # Dictionary filter or Beanie operator (both are Mappings)
                    # Supports: {"field": value}, {"field": {"$op": value}},
                    # or Beanie operators like In(), NotIn(), etc.
                    filter_arg: Mapping[str, Any] = arg
                    initial_list = [entity for entity in initial_list if self._matches_filter(entity, filter_arg)]
                elif isinstance(arg, bool):
                    # Boolean filter: if False, filter out all entities
                    initial_list = [entity for entity in initial_list if arg]
                else:
                    # Treat any other type (including Beanie query expressions) as boolean
                    # This handles cases where query expressions evaluate to bool
                    initial_list = [entity for entity in initial_list if arg]

        # Apply the sorting
        if sort:
            initial_list = sorted(
                initial_list, key=lambda x: x.model_dump()[sort[0][0]], reverse=sort[0][1] == SortDirection.DESCENDING
            )

        # Apply the skip
        if skip:
            initial_list = initial_list[skip:]

        # Apply the limit
        if limit:
            initial_list = initial_list[:limit]

        return initial_list
