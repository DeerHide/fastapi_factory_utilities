"""Helper functions for ODM plugins."""

import datetime
import uuid
from collections.abc import Callable
from typing import Annotated, Generic, TypeVar, cast

from pydantic import BaseModel, Field

from fastapi_factory_utilities.core.utils.api import (
    ApiField,
    ApiResponseModelAbstract,
    SearchableEntity,
)

GenericPersistedEntityId = TypeVar("GenericPersistedEntityId", bound=uuid.UUID)


class PersistedEntity(SearchableEntity, ApiResponseModelAbstract, BaseModel, Generic[GenericPersistedEntityId]):
    """Base class for persisted entities.

    Attributes:
        id: The ID of the persisted entity.
        revision_id: The revision ID of the persisted entity.
        created_at: The creation date of the persisted entity.
        updated_at: The last update date of the persisted entity.
        schema_version: Persisted document schema version (mirrors BaseDocument).

    ```python
    from fastapi_factory_utilities.core.plugins.odm_plugin.helpers import PersistedEntity

    BookEntityId = NewType("BookEntityId", uuid.UUID)


    class BookEntity(PersistedEntity[BookEntityId]):
        title: str = Field(title="Title of the book")
        author: str = Field(title="Author name")
        published_year: int = Field(title="Year published")
    ```
    """

    id: Annotated[GenericPersistedEntityId, ApiField(searchable=True)] = Field(
        default_factory=cast(Callable[[], GenericPersistedEntityId], uuid.uuid4)
    )

    revision_id: uuid.UUID | None = Field(default=None)
    created_at: Annotated[datetime.datetime, ApiField(searchable=True)] = Field(default_factory=datetime.datetime.now)
    updated_at: Annotated[datetime.datetime, ApiField(searchable=True)] = Field(default_factory=datetime.datetime.now)
    # Mirrored on BaseDocument. Not searchable / not an API response field.
    # Entities that do not extend PersistedEntity must declare the same field or
    # model_dump() drops it (extra=ignore) and the next save cannot carry it.
    schema_version: int = Field(default=0)
