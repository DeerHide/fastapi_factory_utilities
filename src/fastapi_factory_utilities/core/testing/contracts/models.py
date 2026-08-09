"""Shared document/entity/repository types for :class:`RepositoryContract`."""

import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from fastapi_factory_utilities.core.plugins.odm_plugin.documents import BaseDocument
from fastapi_factory_utilities.core.plugins.odm_plugin.repositories import AbstractRepository


class ContractDocument(BaseDocument):
    """Document used by the shared repository contract suite."""

    my_field: str = Field(description="Primary string field.")
    category: str | None = Field(default=None, description="Optional filter field.")

    class Settings:
        """Beanie settings."""

        name = "ffu_contract_documents"
        use_revision = True


class ContractEntity(BaseModel):
    """Entity used by the shared repository contract suite."""

    id: UUID
    my_field: str
    category: str | None = None
    revision_id: UUID | None = Field(default=None)
    created_at: datetime.datetime | None = Field(default=None)
    updated_at: datetime.datetime | None = Field(default=None)


class ContractRepository(AbstractRepository[ContractDocument, ContractEntity]):
    """Repository under test for the shared contract suite."""
