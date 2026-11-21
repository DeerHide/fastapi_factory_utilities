"""Unit tests for schema migration helpers and BaseDocument validator."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar
from uuid import UUID, uuid4

import pytest
from bson.binary import Binary

from fastapi_factory_utilities.core.plugins.odm_plugin.documents import BaseDocument
from fastapi_factory_utilities.core.plugins.odm_plugin.migrations import (
    SchemaMigration,
    apply_schema_migrations,
    build_migration_update,
    validate_migration_chain,
)


def _copy_name_to_display_name(raw: dict[str, Any]) -> dict[str, Any]:
    """Expand: copy ``name`` to ``display_name``, keep ``name``."""
    upgraded: dict[str, Any] = dict(raw)
    upgraded["display_name"] = upgraded.get("name")
    return upgraded


def _drop_legacy_name(raw: dict[str, Any]) -> dict[str, Any]:
    """Contract: drop ``name`` after expand."""
    upgraded: dict[str, Any] = dict(raw)
    upgraded.pop("name", None)
    return upgraded


_MIGRATIONS: Mapping[int, SchemaMigration] = {
    0: SchemaMigration(to_version=1, transform=_copy_name_to_display_name),
    1: SchemaMigration(to_version=2, transform=_drop_legacy_name),
}


class _MigratingDocument(BaseDocument):
    """Document with a two-step expand then contract chain."""

    name: str | None = None
    display_name: str | None = None

    CURRENT_SCHEMA_VERSION: ClassVar[int] = 2

    @classmethod
    def schema_migrations(cls) -> Mapping[int, SchemaMigration]:
        """Return the test migration chain."""
        return _MIGRATIONS

    class Settings(BaseDocument.Settings):
        """Beanie settings."""

        name = "ffu_migrating_documents"


class TestValidateMigrationChain:
    """Tests for ``validate_migration_chain``."""

    def test_accepts_empty_chain_at_version_zero(self) -> None:
        """Version 0 requires an empty map."""
        validate_migration_chain(0, {})

    def test_rejects_non_empty_chain_at_version_zero(self) -> None:
        """Version 0 with steps is invalid."""
        with pytest.raises(ValueError, match="not empty"):
            validate_migration_chain(0, _MIGRATIONS)

    def test_accepts_contiguous_chain(self) -> None:
        """A contiguous 0→1→2 chain is valid."""
        validate_migration_chain(2, _MIGRATIONS)

    def test_rejects_gap(self) -> None:
        """A missing step raises."""
        with pytest.raises(ValueError, match="missing schema migration from version 1"):
            validate_migration_chain(2, {0: _MIGRATIONS[0]})


class TestApplySchemaMigrations:
    """Tests for ``apply_schema_migrations``."""

    def test_legacy_dict_walks_zero_to_two_and_names_unset_keys(self) -> None:
        """``_id`` + no version walks 0→1→2 and collects removed keys."""
        document_id: UUID = uuid4()
        raw: dict[str, Any] = {"_id": document_id, "name": "Ada", "revision_id": uuid4()}
        upgraded, unset = apply_schema_migrations(
            raw,
            from_version=0,
            current_version=2,
            migrations=_MIGRATIONS,
        )
        assert upgraded["schema_version"] == _MigratingDocument.CURRENT_SCHEMA_VERSION
        assert upgraded["display_name"] == "Ada"
        assert "name" not in upgraded
        assert unset == frozenset({"name"})

    def test_already_current_is_unchanged(self) -> None:
        """A current document is returned as a copy with no unsets."""
        raw: dict[str, Any] = {"_id": uuid4(), "display_name": "Ada", "schema_version": 2}
        upgraded, unset = apply_schema_migrations(
            raw,
            from_version=2,
            current_version=2,
            migrations=_MIGRATIONS,
        )
        assert upgraded == raw
        assert unset == frozenset()


class TestBuildMigrationUpdate:
    """Tests for ``build_migration_update``."""

    def test_filter_and_set_unset_operators(self) -> None:
        """Filter pins ``_id``, ``revision_id``, and ``schema_version``; update uses $set/$unset."""
        document_id: UUID = uuid4()
        revision_id: UUID = uuid4()
        new_revision: UUID = uuid4()
        upgraded: dict[str, Any] = {
            "_id": document_id,
            "display_name": "Ada",
            "schema_version": 2,
            "revision_id": revision_id,
        }
        filt, update = build_migration_update(
            document_id=document_id,
            observed_revision_id=revision_id,
            observed_schema_version=0,
            upgraded=upgraded,
            keys_to_unset=frozenset({"name"}),
            new_revision_id=new_revision,
        )
        assert filt == {
            "_id": Binary.from_uuid(document_id),
            "revision_id": Binary.from_uuid(revision_id),
            "schema_version": 0,
        }
        assert update["$set"]["display_name"] == "Ada"
        assert update["$set"]["schema_version"] == _MigratingDocument.CURRENT_SCHEMA_VERSION
        assert update["$set"]["revision_id"] == Binary.from_uuid(new_revision)
        assert "_id" not in update["$set"]
        assert "name" not in update["$set"]
        assert update["$unset"] == {"name": ""}

    def test_missing_schema_version_uses_exists_false(self) -> None:
        """Legacy documents without the field filter on ``$exists: False``."""
        document_id: UUID = uuid4()
        filt, _update = build_migration_update(
            document_id=document_id,
            observed_revision_id=None,
            observed_schema_version=None,
            upgraded={"_id": document_id, "schema_version": 1},
            keys_to_unset=frozenset(),
            new_revision_id=uuid4(),
        )
        assert filt["schema_version"] == {"$exists": False}


class TestBaseDocumentValidator:
    """Tests for ``BaseDocument._apply_schema_migrations_on_load``.

    Call the before-validator directly: Beanie ``Document.__init__`` requires
    ``init_beanie`` and belongs in integration tests.
    """

    def test_legacy_stored_document_is_upgraded_in_memory(self) -> None:
        """A stored dict with ``_id`` and no version is upgraded before validation."""
        document_id: UUID = uuid4()
        upgraded: Any = _MigratingDocument._apply_schema_migrations_on_load(
            {"_id": document_id, "name": "Ada", "revision_id": uuid4()}
        )
        assert isinstance(upgraded, dict)
        assert upgraded["schema_version"] == _MigratingDocument.CURRENT_SCHEMA_VERSION
        assert upgraded["display_name"] == "Ada"
        assert "name" not in upgraded

    def test_new_instance_stamps_current_version(self) -> None:
        """A new instance without id/version gets CURRENT_SCHEMA_VERSION."""
        upgraded: Any = _MigratingDocument._apply_schema_migrations_on_load({"title": "x"})
        assert isinstance(upgraded, dict)
        assert upgraded["schema_version"] == _MigratingDocument.CURRENT_SCHEMA_VERSION

    def test_already_current_dict_is_unchanged(self) -> None:
        """A dict already at CURRENT is left alone."""
        document_id: UUID = uuid4()
        raw: dict[str, Any] = {"_id": document_id, "schema_version": 2, "display_name": "Ada"}
        upgraded: Any = _MigratingDocument._apply_schema_migrations_on_load(raw)
        assert upgraded == raw

    def test_base_document_defaults_to_version_zero(self) -> None:
        """BaseDocument with no migrations stamps version 0 on new instances."""
        upgraded: Any = BaseDocument._apply_schema_migrations_on_load({})
        assert isinstance(upgraded, dict)
        assert upgraded["schema_version"] == 0
        assert BaseDocument.CURRENT_SCHEMA_VERSION == 0
