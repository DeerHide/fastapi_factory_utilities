"""Run RepositoryContract against the mongomock-backed driver fake."""

from collections.abc import Callable
from typing import Any

import pytest
import pytest_asyncio

from fastapi_factory_utilities.core.plugins.odm_plugin.repositories import AbstractRepository
from fastapi_factory_utilities.core.testing.contracts import ContractEntity, RepositoryContract
from fastapi_factory_utilities.core.testing.odm import make_contract_entity


class TestRepositoryContractMongomock(RepositoryContract):
    """Contract suite — mongomock fake (must match the real Mongo suite)."""

    @pytest_asyncio.fixture
    async def repository(
        self,
        contract_repository_mongomock: AbstractRepository[Any, Any],
    ) -> AbstractRepository[Any, Any]:
        """Use the shared mongomock ContractRepository fixture."""
        return contract_repository_mongomock

    @pytest.fixture
    def new_entity(self) -> Callable[..., ContractEntity]:
        """Entity factory for contract tests."""
        return make_contract_entity
