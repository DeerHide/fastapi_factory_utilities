"""Run RepositoryContract against the mongomock-backed driver fake."""

from collections.abc import Callable

import pytest
import pytest_asyncio

from tests.fixtures.repository_contract import (
    ContractEntity,
    ContractRepository,
    RepositoryContract,
    init_contract_mongomock,
    make_contract_entity,
)


class TestRepositoryContractMongomock(RepositoryContract):
    """Contract suite — mongomock fake (must match the real Mongo suite)."""

    @pytest_asyncio.fixture
    async def repository(self) -> ContractRepository:
        """Use a mongomock ContractRepository."""
        return await init_contract_mongomock()

    @pytest.fixture
    def new_entity(self) -> Callable[..., ContractEntity]:
        """Entity factory for contract tests."""
        return make_contract_entity
