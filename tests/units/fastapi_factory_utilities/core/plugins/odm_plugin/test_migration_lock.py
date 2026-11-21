"""Unit tests for MongoSchemaMigrationLock."""

from __future__ import annotations

import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pymongo.errors import DuplicateKeyError

from fastapi_factory_utilities.core.plugins.odm_plugin.migration_lock import (
    MongoSchemaMigrationLock,
)


def _fixed_clock(moment: datetime.datetime) -> Any:
    """Return a clock that always yields ``moment``."""

    def _clock() -> datetime.datetime:
        return moment

    return _clock


class TestMongoSchemaMigrationLock:
    """Tests for the default Mongo lease."""

    @pytest.mark.asyncio
    async def test_acquire_inserts_when_missing(self) -> None:
        """A missing lease is created via insert."""
        now = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
        collection = MagicMock()
        collection.find_one_and_update = AsyncMock(return_value=None)
        collection.insert_one = AsyncMock(return_value=None)
        database = MagicMock()
        database.__getitem__ = MagicMock(return_value=collection)

        lock = MongoSchemaMigrationLock(database, lease_ttl=datetime.timedelta(seconds=30), clock=_fixed_clock(now))
        assert await lock.try_acquire(key="customers", owner="host:1") is True
        collection.insert_one.assert_awaited_once_with(
            {"_id": "customers", "owner": "host:1", "expires_at": now + datetime.timedelta(seconds=30)}
        )

    @pytest.mark.asyncio
    async def test_second_owner_refused_while_lease_live(self) -> None:
        """A live lease held by another owner refuses acquire."""
        now = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
        collection = MagicMock()
        collection.find_one_and_update = AsyncMock(return_value=None)
        collection.insert_one = AsyncMock(side_effect=DuplicateKeyError("dup"))
        database = MagicMock()
        database.__getitem__ = MagicMock(return_value=collection)

        lock = MongoSchemaMigrationLock(database, clock=_fixed_clock(now))
        assert await lock.try_acquire(key="customers", owner="host:2") is False

    @pytest.mark.asyncio
    async def test_same_owner_can_reacquire(self) -> None:
        """The same owner refreshes a live lease via find_one_and_update."""
        now = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
        collection = MagicMock()
        collection.find_one_and_update = AsyncMock(
            return_value={"_id": "customers", "owner": "host:1", "expires_at": now}
        )
        collection.insert_one = AsyncMock()
        database = MagicMock()
        database.__getitem__ = MagicMock(return_value=collection)

        lock = MongoSchemaMigrationLock(database, clock=_fixed_clock(now))
        assert await lock.try_acquire(key="customers", owner="host:1") is True
        collection.insert_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_expired_lease_can_be_taken(self) -> None:
        """An expired lease matches the update filter and is taken."""
        now = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
        collection = MagicMock()
        collection.find_one_and_update = AsyncMock(
            return_value={"_id": "customers", "owner": "host:old", "expires_at": now - datetime.timedelta(seconds=1)}
        )
        database = MagicMock()
        database.__getitem__ = MagicMock(return_value=collection)

        lock = MongoSchemaMigrationLock(database, clock=_fixed_clock(now))
        assert await lock.try_acquire(key="customers", owner="host:new") is True
        filt = collection.find_one_and_update.await_args.args[0]
        assert filt["_id"] == "customers"
        assert {"expires_at": {"$lte": now}} in filt["$or"]

    @pytest.mark.asyncio
    async def test_release_deletes_only_matching_owner(self) -> None:
        """Release deletes with both key and owner in the filter."""
        collection = MagicMock()
        collection.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
        database = MagicMock()
        database.__getitem__ = MagicMock(return_value=collection)

        lock = MongoSchemaMigrationLock(database)
        await lock.release(key="customers", owner="host:1")
        collection.delete_one.assert_awaited_once_with({"_id": "customers", "owner": "host:1"})

    @pytest.mark.asyncio
    async def test_renew_fails_for_other_owner(self) -> None:
        """Renew returns False when the stored owner does not match."""
        collection = MagicMock()
        collection.find_one_and_update = AsyncMock(return_value=None)
        database = MagicMock()
        database.__getitem__ = MagicMock(return_value=collection)

        lock = MongoSchemaMigrationLock(database)
        assert await lock.renew(key="customers", owner="host:2") is False

    @pytest.mark.asyncio
    async def test_get_owner_returns_stored_owner(self) -> None:
        """``get_owner`` reads the lease document."""
        collection = MagicMock()
        collection.find_one = AsyncMock(return_value={"_id": "customers", "owner": "host:1"})
        database = MagicMock()
        database.__getitem__ = MagicMock(return_value=collection)

        lock = MongoSchemaMigrationLock(database)
        assert await lock.get_owner(key="customers") == "host:1"
