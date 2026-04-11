"""Provides the objects for the Hydra service."""

from typing import Annotated, ClassVar

from pydantic import BaseModel, ConfigDict

from fastapi_factory_utilities.core.utils.api import ApiResponseField, ApiResponseModelAbstract
from fastapi_factory_utilities.core.utils.queries import SearchableEntity, SearchableField


class HydraTokenIntrospectObject(SearchableEntity, ApiResponseModelAbstract, BaseModel):
    """Represents the object returned by the Hydra token introspection."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    active: Annotated[bool, ApiResponseField, SearchableField]
    aud: Annotated[list[str], ApiResponseField, SearchableField]
    client_id: Annotated[str, ApiResponseField, SearchableField]
    exp: Annotated[int, ApiResponseField, SearchableField]
    ext: Annotated[dict[str, str] | None, ApiResponseField, SearchableField] = None
    iat: Annotated[int, ApiResponseField, SearchableField]
    iss: Annotated[str, ApiResponseField, SearchableField]
    nbf: Annotated[int, ApiResponseField, SearchableField]
    obfuscated_subject: Annotated[str | None, ApiResponseField, SearchableField] = None
    scope: Annotated[str, ApiResponseField, SearchableField]
    sub: Annotated[str, ApiResponseField, SearchableField]
    token_type: Annotated[str, ApiResponseField, SearchableField]
    token_use: Annotated[str, ApiResponseField, SearchableField]
    username: Annotated[str | None, ApiResponseField, SearchableField] = None
