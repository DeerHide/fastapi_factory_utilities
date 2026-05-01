"""Provides the objects for the Hydra service."""

from typing import Annotated, ClassVar

from pydantic import BaseModel, ConfigDict

from fastapi_factory_utilities.core.utils.api import ApiField, ApiResponseModelAbstract, SearchableEntity


class HydraTokenIntrospectObject(SearchableEntity, ApiResponseModelAbstract, BaseModel):
    """Represents the object returned by the Hydra token introspection."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    active: Annotated[bool, ApiField(searchable=True)]
    aud: Annotated[list[str], ApiField(searchable=True)]
    client_id: Annotated[str, ApiField(searchable=True)]
    exp: Annotated[int, ApiField(searchable=True)]
    ext: Annotated[dict[str, str] | None, ApiField(searchable=True)] = None
    iat: Annotated[int, ApiField(searchable=True)]
    iss: Annotated[str, ApiField(searchable=True)]
    nbf: Annotated[int, ApiField(searchable=True)]
    obfuscated_subject: Annotated[str | None, ApiField(searchable=True)] = None
    scope: Annotated[str, ApiField(searchable=True)]
    sub: Annotated[str, ApiField(searchable=True)]
    token_type: Annotated[str, ApiField(searchable=True)]
    token_use: Annotated[str, ApiField(searchable=True)]
    username: Annotated[str | None, ApiField(searchable=True)] = None
