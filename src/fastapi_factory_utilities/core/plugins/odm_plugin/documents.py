"""Provides base document class for ODM plugins."""

import datetime
from typing import Annotated
from uuid import UUID, uuid4

from beanie import Document, Indexed  # pyright: ignore[reportUnknownVariableType]
from pydantic import Field
from pymongo import DESCENDING


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

    class Settings:
        """Meta class for BaseDocument."""

        use_revision = True

        # Dotted field paths (e.g. "creds.client_secret") to encrypt with CSFLE. Subclasses
        # override this list; see `fastapi_factory_utilities.core.plugins.odm_plugin.encryption`.
        encrypted_fields: list[str] = []  # noqa: RUF012
