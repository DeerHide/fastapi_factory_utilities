"""Integration tests for continuous schema migration sweeps."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar
from uuid import UUID, uuid4

import pytest
from beanie import init_beanie
from bson.binary import Binary, UuidRepresentation
from pydantic import Field
from pymongo.asynchronous.database import AsyncDatabase

from fastapi_factory_utilities.core.plugins.odm_plugin.documents import BaseDocument
from fastapi_factory_utilities.core.plugins.odm_plugin.migration_lock import (
    AlwaysAcquireMigrationLock,
    MongoSchemaMigrationLock,
)
from fastapi_factory_utilities.core.plugins.odm_plugin.migration_sweep import (
    migrate_one_document,
    run_one_migration_batch,
)
from fastapi_factory_utilities.core.plugins.odm_plugin.migrations import SchemaMigration


def _uuid_binary(value: UUID) -> Binary:
    """Encode a UUID the way Beanie/pymongo STANDARD representation expects."""
    return Binary.from_uuid(value, uuid_representation=UuidRepresentation.STANDARD)


def _copy_name_to_display_name(raw: dict[str, Any]) -> dict[str, Any]:
    """Expand: copy ``name`` to ``display_name``."""
    upgraded: dict[str, Any] = dict(raw)
    upgraded["display_name"] = upgraded.get("name")
    return upgraded


def _drop_legacy_name(raw: dict[str, Any]) -> dict[str, Any]:
    """Contract: drop ``name``."""
    upgraded: dict[str, Any] = dict(raw)
    upgraded.pop("name", None)
    return upgraded


class MigrationDocument(BaseDocument):
    """Document under test for integration migration sweeps."""

    name: str | None = Field(default=None)
    display_name: str | None = Field(default=None)

    CURRENT_SCHEMA_VERSION: ClassVar[int] = 2

    @classmethod
    def schema_migrations(cls) -> Mapping[int, SchemaMigration]:
        """Return expand then contract steps."""
        return {
            0: SchemaMigration(to_version=1, transform=_copy_name_to_display_name),
            1: SchemaMigration(to_version=2, transform=_drop_legacy_name),
        }

    class Settings(BaseDocument.Settings):
        """Beanie settings."""

        name = "ffu_integration_migration_documents"
        use_revision = True


@pytest.mark.asyncio()
async def test_batch_sweep_upgrades_legacy_documents(async_motor_database: AsyncDatabase[Any]) -> None:
    """Insert raw legacy docs, run one batch, assert field/version/unset."""
    await init_beanie(database=async_motor_database, document_models=[MigrationDocument])
    collection = MigrationDocument.get_pymongo_collection()

    first_id: UUID = uuid4()
    second_id: UUID = uuid4()
    first_revision: UUID = uuid4()
    second_revision: UUID = uuid4()
    await collection.insert_many(
        [
            {"_id": _uuid_binary(first_id), "name": "Ada", "revision_id": _uuid_binary(first_revision)},
            {"_id": _uuid_binary(second_id), "name": "Grace", "revision_id": _uuid_binary(second_revision)},
        ]
    )

    expected_batch_size = 2
    batch_count: int = await run_one_migration_batch(MigrationDocument, batch_size=100)
    assert batch_count == expected_batch_size

    first: dict[str, Any] | None = await collection.find_one({"_id": _uuid_binary(first_id)})
    second: dict[str, Any] | None = await collection.find_one({"_id": _uuid_binary(second_id)})
    assert first is not None
    assert second is not None
    assert first["schema_version"] == MigrationDocument.CURRENT_SCHEMA_VERSION
    assert first["display_name"] == "Ada"
    assert "name" not in first
    assert first["revision_id"] != _uuid_binary(first_revision)
    assert second["schema_version"] == MigrationDocument.CURRENT_SCHEMA_VERSION
    assert second["display_name"] == "Grace"
    assert "name" not in second


@pytest.mark.asyncio()
async def test_stale_revision_does_not_overwrite_winner(async_motor_database: AsyncDatabase[Any]) -> None:
    """A second update with a stale revision_id matches nothing."""
    await init_beanie(database=async_motor_database, document_models=[MigrationDocument])
    collection = MigrationDocument.get_pymongo_collection()

    document_id: UUID = uuid4()
    stale_revision: UUID = uuid4()
    await collection.insert_one(
        {"_id": _uuid_binary(document_id), "name": "Ada", "revision_id": _uuid_binary(stale_revision)}
    )

    # Batch find returns Binary UUIDs; migrate_one must round-trip that wire form.
    raw: dict[str, Any] | None = await collection.find_one({"_id": _uuid_binary(document_id)})
    assert raw is not None
    assert await migrate_one_document(MigrationDocument, raw, current_version=2) is True

    stored: dict[str, Any] | None = await collection.find_one({"_id": _uuid_binary(document_id)})
    assert stored is not None
    winner_revision: Any = stored["revision_id"]
    assert winner_revision != _uuid_binary(stale_revision)

    # Replay the same pre-migration raw (stale revision) — must not overwrite.
    assert await migrate_one_document(MigrationDocument, raw, current_version=2) is False
    after: dict[str, Any] | None = await collection.find_one({"_id": _uuid_binary(document_id)})
    assert after is not None
    assert after["revision_id"] == winner_revision
    assert after["display_name"] == "Ada"


@pytest.mark.asyncio()
async def test_second_sweeper_refused_while_lease_held(async_motor_database: AsyncDatabase[Any]) -> None:
    """Only one owner holds the collection lease while it is live."""
    lock_a = MongoSchemaMigrationLock(async_motor_database)
    lock_b = MongoSchemaMigrationLock(async_motor_database)

    assert await lock_a.try_acquire(key="customers", owner="pod-a") is True
    assert await lock_b.try_acquire(key="customers", owner="pod-b") is False
    assert await lock_a.get_owner(key="customers") == "pod-a"

    await lock_a.release(key="customers", owner="pod-a")
    assert await lock_b.try_acquire(key="customers", owner="pod-b") is True
    await lock_b.release(key="customers", owner="pod-b")


@pytest.mark.asyncio()
async def test_release_does_not_delete_other_owners_lock(async_motor_database: AsyncDatabase[Any]) -> None:
    """Release with a mismatched owner leaves the lease in place."""
    lock = MongoSchemaMigrationLock(async_motor_database)
    assert await lock.try_acquire(key="realms", owner="pod-a") is True
    await lock.release(key="realms", owner="pod-b")
    assert await lock.get_owner(key="realms") == "pod-a"
    await lock.release(key="realms", owner="pod-a")


@pytest.mark.asyncio()
async def test_always_acquire_lock_allows_batch(async_motor_database: AsyncDatabase[Any]) -> None:
    """AlwaysAcquireMigrationLock is usable as the plugin hook stand-in."""
    await init_beanie(database=async_motor_database, document_models=[MigrationDocument])
    lock = AlwaysAcquireMigrationLock()
    assert await lock.try_acquire(key="x", owner="test") is True
    assert await lock.renew(key="x", owner="test") is True
    await lock.release(key="x", owner="test")
