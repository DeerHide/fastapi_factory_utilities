"""Mocker for ODM plugin.

Objectives:
- Provide an implementation in memory for the Repository Class.
- This RepositoryInMemory must be a subclass of the AbstractRepository class.
- This RepositoryInMemory must be a singleton with all the data in memory.
- This RepositoryInMemory must accept generic like the real one.
"""

import datetime
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
        *args: Mapping[str, Any] | bool,
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
            *args: Filter arguments. Can be Mapping for field filters or bool for boolean filters.
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
                    initial_list = [
                        entity
                        for entity in initial_list
                        if all(getattr(entity, key) == value for key, value in arg.items())
                    ]
                else:
                    # arg is a bool filter - if False, filter out all entities
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
