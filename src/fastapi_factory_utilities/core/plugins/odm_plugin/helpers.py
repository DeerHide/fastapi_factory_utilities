"""Helper functions for ODM plugins."""

import datetime
import uuid
from collections.abc import Callable
from typing import Generic, TypeVar, cast

from pydantic import BaseModel, Field

GenericPersistedEntityId = TypeVar("GenericPersistedEntityId", bound=uuid.UUID)


class PersistedEntity(BaseModel, Generic[GenericPersistedEntityId]):
    """Base class for persisted entities.

    Attributes:
        id: The ID of the persisted entity.
        revision_id: The revision ID of the persisted entity.
        created_at: The creation date of the persisted entity.
        updated_at: The last update date of the persisted entity.

    ```python
    from fastapi_factory_utilities.core.plugins.odm_plugin.helpers import PersistedEntity

    BookEntityId = NewType("BookEntityId", uuid.UUID)


    class BookEntity(PersistedEntity[BookEntityId]):
        title: str = Field(title="Title of the book")
        author: str = Field(title="Author name")
        published_year: int = Field(title="Year published")
    ```
    """

    id: GenericPersistedEntityId = Field(default_factory=cast(Callable[[], GenericPersistedEntityId], uuid.uuid4))

    revision_id: uuid.UUID | None = Field(default=None)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
