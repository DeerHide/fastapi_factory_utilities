"""Unit tests for the sequential batch migration sweep."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from bson.binary import Binary

from fastapi_factory_utilities.core.plugins.odm_plugin.documents import BaseDocument
from fastapi_factory_utilities.core.plugins.odm_plugin.migration_sweep import (
    run_one_migration_batch,
)
from fastapi_factory_utilities.core.plugins.odm_plugin.migrations import SchemaMigration


def _noop_transform(raw: dict[str, Any]) -> dict[str, Any]:
    """Identity transform that stamps nothing beyond schema_version (applicator does)."""
    return dict(raw)


class _SweepDocument(BaseDocument):
    """Minimal document for sweep unit tests."""

    CURRENT_SCHEMA_VERSION: ClassVar[int] = 1

    @classmethod
    def schema_migrations(cls) -> Mapping[int, SchemaMigration]:
        """Single step 0→1."""
        return {0: SchemaMigration(to_version=1, transform=_noop_transform)}

    class Settings(BaseDocument.Settings):
        """Beanie settings."""

        name = "ffu_sweep_documents"


class TestRunOneMigrationBatch:
    """Tests for sequential per-document updates."""

    @pytest.mark.asyncio
    async def test_batch_calls_update_one_per_document_not_bulk_write(self) -> None:
        """One batch is find+limit then sequential update_one — never bulk_write."""
        first_id = uuid4()
        second_id = uuid4()
        batch: list[dict[str, Any]] = [
            {"_id": first_id, "revision_id": uuid4()},
            {"_id": second_id, "revision_id": uuid4()},
        ]

        mock_collection = MagicMock()
        mock_collection.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
        mock_collection.bulk_write = AsyncMock()

        with (
            patch(
                "fastapi_factory_utilities.core.plugins.odm_plugin.migration_sweep.fetch_legacy_batch",
                new_callable=AsyncMock,
                return_value=batch,
            ),
            patch.object(_SweepDocument, "get_pymongo_collection", return_value=mock_collection),
            patch.object(_SweepDocument, "get_collection_name", return_value="ffu_sweep_documents"),
        ):
            count: int = await run_one_migration_batch(_SweepDocument, batch_size=100)

        expected_batch_size = 2
        assert count == expected_batch_size
        assert mock_collection.update_one.await_count == expected_batch_size
        mock_collection.bulk_write.assert_not_called()
        # Sequential: first document then second (UUIDs encoded as Binary for pymongo).
        first_filter = mock_collection.update_one.await_args_list[0].args[0]
        second_filter = mock_collection.update_one.await_args_list[1].args[0]
        assert first_filter["_id"] == Binary.from_uuid(first_id)
        assert second_filter["_id"] == Binary.from_uuid(second_id)
