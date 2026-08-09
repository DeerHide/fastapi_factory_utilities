"""Run RepositoryContract against a real MongoDB testcontainer."""

from collections.abc import Callable
from typing import Any

import pytest
import pytest_asyncio
from beanie import init_beanie
from pymongo.asynchronous.database import AsyncDatabase

from fastapi_factory_utilities.core.testing.contracts import (
    ContractDocument,
    ContractEntity,
    ContractRepository,
    RepositoryContract,
)
from fastapi_factory_utilities.core.testing.odm import make_contract_entity


class TestRepositoryContractReal(RepositoryContract):
    """Contract suite — reference implementation (real Mongo)."""

    @pytest_asyncio.fixture
    async def repository(self, async_motor_database: AsyncDatabase[Any]) -> ContractRepository:
        """Initialize Beanie on the testcontainer database and return a repository."""
        await init_beanie(database=async_motor_database, document_models=[ContractDocument])
        return ContractRepository(database=async_motor_database)

    @pytest.fixture
    def new_entity(self) -> Callable[..., ContractEntity]:
        """Entity factory for contract tests."""
        return make_contract_entity
