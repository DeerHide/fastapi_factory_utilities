"""Schema version migrations for ODM documents."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Set
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from bson.binary import Binary

SchemaTransform = Callable[[dict[str, Any]], dict[str, Any]]


def _bson_encode(value: Any) -> Any:
    """Encode native ``UUID`` the way Beanie's Encoder does for raw pymongo writes."""
    if isinstance(value, UUID):
        return Binary.from_uuid(value)
    return value


@dataclass(frozen=True, slots=True)
class SchemaMigration:
    """One forward step from a stored schema version to the next.

    Attributes:
        to_version: Schema version produced by ``transform``.
        transform: Pure function that returns the next document dict. Keys removed
            from the input become ``$unset`` targets on the sweep write.
    """

    to_version: int
    transform: SchemaTransform


def validate_migration_chain(
    current_version: int,
    migrations: Mapping[int, SchemaMigration],
) -> None:
    """Require a contiguous ``0 → 1 → … → current_version`` chain.

    Args:
        current_version: The document class ``CURRENT_SCHEMA_VERSION``.
        migrations: Map of accepted version → step.

    Raises:
        ValueError: If the chain is incomplete or a step does not advance by one.
    """
    if current_version < 0:
        raise ValueError(f"CURRENT_SCHEMA_VERSION must be >= 0, got {current_version}")
    if current_version == 0:
        if migrations:
            raise ValueError("CURRENT_SCHEMA_VERSION is 0 but schema_migrations is not empty")
        return
    for version in range(current_version):
        step: SchemaMigration | None = migrations.get(version)
        if step is None:
            raise ValueError(f"missing schema migration from version {version}")
        if step.to_version != version + 1:
            raise ValueError(
                f"schema migration from version {version} must target {version + 1}, got {step.to_version}"
            )


def apply_schema_migrations(
    raw: Mapping[str, Any],
    *,
    from_version: int,
    current_version: int,
    migrations: Mapping[int, SchemaMigration],
) -> tuple[dict[str, Any], frozenset[str]]:
    """Apply forward migration steps until ``current_version``.

    Args:
        raw: Stored or in-memory document dict.
        from_version: Observed schema version (``0`` when the field is missing).
        current_version: Target ``CURRENT_SCHEMA_VERSION``.
        migrations: Contiguous forward steps.

    Returns:
        The upgraded document and the set of keys removed across the chain
        (candidates for ``$unset`` on a sweep write).

    Raises:
        ValueError: If a required step is missing or the chain does not reach
            ``current_version``.
        TypeError: If a transform does not return a ``dict``.
    """
    if from_version >= current_version:
        return dict(raw), frozenset()

    data: dict[str, Any] = dict(raw)
    removed: set[str] = set()
    version: int = from_version
    while version < current_version:
        step: SchemaMigration | None = migrations.get(version)
        if step is None:
            raise ValueError(f"missing schema migration from version {version}")
        before_keys: set[str] = set(data.keys())
        transformed: dict[str, Any] = step.transform(data)
        if not isinstance(transformed, dict):
            raise TypeError(f"schema migration from version {version} must return a dict")
        data = transformed
        removed |= before_keys - set(data.keys())
        removed -= set(data.keys())
        if step.to_version <= version:
            raise ValueError(f"schema migration from version {version} did not advance")
        version = step.to_version
        data["schema_version"] = version

    if version != current_version:
        raise ValueError(f"schema migrations ended at {version}, expected {current_version}")
    return data, frozenset(removed)


def build_migration_update(  # noqa: PLR0913
    *,
    document_id: Any,
    observed_revision_id: Any,
    observed_schema_version: int | None,
    upgraded: Mapping[str, Any],
    keys_to_unset: Set[str],
    new_revision_id: UUID | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a conditional ``update_one`` filter and ``$set`` / ``$unset`` document.

    Args:
        document_id: Stored ``_id``.
        observed_revision_id: ``revision_id`` read with the batch (may be ``None``).
        observed_schema_version: Stored ``schema_version``, or ``None`` if missing.
        upgraded: Document after applying the migration chain.
        keys_to_unset: Keys removed by the chain.
        new_revision_id: Optional fixed revision for tests; otherwise a new UUID.

    Returns:
        ``(filter, update)`` suitable for ``collection.update_one``.
    """
    filt: dict[str, Any] = {
        "_id": _bson_encode(document_id),
        "revision_id": _bson_encode(observed_revision_id),
    }
    if observed_schema_version is None:
        filt["schema_version"] = {"$exists": False}
    else:
        filt["schema_version"] = observed_schema_version

    revision: UUID = new_revision_id if new_revision_id is not None else uuid4()
    set_doc: dict[str, Any] = {
        key: _bson_encode(value) for key, value in upgraded.items() if key != "_id" and key not in keys_to_unset
    }
    set_doc["revision_id"] = Binary.from_uuid(revision)

    update: dict[str, Any] = {"$set": set_doc}
    unset_keys: dict[str, str] = {key: "" for key in keys_to_unset if key != "_id"}
    if unset_keys:
        update["$unset"] = unset_keys
    return filt, update


def legacy_documents_filter(current_version: int) -> dict[str, Any]:
    """Mongo filter for documents that still need a sweep write.

    Args:
        current_version: Document class ``CURRENT_SCHEMA_VERSION``.

    Returns:
        A filter matching missing or lower ``schema_version`` values.
    """
    return {
        "$or": [
            {"schema_version": {"$lt": current_version}},
            {"schema_version": {"$exists": False}},
        ]
    }
