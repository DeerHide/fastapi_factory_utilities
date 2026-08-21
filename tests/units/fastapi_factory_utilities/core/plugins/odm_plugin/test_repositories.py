"""Provides unit tests for the repositories module."""

from pydantic import BaseModel

from fastapi_factory_utilities.core.plugins.odm_plugin.documents import BaseDocument
from fastapi_factory_utilities.core.plugins.odm_plugin.repositories import (
    AbstractRepository,
)


class TestUnitRepositories:
    """Unit tests for the repositories module."""

    def test_concrete_type_retrieval(self) -> None:
        """Test the retrieval of the concrete types."""

        # Given
        class ConcreteDocument(BaseDocument):
            pass

        class ConcreteEntity(BaseModel):
            pass

        class ConcreteRepository(AbstractRepository[ConcreteDocument, ConcreteEntity]):
            pass

        # When
        repository = ConcreteRepository(database=None)  # type: ignore

        # Then

        # pylint: disable=protected-access
        assert repository._document_type == ConcreteDocument  # pyright: ignore[reportPrivateUsage]
        assert repository._entity_type == ConcreteEntity  # pyright: ignore[reportPrivateUsage]
