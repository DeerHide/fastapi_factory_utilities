"""Provides the configurations for the JWT bearer token."""

from typing import ClassVar, Self

from fastapi import Request
from fastapi.datastructures import State
from jwt.algorithms import get_default_algorithms, requires_cryptography
from pydantic import BaseModel, ConfigDict, Field, field_validator

from fastapi_factory_utilities.core.security.jwt.types import OAuth2Issuer
from fastapi_factory_utilities.core.utils.configs import (
    UnableToReadConfigFileError,
    ValueErrorConfigError,
    build_config_from_file_in_package,
)

from .exceptions import JWTBearerAuthenticationConfigBuilderError


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
