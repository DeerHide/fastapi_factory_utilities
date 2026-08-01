"""Provides the configuration for the S3 plugin."""

from pathlib import Path
from typing import Self
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class S3Config(BaseModel):
    """Provides the configuration model for the S3 plugin."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    endpoint_url: str
    access_key_id: str
    secret_access_key: str
    region: str = "us-east-1"
    tls_verify: bool = True
    ca_bundle: Path | None = None
    buckets: dict[str, str] = Field(min_length=1)
    presign_endpoint_url: str | None = None
    presign_expiry_seconds: int = Field(default=900, ge=1)

    @field_validator("ca_bundle", mode="before")
    @classmethod
    def normalize_ca_bundle(cls, value: object) -> Path | None:
        """Normalize empty ca_bundle values to None and coerce strings to Path.

        Args:
            value: Raw ca_bundle value from YAML or constructors.

        Returns:
            A Path when a non-empty value is provided, otherwise None.
        """
        if value is None or value == "":
            return None
        if isinstance(value, Path):
            return value
        return Path(str(value))

    @field_validator("ca_bundle")
    @classmethod
    def validate_ca_bundle(cls, value: Path | None) -> Path | None:
        """Ensure a configured CA bundle path exists and is a file.

        Args:
            value: Optional CA bundle path.

        Returns:
            The validated path, or None.

        Raises:
            ValueError: If the path is set but missing or not a regular file.
        """
        if value is not None and not value.is_file():
            raise ValueError("ca_bundle path must exist and be a regular file")
        return value

    @field_validator("presign_endpoint_url", mode="before")
    @classmethod
    def normalize_presign_endpoint_url(cls, value: object) -> str | None:
        """Treat empty presign_endpoint_url as unset.

        Args:
            value: Raw presign endpoint value.

        Returns:
            A non-empty string, or None.
        """
        if value is None or value == "":
            return None
        return str(value)

    @field_validator("buckets")
    @classmethod
    def validate_buckets(cls, value: dict[str, str]) -> dict[str, str]:
        """Reject empty logical keys or empty physical bucket names.

        Args:
            value: Mapping of logical bucket keys to physical bucket names.

        Returns:
            The validated mapping.

        Raises:
            ValueError: If any key or bucket name is empty.
        """
        if not value:
            raise ValueError("buckets must contain at least one entry")
        for key, bucket_name in value.items():
            if not key or not key.strip():
                raise ValueError("bucket logical keys must be non-empty")
            if not bucket_name or not bucket_name.strip():
                raise ValueError(f"bucket name for key {key!r} must be non-empty")
        return value

    @model_validator(mode="after")
    def validate_credentials(self) -> Self:
        """Ensure access credentials are non-empty.

        Returns:
            The validated configuration.

        Raises:
            ValueError: If credentials are missing.
        """
        if not self.access_key_id or not self.secret_access_key:
            raise ValueError("Both access_key_id and secret_access_key must be set")
        if not self.endpoint_url:
            raise ValueError("endpoint_url must be set")
        return self

    def resolve_verify(self) -> bool | str:
        """Resolve the botocore/aioboto3 ``verify`` argument.

        Returns:
            A CA bundle path string when configured, otherwise the tls_verify flag.
        """
        if self.ca_bundle is not None:
            return str(self.ca_bundle)
        return self.tls_verify

    def resolve_presign_host(self) -> str | None:
        """Return ``scheme://netloc`` of ``presign_endpoint_url`` for botocore signing.

        botocore folds the endpoint path into the SigV4 canonical URI; Gateways that
        strip a path prefix before MinIO validates the signature require signing
        against the host only, with the path re-injected after.

        Returns:
            Host-only endpoint URL, or None when presigning is unset.
        """
        if not self.presign_endpoint_url:
            return None
        parsed = urlparse(self.presign_endpoint_url)
        if not parsed.scheme or not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"

    def resolve_presign_path_prefix(self) -> str | None:
        """Return the path prefix of ``presign_endpoint_url`` (e.g. ``/storage``).

        Returns:
            Path prefix without trailing slash, or None when unset / empty.
        """
        if not self.presign_endpoint_url:
            return None
        prefix: str = urlparse(self.presign_endpoint_url).path.rstrip("/")
        return prefix or None
