"""Lock hook for continuous schema-migration sweeps."""

from __future__ import annotations

import datetime
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError

SCHEMA_MIGRATION_LOCKS_COLLECTION = "schema_migration_locks"
DEFAULT_LEASE_TTL = datetime.timedelta(seconds=60)


@runtime_checkable
class SchemaMigrationLock(Protocol):
    """Exclusive owner for a collection sweep.

    ``key`` is the collection name. ``owner`` identifies the process
    (typically ``hostname:pid``). Only one live owner may sweep a key.
    """

    async def try_acquire(self, *, key: str, owner: str) -> bool:
        """Acquire the lock when free, expired, or already held by ``owner``."""

    async def renew(self, *, key: str, owner: str) -> bool:
        """Extend the lease when ``owner`` still holds ``key``."""

    async def release(self, *, key: str, owner: str) -> None:
        """Release the lock only when ``owner`` matches."""


class AlwaysAcquireMigrationLock:
    """Test / single-process lock that always grants ownership."""

    async def try_acquire(self, *, key: str, owner: str) -> bool:
        """Always acquire.

        Args:
            key: Lock key (unused).
            owner: Owner id (unused).

        Returns:
            Always ``True``.
        """
        return True

    async def renew(self, *, key: str, owner: str) -> bool:
        """Always renew.

        Args:
            key: Lock key (unused).
            owner: Owner id (unused).

        Returns:
            Always ``True``.
        """
        return True

    async def release(self, *, key: str, owner: str) -> None:
        """No-op release.

        Args:
            key: Lock key (unused).
            owner: Owner id (unused).
        """
        return None


class MongoSchemaMigrationLock:
    """Mongo lease documents in ``schema_migration_locks``.

    Each document is ``{_id: collection, owner, expires_at}``. Acquire matches a
    missing lock, an expired lock, or the same owner. Release deletes only when
    ``owner`` matches.
    """

    def __init__(
        self,
        database: AsyncDatabase[Any],
        *,
        collection_name: str = SCHEMA_MIGRATION_LOCKS_COLLECTION,
        lease_ttl: datetime.timedelta = DEFAULT_LEASE_TTL,
        clock: Callable[[], datetime.datetime] | None = None,
    ) -> None:
        """Initialize the Mongo lease lock.

        Args:
            database: Database that holds the lease collection.
            collection_name: Lease collection name.
            lease_ttl: How long a lease stays live without renew.
            clock: Injectable UTC clock for tests.
        """
        self._collection: AsyncCollection[Any] = database[collection_name]
        self._lease_ttl: datetime.timedelta = lease_ttl
        self._clock: Callable[[], datetime.datetime] = clock or (lambda: datetime.datetime.now(tz=datetime.UTC))

    async def try_acquire(self, *, key: str, owner: str) -> bool:
        """Acquire when missing, expired, or already owned by ``owner``.

        Args:
            key: Collection name used as the lease ``_id``.
            owner: Process identity claiming the lease.

        Returns:
            ``True`` when this owner holds the lease after the call.
        """
        now: datetime.datetime = self._clock()
        expires_at: datetime.datetime = now + self._lease_ttl

        updated: dict[str, Any] | None = await self._collection.find_one_and_update(
            {
                "_id": key,
                "$or": [
                    {"expires_at": {"$lte": now}},
                    {"owner": owner},
                ],
            },
            {"$set": {"owner": owner, "expires_at": expires_at}},
        )
        if updated is not None:
            return True

        try:
            await self._collection.insert_one({"_id": key, "owner": owner, "expires_at": expires_at})
        except DuplicateKeyError:
            return False
        return True

    async def renew(self, *, key: str, owner: str) -> bool:
        """Extend ``expires_at`` when ``owner`` still holds ``key``.

        Args:
            key: Collection name used as the lease ``_id``.
            owner: Process identity that must match the stored owner.

        Returns:
            ``True`` when the lease was renewed.
        """
        now: datetime.datetime = self._clock()
        expires_at: datetime.datetime = now + self._lease_ttl
        updated: dict[str, Any] | None = await self._collection.find_one_and_update(
            {"_id": key, "owner": owner},
            {"$set": {"expires_at": expires_at}},
        )
        return updated is not None

    async def release(self, *, key: str, owner: str) -> None:
        """Delete the lease document only when ``owner`` matches.

        Args:
            key: Collection name used as the lease ``_id``.
            owner: Process identity that must match the stored owner.
        """
        await self._collection.delete_one({"_id": key, "owner": owner})

    async def get_owner(self, *, key: str) -> str | None:
        """Return the stored owner for logging after a failed acquire.

        Args:
            key: Collection name used as the lease ``_id``.

        Returns:
            The owner string, or ``None`` when no lease document exists.
        """
        document: dict[str, Any] | None = await self._collection.find_one({"_id": key})
        if document is None:
            return None
        owner: Any = document.get("owner")
        return str(owner) if owner is not None else None
