"""Provides base document class for ODM plugins."""

from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Annotated, Any, ClassVar
from uuid import UUID, uuid4

from beanie import Document, Indexed  # pyright: ignore[reportUnknownVariableType]
from pydantic import Field, model_validator
from pymongo import DESCENDING

from .migrations import SchemaMigration, apply_schema_migrations


class BaseDocument(Document):
    """Base document class."""

    # To be agnostic of MongoDN, we use UUID as the document ID.
    id: UUID = Field(  # type: ignore
        default_factory=uuid4, description="The document ID."
    )

    revision_id: UUID | None = Field(default=None, exclude=False)
    created_at: Annotated[datetime.datetime, Indexed(index_type=DESCENDING)] = Field(  # pyright: ignore
        default_factory=lambda: datetime.datetime.now(tz=datetime.UTC), description="Creation timestamp."
    )

    updated_at: Annotated[datetime.datetime, Indexed(index_type=DESCENDING)] = Field(  # pyright: ignore
        default_factory=lambda: datetime.datetime.now(tz=datetime.UTC), description="Last update timestamp."
    )

    # Document schema version for continuous forward migrations. Not an API field.
    schema_version: Annotated[int, Indexed()] = Field(  # pyright: ignore
        default=0, description="Persisted document schema version."
    )

    CURRENT_SCHEMA_VERSION: ClassVar[int] = 0

    class Settings:
        """Meta class for BaseDocument."""

        use_revision = True

        # Dotted field paths (e.g. "creds.client_secret") to encrypt with CSFLE. Subclasses
        # override this list; see `fastapi_factory_utilities.core.plugins.odm_plugin.encryption`.
        encrypted_fields: list[str] = []  # noqa: RUF012

    @classmethod
    def schema_migrations(cls) -> Mapping[int, SchemaMigration]:
        """Return forward migrations keyed by the version they accept.

        Returns:
            Contiguous map from ``0`` through ``CURRENT_SCHEMA_VERSION - 1``.
            Empty when ``CURRENT_SCHEMA_VERSION`` is ``0``.
        """
        return {}

    @model_validator(mode="before")
    @classmethod
    def _apply_schema_migrations_on_load(cls, data: Any) -> Any:
        """Upgrade stored documents in memory before Pydantic validation.

        - New instance (no ``_id`` / ``id``, no ``schema_version``): stamp
          ``CURRENT_SCHEMA_VERSION`` so the field default matches the class.
        - Stored legacy (has id, missing ``schema_version``): treat as version ``0``.
        - Stored older version: apply the contiguous forward chain.
        - Already current: leave untouched.

        The read path does not write. A failing step fails the load.
        """
        if not isinstance(data, dict):
            return data

        current_version: int = cls.CURRENT_SCHEMA_VERSION
        has_stored_id: bool = "_id" in data or "id" in data

        if "schema_version" not in data:
            if not has_stored_id:
                return {**data, "schema_version": current_version}
            from_version = 0
        else:
            from_version = int(data["schema_version"])
            if from_version >= current_version:
                return data

        if current_version == 0:
            return {**data, "schema_version": 0}

        upgraded, _keys_to_unset = apply_schema_migrations(
            data,
            from_version=from_version,
            current_version=current_version,
            migrations=cls.schema_migrations(),
        )
        return upgraded
