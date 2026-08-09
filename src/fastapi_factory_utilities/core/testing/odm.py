"""MongoDB test doubles: mongomock via pymongo-async-mock at the driver seam.

Fakes ``AsyncMongoClient`` so Beanie / ``AbstractRepository`` run for real.
Transactions stay container-only — mongomock has no sessions.
"""

from collections.abc import Callable, Sequence
from types import MethodType
from typing import Any
from uuid import uuid4

from beanie import Document, init_beanie
from pymongo.asynchronous.database import AsyncDatabase

from fastapi_factory_utilities.core.testing.contracts.models import ContractEntity


class _FalsyNoOpSession:
    """Session stand-in that slips past mongomock's truthy ``if session:`` guards.

    ``AbstractRepository.get_session`` calls ``client.start_session()`` synchronously
    and later ``await session.end_session()``. ``managed_session`` always passes
    ``session=`` into Beanie calls. mongomock raises ``NotImplementedError`` when
    ``session`` is truthy, so ``__bool__`` returns ``False`` while the repository
    code path stays intact.
    """

    def __bool__(self) -> bool:
        """Return False so mongomock treats the session as absent."""
        return False

    async def end_session(self) -> None:
        """No-op end_session matching pymongo's async API."""
        return None


def _patch_async_mongo_mock_client(client: Any) -> Any:
    """Add missing ``aconnect`` / ``aclose`` / ``start_session`` to a mock client.

    ``AsyncMongoMockClient.__getattr__`` falls through to ``get_database(name)``,
    so missing methods silently return database objects. Patch explicitly.
    """

    async def _aconnect(self: Any) -> Any:
        return self

    async def _aclose(self: Any) -> None:  # pylint: disable=unused-argument
        return None

    def _start_session(self: Any, **_kwargs: Any) -> _FalsyNoOpSession:  # pylint: disable=unused-argument
        # Sync: matches AbstractRepository.get_session (does not await start_session).
        return _FalsyNoOpSession()

    client.aconnect = MethodType(_aconnect, client)
    client.aclose = MethodType(_aclose, client)
    client.start_session = MethodType(_start_session, client)
    return client


def _patch_async_mongo_mock_database(database: Any) -> Any:
    """Make Beanie's ``init_beanie`` kwargs acceptable to mongomock.

    Beanie calls ``list_collection_names(authorizedCollections=True, nameOnly=True)``;
    mongomock rejects those kwargs. Strip them and forward the rest.
    """
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


def build_mongomock_client() -> Any:
    """Build a patched ``AsyncMongoMockClient`` suitable for Beanie / repositories.

    Returns:
        An async Mongo client backed by mongomock.

    Raises:
        ImportError: When ``pymongo-async-mock`` is not installed.
    """
    try:
        from pymongo_async_mock import (  # pylint: disable=import-outside-toplevel  # noqa: PLC0415
            AsyncMongoMockClient,
        )
    except ImportError as error:
        raise ImportError(
            "pymongo-async-mock is required for MongoDB test doubles. "
            "Install with: pip install 'fastapi_factory_utilities[testing]'",
        ) from error
    return _patch_async_mongo_mock_client(AsyncMongoMockClient())


def build_mongomock_database(database_name: str | None = None) -> AsyncDatabase[Any]:
    """Build a mongomock-backed ``AsyncDatabase``.

    Args:
        database_name: Optional database name; a unique name is generated when omitted.

    Returns:
        An async database handle.
    """
    client = build_mongomock_client()
    name = database_name or f"test_{uuid4()!s}"
    return _patch_async_mongo_mock_database(client[name])


def mongomock_repository_factory(
    document_models: Sequence[type[Document]],
) -> Callable[[], Any]:
    """Return a factory that builds a mongomock database with ``document_models`` init'd.

    Args:
        document_models: Beanie document classes to initialize.

    Returns:
        A zero-arg async callable yielding a database after ``init_beanie``.
    """

    async def _factory() -> AsyncDatabase[Any]:
        database = build_mongomock_database()
        await init_beanie(database=database, document_models=list(document_models))
        return database

    return _factory


def make_contract_entity(**kwargs: Any) -> ContractEntity:
    """Build a :class:`ContractEntity` for contract tests.

    Args:
        **kwargs: Optional ``id``, ``my_field``, ``category``.

    Returns:
        A new contract entity.
    """
    return ContractEntity(
        id=kwargs.get("id", uuid4()),
        my_field=kwargs.get("my_field", "field"),
        category=kwargs.get("category"),
    )
