"""Provides the configurations for the JWT bearer token."""

import warnings
from enum import StrEnum
from typing import Any, ClassVar, Self

from fastapi import Request
from fastapi.datastructures import State
from jwt.algorithms import get_default_algorithms, requires_cryptography
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fastapi_factory_utilities.core.security.types import OAuth2Issuer
from fastapi_factory_utilities.core.utils.configs import (
    UnableToReadConfigFileError,
    ValueErrorConfigError,
    build_config_from_file_in_package,
)

from .exceptions import JWTBearerAuthenticationConfigBuilderError


class JWTLocation(StrEnum):
    """JWT location."""

    HEADER = "header"
    AUTHORIZATION_BEARER = "authorization_bearer"
    COOKIE = "cookie"


class JWTBearerAuthenticationConfig(BaseModel):
    """JWT bearer token authentication configuration.

    ``authorized_audiences`` is required and always enforced during decode.
    The legacy ``audience`` field is accepted only as a deprecated alias that
    populates ``authorized_audiences`` when the latter is omitted.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    authorized_algorithms: list[str] = Field(
        default_factory=lambda: list(get_default_algorithms().keys()), description="The authorized algorithms."
    )

    authorized_audiences: list[str] = Field(description="The authorized audiences (required; enforced on decode).")
    issuer: OAuth2Issuer = Field(description="The authorized issuers.")
    audience: str | None = Field(
        default=None,
        description="Deprecated alias for a single authorized audience; use authorized_audiences.",
    )

    # JWT location
    authorized_locations: list[JWTLocation] = Field(
        default_factory=lambda: [JWTLocation.AUTHORIZATION_BEARER], description="The authorized locations."
    )
    header_name: str | None = Field(default=None, description="The header name.")
    cookie_name: str | None = Field(default=None, description="The cookie name.")

    cache_enabled: bool = Field(default=False, description="Whether JWT introspection caching is enabled.")
    cache_ttl_seconds: int = Field(default=300, description="Default TTL for cached introspection results in seconds.")
    cache_max_entries: int = Field(default=10000, description="Maximum number of cached introspection results.")

    @model_validator(mode="before")
    @classmethod
    def migrate_deprecated_audience_alias(cls, data: Any) -> Any:
        """Map deprecated ``audience`` into ``authorized_audiences`` when needed."""
        if not isinstance(data, dict):
            return data
        if data.get("authorized_audiences") is None and data.get("audience") is not None:
            warnings.warn(
                "JWTBearerAuthenticationConfig.audience is deprecated; use authorized_audiences=[...] instead",
                DeprecationWarning,
                stacklevel=2,
            )
            return {**data, "authorized_audiences": data["audience"]}
        return data

    @field_validator("authorized_audiences", mode="before")
    @classmethod
    def validate_authorized_audiences(cls, v: str | list[str] | None) -> list[str]:
        """Validate the authorized audiences.

        Example:
            "aud1,aud2,aud3" -> ["aud1", "aud2", "aud3"]
            ["aud1", "aud2", "aud3"] -> ["aud1", "aud2", "aud3"]
        """
        if v is None:
            raise ValueError("authorized_audiences is required and must be non-empty")
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


class JWTBearerAuthenticationConfigBuilder:
    """Builder for the JWT bearer authentication configuration.

    The builder will build the JWT bearer authentication configuration from the application YAML file.
    It must be used in the configuration hook of the application.
    """

    APPLICATION_YAML_BASE_JWT_CONFIG_KEY: str = "jwt_configs"

    def __init__(self, key: str) -> None:
        """Initialize the JWT bearer authentication configuration builder.

        Args:
            key: The key of the JWT bearer authentication configuration.
        """
        if not key or len(key) == 0:
            raise JWTBearerAuthenticationConfigBuilderError("Key cannot be empty")

        self._key: str = key
        self._config_key: str = f"{self.APPLICATION_YAML_BASE_JWT_CONFIG_KEY}.{self._key}"
        self._config: JWTBearerAuthenticationConfig | None = None
        self._package_name: str | None = None
        self._filename: str | None = None

    def add_application_yaml_path(self, package_name: str, filename: str) -> Self:
        """Add the application YAML path to the builder."""
        self._package_name = package_name
        self._filename = filename
        return self

    def _build_config_from_application_yaml(self) -> JWTBearerAuthenticationConfig:
        """Build the JWT bearer authentication configuration from the application YAML."""
        if self._package_name is None or self._filename is None:
            raise JWTBearerAuthenticationConfigBuilderError("Package name and filename must be provided")

        try:
            return build_config_from_file_in_package(
                package_name=self._package_name,
                filename=self._filename,
                config_class=JWTBearerAuthenticationConfig,
                yaml_base_key=self._config_key,
            )
        except (UnableToReadConfigFileError, ValueErrorConfigError) as error:
            raise JWTBearerAuthenticationConfigBuilderError("Failed to read the application YAML file") from error

    def build(self) -> JWTBearerAuthenticationConfig:
        """Build the JWT bearer authentication configuration.

        Returns:
            JWTBearerAuthenticationConfig: The built JWT bearer authentication configuration.

        Raises:
            JWTBearerAuthenticationConfigBuilderError: When no configuration is provided
            and the application YAML path is not provided.
        """
        if self._config is None and self._package_name is not None and self._filename is not None:
            self._config = self._build_config_from_application_yaml()

        if self._config is None:
            raise JWTBearerAuthenticationConfigBuilderError(
                "Neither a JWT bearer authentication configuration nor an application YAML path was provided"
            )

        return self._config

    @property
    def config(self) -> JWTBearerAuthenticationConfig:
        """Get the JWT bearer authentication configuration."""
        if self._config is None:
            raise JWTBearerAuthenticationConfigBuilderError("No configuration found")
        return self._config


class DependsJWTBearerAuthenticationConfig:
    """Dependency for the JWT bearer authentication configuration."""

    STATE_PREFIX_KEY: str = "jwt_configs"

    def __init__(self, key: str) -> None:
        """Initialize the dependency for the JWT bearer authentication configuration."""
        self._key: str = key

    @classmethod
    def export_from_state(cls, state: State, key: str) -> JWTBearerAuthenticationConfig:
        """Export the JWT bearer authentication configuration from the state."""
        config: JWTBearerAuthenticationConfig | None = getattr(state, f"{cls.STATE_PREFIX_KEY}.{key}", None)
        if config is None:
            raise JWTBearerAuthenticationConfigBuilderError(
                "JWT bearer authentication configuration not found in the state"
            )
        return config

    @classmethod
    def import_to_state(cls, state: State, config: JWTBearerAuthenticationConfig, key: str) -> None:
        """Import the JWT bearer authentication configuration to the state."""
        setattr(state, f"{cls.STATE_PREFIX_KEY}.{key}", config)

    def __call__(self, request: Request) -> JWTBearerAuthenticationConfig:
        """Dependency for the JWT bearer authentication configuration."""
        return self.export_from_state(state=request.app.state, key=self._key)
