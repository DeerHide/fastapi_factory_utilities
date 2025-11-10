"""Provides the abstract classes for the repositories."""

import datetime
from abc import ABC
from collections.abc import AsyncGenerator, Callable, Mapping
from contextlib import asynccontextmanager
from typing import Any, Generic, TypeVar, get_args
from uuid import UUID

from beanie import SortDirection
from pydantic import BaseModel
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo.results import DeleteResult

from .documents import BaseDocument
from .exceptions import OperationError, UnableToCreateEntityDueToDuplicateKeyError

DocumentGenericType = TypeVar("DocumentGenericType", bound=BaseDocument)  # pylint: disable=invalid-name
EntityGenericType = TypeVar("EntityGenericType", bound=BaseModel)  # pylint: disable=invalid-name


def managed_session() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to manage the session.

    It will introspect the function arguments and check if the session is passed as a keyword argument.
    If it is not, it will create a new session and pass it to the function.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if "session" in kwargs:
                return await func(*args, **kwargs)

            async with args[0].get_session() as session:
                return await func(*args, **kwargs, session=session)

        return wrapper

    return decorator


class AbstractRepository(ABC, Generic[DocumentGenericType, EntityGenericType]):
    """Abstract class for the repository."""

    def __init__(self, database: AsyncDatabase[Any]) -> None:
        """Initialize the repository."""
        super().__init__()
        self._database: AsyncDatabase[Any] = database
        # Retrieve the generic concrete types
        generic_args: tuple[Any, ...] = get_args(self.__orig_bases__[0])  # type: ignore
        self._document_type: type[DocumentGenericType] = generic_args[0]
        self._entity_type: type[EntityGenericType] = generic_args[1]

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncClientSession, None]:
        """Yield a new session."""
        session: AsyncClientSession | None = None
        try:
            session = self._database.client.start_session()
            yield session
        except PyMongoError as error:
            raise OperationError(f"Failed to create session: {error}") from error
        finally:
            if session is not None:
                await session.end_session()

    @managed_session()
    async def insert(self, entity: EntityGenericType, session: AsyncClientSession | None = None) -> EntityGenericType:
        """Insert the entity into the database.

        Args:
            entity (EntityGenericType): The entity to insert.
            session (AsyncIOMotorClientSession | None): The session to use. Defaults to None. (managed by decorator)

        Returns:
            EntityGenericType: The entity created.

        Raises:
            ValueError: If the entity cannot be created from the document.
            UnableToCreateEntityDueToDuplicateKeyError: If the entity cannot be created due to a duplicate key error.
            OperationError: If the operation fails.
        """
        insert_time: datetime.datetime = datetime.datetime.now(tz=datetime.UTC)
        try:
            entity_dump: dict[str, Any] = entity.model_dump()
            entity_dump["created_at"] = insert_time
            entity_dump["updated_at"] = insert_time
            document: DocumentGenericType = self._document_type(**entity_dump)

        except ValueError as error:
            raise ValueError(f"Failed to create document from entity: {error}") from error

        try:
            document_created: DocumentGenericType = await document.insert(session=session)
        except DuplicateKeyError as error:
            raise UnableToCreateEntityDueToDuplicateKeyError(f"Failed to insert document: {error}") from error
        except PyMongoError as error:
            raise OperationError(f"Failed to insert document: {error}") from error

        try:
            entity_created: EntityGenericType = self._entity_type(**document_created.model_dump())
        except ValueError as error:
            raise ValueError(f"Failed to create entity from document: {error}") from error

        return entity_created

    @managed_session()
    async def update(self, entity: EntityGenericType, session: AsyncClientSession | None = None) -> EntityGenericType:
        """Update the entity in the database.

        Args:
            entity (EntityGenericType): The entity to update.
            session (AsyncIOMotorClientSession | None): The session to use. Defaults to None. (managed by decorator)

        Returns:
            EntityGenericType: The updated entity.

        Raises:
            ValueError: If the entity cannot be created from the document.
            OperationError: If the operation fails.
        """
        update_time: datetime.datetime = datetime.datetime.now(tz=datetime.UTC)
        try:
            entity_dump: dict[str, Any] = entity.model_dump()
            entity_dump["updated_at"] = update_time
            document: DocumentGenericType = self._document_type(**entity_dump)

        except ValueError as error:
            raise ValueError(f"Failed to create document from entity: {error}") from error

        try:
            document_updated: DocumentGenericType = await document.save(session=session)
        except PyMongoError as error:
            raise OperationError(f"Failed to update document: {error}") from error

        try:
            entity_updated: EntityGenericType = self._entity_type(**document_updated.model_dump())
        except ValueError as error:
            raise ValueError(f"Failed to create entity from document: {error}") from error

        return entity_updated

    @managed_session()
    async def get_one_by_id(
        self,
        entity_id: UUID,
        session: AsyncClientSession | None = None,
    ) -> EntityGenericType | None:
        """Get the entity by its ID.

        Args:
            entity_id (UUID): The ID of the entity.
            session (AsyncIOMotorClientSession | None): The session to use. Defaults to None. (managed by decorator)

        Returns:
            EntityGenericType | None: The entity or None if not found.

        Raises:
            OperationError: If the operation fails.

        """
        try:
            document: DocumentGenericType | None = await self._document_type.get(document_id=entity_id, session=session)
        except PyMongoError as error:
            raise OperationError(f"Failed to get document: {error}") from error

        # If no document is found, return None
        if document is None:
            return None

        # Convert the document to an entity
        try:
            entity: EntityGenericType = self._entity_type(**document.model_dump())
        except ValueError as error:
            raise ValueError(f"Failed to create entity from document: {error}") from error

        return entity

    @managed_session()
    async def delete_one_by_id(
        self, entity_id: UUID, raise_if_not_found: bool = False, session: AsyncClientSession | None = None
    ) -> None:
        """Delete a document by its ID.

        Args:
            entity_id (UUID): The ID of the entity.
            raise_if_not_found (bool, optional): Raise an exception if the document is not found. Defaults to False.
            session (AsyncIOMotorClientSession | None, optional): The session to use.
            Defaults to None. (managed by decorator)

        Raises:
            ValueError: If the document is not found and raise_if_not_found is True.
            OperationError: If the operation fails.

        """
        try:
            document_to_delete: DocumentGenericType | None = await self._document_type.get(
                document_id=entity_id, session=session
            )
        except PyMongoError as error:
            raise OperationError(f"Failed to get document to delete: {error}") from error

        if document_to_delete is None:
            if raise_if_not_found:
                raise ValueError(f"Failed to find document with ID {entity_id}")
            return

        try:
            delete_result: DeleteResult | None = await document_to_delete.delete()
        except PyMongoError as error:
            raise OperationError(f"Failed to delete document: {error}") from error

        if delete_result is not None and delete_result.deleted_count == 1 and delete_result.acknowledged:
            return

        raise OperationError("Failed to delete document.")

    @managed_session()
    async def find(  # noqa: PLR0913
        self,
        *args: Mapping[str, Any] | bool,
        projection_model: None = None,
        skip: int | None = None,
        limit: int | None = None,
        sort: None | str | list[tuple[str, SortDirection]] = None,
        session: AsyncClientSession | None = None,
        ignore_cache: bool = False,
        fetch_links: bool = False,
        lazy_parse: bool = False,
        nesting_depth: int | None = None,
        nesting_depths_per_field: dict[str, int] | None = None,
        **pymongo_kwargs: Any,
    ) -> list[EntityGenericType]:
        """Find documents in the database.

        Args:
            *args: The arguments to pass to the find method.
            projection_model: The projection model to use.
            skip: The number of documents to skip.
            limit: The number of documents to return.
            sort: The sort order.
            session: The session to use.
            ignore_cache: Whether to ignore the cache.
            fetch_links: Whether to fetch links.
            lazy_parse: Whether to lazy parse the documents.
            nesting_depth: The nesting depth.
            nesting_depths_per_field: The nesting depths per field.
            **pymongo_kwargs: Additional keyword arguments to pass to the find method.

        Returns:
            list[EntityGenericType]: The list of entities.

        Raises:
            OperationError: If the operation fails.
            ValueError: If the entity cannot be created from the document.
        """
        try:
            documents: list[DocumentGenericType] = await self._document_type.find(
                *args,
                projection_model=projection_model,
                skip=skip,
                limit=limit,
                sort=sort,
                session=session,
                ignore_cache=ignore_cache,
                fetch_links=fetch_links,
                lazy_parse=lazy_parse,
                nesting_depth=nesting_depth,
                nesting_depths_per_field=nesting_depths_per_field,
                **pymongo_kwargs,
            ).to_list()
        except PyMongoError as error:
            raise OperationError(f"Failed to find documents: {error}") from error

        try:
            entities: list[EntityGenericType] = [self._entity_type(**document.model_dump()) for document in documents]
        except ValueError as error:
            raise ValueError(f"Failed to create entity from document: {error}") from error

        return entities
