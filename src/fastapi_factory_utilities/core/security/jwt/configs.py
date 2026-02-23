"""Provides the configurations for the JWT bearer token."""

from typing import ClassVar

from jwt.algorithms import get_default_algorithms, requires_cryptography
from pydantic import BaseModel, ConfigDict, Field, field_validator

from fastapi_factory_utilities.core.security.jwt.types import OAuth2Issuer


class JWTBearerAuthenticationConfig(BaseModel):
    """JWT bearer token authentication configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    authorized_algorithms: list[str] = Field(
        default_factory=lambda: list(get_default_algorithms().keys()), description="The authorized algorithms."
    )

    authorized_audiences: list[str] | None = Field(default=None, description="The authorized audiences.")
    issuer: OAuth2Issuer = Field(description="The authorized issuers.")

    @field_validator("authorized_audiences", mode="before")
    @classmethod
    def validate_authorized_audiences(cls, v: str | list[str]) -> list[str]:
        """Validate the authorized audiences.

        Example:
            "aud1,aud2,aud3" -> ["aud1", "aud2", "aud3"]
            ["aud1", "aud2", "aud3"] -> ["aud1", "aud2", "aud3"]
        """
        if isinstance(v, str):
            v = v.split(sep=",")
        v = [item.strip() for item in v if item.strip()]
        if len(v) == 0:
            raise ValueError("Invalid value: empty list after processing")
        return list(set(v))

    @field_validator("authorized_algorithms")
    @classmethod
    def validate_authorized_algorithms(cls, v: list[str]) -> list[str]:
        """Validate the authorized algorithms."""
        invalid_algorithms: list[str] = []
        for algorithm in v:
            if algorithm not in requires_cryptography:
                invalid_algorithms.append(algorithm)
        if invalid_algorithms:
            raise ValueError(f"Invalid algorithms: {invalid_algorithms}")
        return v
