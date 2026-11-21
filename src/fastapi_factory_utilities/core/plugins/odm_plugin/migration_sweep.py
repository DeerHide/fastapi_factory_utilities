"""Background batch sweep that rewrites legacy documents to CURRENT_SCHEMA_VERSION."""

from __future__ import annotations

import asyncio
from typing import Any

from structlog.stdlib import BoundLogger, get_logger

from .documents import BaseDocument
from .migration_lock import MongoSchemaMigrationLock, SchemaMigrationLock
from .migrations import (
    apply_schema_migrations,
    build_migration_update,
    legacy_documents_filter,
    validate_migration_chain,
)

_logger: BoundLogger = get_logger()

DEFAULT_BATCH_SIZE = 100
DEFAULT_IDLE_SLEEP_S = 5.0
DEFAULT_LOCK_RETRY_SLEEP_S = 5.0


async def fetch_legacy_batch(
    document_type: type[BaseDocument],
    *,
    current_version: int,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> list[dict[str, Any]]:
    """Load one batch of documents that still need a sweep write.

    Args:
        document_type: Beanie document class (must already be init_beanie'd).
        current_version: ``CURRENT_SCHEMA_VERSION`` for the class.
        batch_size: Maximum documents to return.

    Returns:
        Raw Mongo documents (not Beanie models).
    """
    collection = document_type.get_pymongo_collection()
    cursor = collection.find(legacy_documents_filter(current_version)).limit(batch_size)
    return await cursor.to_list(length=batch_size)


async def migrate_one_document(
    document_type: type[BaseDocument],
    raw: dict[str, Any],
    *,
    current_version: int,
) -> bool:
    """Upgrade one raw document with a conditional ``update_one``.

    Args:
        document_type: Beanie document class.
        raw: Stored document dict from the batch find.
        current_version: Target schema version.

    Returns:
        ``True`` when a document was modified, ``False`` when the conditional
        update matched nothing (stale revision / version) or the document was
        already current.

    Raises:
        ValueError: If the migration chain is incomplete for this document.
        TypeError: If a transform returns a non-dict.
    """
    observed_schema_version: int | None
    if "schema_version" not in raw:
        observed_schema_version = None
        from_version = 0
    else:
        observed_schema_version = int(raw["schema_version"])
        from_version = observed_schema_version

    if from_version >= current_version:
        return False

    upgraded, keys_to_unset = apply_schema_migrations(
        raw,
        from_version=from_version,
        current_version=current_version,
        migrations=document_type.schema_migrations(),
    )
    filt, update = build_migration_update(
        document_id=raw["_id"],
        observed_revision_id=raw.get("revision_id"),
        observed_schema_version=observed_schema_version,
        upgraded=upgraded,
        keys_to_unset=keys_to_unset,
    )
    collection = document_type.get_pymongo_collection()
    result = await collection.update_one(filt, update)
    return result.modified_count > 0


async def run_one_migration_batch(
    document_type: type[BaseDocument],
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> int:
    """Fetch one batch and ``update_one`` each document in order.

    Args:
        document_type: Beanie document class.
        batch_size: Maximum documents per batch.

    Returns:
        Number of documents in the batch (including skipped failures / races).
    """
    current_version: int = document_type.CURRENT_SCHEMA_VERSION
    batch: list[dict[str, Any]] = await fetch_legacy_batch(
        document_type,
        current_version=current_version,
        batch_size=batch_size,
    )
    collection_name: str = document_type.get_collection_name()
    for raw in batch:
        document_id: Any = raw.get("_id")
        try:
            await migrate_one_document(document_type, raw, current_version=current_version)
        except Exception:
            _logger.exception(
                "schema migration failed for one document; continuing batch",
                collection=collection_name,
                document_id=str(document_id),
            )
    return len(batch)


async def run_schema_migration_loop(  # noqa: PLR0913
    document_type: type[BaseDocument],
    *,
    lock: SchemaMigrationLock,
    owner: str,
    batch_size: int = DEFAULT_BATCH_SIZE,
    idle_sleep_s: float = DEFAULT_IDLE_SLEEP_S,
    lock_retry_sleep_s: float = DEFAULT_LOCK_RETRY_SLEEP_S,
) -> None:
    """Continuously sweep one collection while this process is alive.

    Acquires the collection lock, walks legacy documents in batches with
    sequential ``update_one`` (no bulk write), renews between batches, releases
    on an empty batch, then idles and rescans. Cancel to stop.

    Args:
        document_type: Beanie document class with ``CURRENT_SCHEMA_VERSION > 0``.
        lock: Exclusive sweep lock for this collection.
        owner: Process identity (``hostname:pid``).
        batch_size: Documents per find.
        idle_sleep_s: Sleep after an empty batch / released lock.
        lock_retry_sleep_s: Sleep when another owner holds the lock.
    """
    current_version: int = document_type.CURRENT_SCHEMA_VERSION
    validate_migration_chain(current_version, document_type.schema_migrations())
    key: str = document_type.get_collection_name()
    logger: BoundLogger = _logger.bind(collection=key, schema_version=current_version, owner=owner)

    while True:
        try:
            acquired: bool = await lock.try_acquire(key=key, owner=owner)
            if not acquired:
                holder: str | None = None
                if isinstance(lock, MongoSchemaMigrationLock):
                    holder = await lock.get_owner(key=key)
                logger.info(
                    "schema migration lock held by another owner; retrying later",
                    holder=holder,
                )
                await asyncio.sleep(lock_retry_sleep_s)
                continue

            try:
                while True:
                    batch_count: int = await run_one_migration_batch(
                        document_type,
                        batch_size=batch_size,
                    )
                    if batch_count == 0:
                        break
                    if not await lock.renew(key=key, owner=owner):
                        logger.warning("schema migration lock lost during sweep")
                        break
            finally:
                await lock.release(key=key, owner=owner)

            await asyncio.sleep(idle_sleep_s)
        except asyncio.CancelledError:
            try:
                await lock.release(key=key, owner=owner)
            except Exception:
                logger.exception("schema migration lock release failed on cancel")
            raise
