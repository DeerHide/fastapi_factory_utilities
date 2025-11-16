"""Provides the JWT bearer token objects."""

import datetime
from typing import Annotated, Any, ClassVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from .types import OAuth2Audience, OAuth2Issuer, OAuth2Scope, OAuth2Subject


def validate_string_list_field(value: Any) -> list[str]:
    """Validate a string list field.

    Accepts either a space-separated string or a list of strings.
    Converts all values to lowercase strings.

    Args:
        value: Either a string (space-separated) or a list of strings.

    Returns:
        A list of lowercase strings.

    Raises:
        ValueError: If the value is not a string or list, or if the resulting list is empty.
    """
    cleaned_value: list[str]
    if isinstance(value, str):
        cleaned_value = value.split(sep=" ")
    elif isinstance(value, list):
        cleaned_value = [str(item) for item in value if item is not None]
    else:
        raise ValueError(f"Invalid value type: expected str or list, got {type(value).__name__}")
    cleaned_value = [item.lower() for item in cleaned_value if item.strip()]
    if len(cleaned_value) == 0:
        raise ValueError("Invalid value: empty list after processing")
    return cleaned_value


def validate_timestamp_field(value: Any) -> datetime.datetime:
    """Validate a timestamp field.

    Accepts either a Unix timestamp (int or string) or a datetime object.
    Converts timestamps to UTC datetime objects.

    Args:
        value: Either a Unix timestamp (int or string) or a datetime object.

    Returns:
        A datetime object in UTC timezone.

    Raises:
        ValueError: If the value cannot be converted to a datetime.
    """
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError as e:
            raise ValueError(f"Invalid timestamp string: {value}") from e
    if isinstance(value, int):
        try:
            return datetime.datetime.fromtimestamp(value, tz=datetime.UTC)
        except (ValueError, OSError) as e:
            raise ValueError(f"Invalid timestamp value: {value}") from e
    raise ValueError(f"Invalid value type: expected int, str, or datetime, got {type(value).__name__}")


class JWTPayload(BaseModel):
    """JWT bearer token payload.

    Represents a decoded JWT bearer token with OAuth2 claims.
    All fields are required and validated according to OAuth2/JWT standards.

    Attributes:
        scope: List of OAuth2 scopes granted by the token.
        aud: List of audiences (intended recipients) of the token.
        iss: The issuer of the JWT token.
        exp: The expiration date/time of the JWT token (UTC).
        iat: The issued at date/time of the JWT token (UTC).
        nbf: The not before date/time of the JWT token (UTC).
        sub: The subject (user identifier) of the JWT token.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        arbitrary_types_allowed=True,
        extra="ignore",
        frozen=True,
    )

    scp: Annotated[list[OAuth2Scope], BeforeValidator(validate_string_list_field)] = Field(
        description="The scope of the JWT token."
    )
    aud: Annotated[list[OAuth2Audience], BeforeValidator(validate_string_list_field)] = Field(
        description="The audiences of the JWT token."
    )
    iss: OAuth2Issuer = Field(description="The issuer of the JWT token.")
    exp: Annotated[datetime.datetime, BeforeValidator(validate_timestamp_field)] = Field(
        description="The expiration date of the JWT token."
    )
    iat: Annotated[datetime.datetime, BeforeValidator(validate_timestamp_field)] = Field(
        description="The issued at date of the JWT token."
    )
    nbf: Annotated[datetime.datetime, BeforeValidator(validate_timestamp_field)] = Field(
        description="The not before date of the JWT token."
    )
    sub: OAuth2Subject = Field(description="The subject of the JWT token.")
