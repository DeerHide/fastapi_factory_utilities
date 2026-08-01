"""Unit tests for S3 plugin configuration."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from fastapi_factory_utilities.core.plugins.s3_plugin.configs import S3Config


def _base_kwargs() -> dict[str, object]:
    """Return minimal valid S3Config kwargs."""
    return {
        "endpoint_url": "https://s3.example.com",
        "access_key_id": "akid",
        "secret_access_key": "secret",
        "buckets": {"media": "media-bucket"},
    }


class TestS3Config:
    """Tests for ``S3Config``."""

    def test_defaults(self) -> None:
        """Production defaults apply when optional fields are omitted."""
        config: S3Config = S3Config(**_base_kwargs())  # type: ignore[arg-type]

        assert config.region == "us-east-1"
        assert config.tls_verify is True
        assert config.ca_bundle is None
        assert config.resolve_verify() is True

    def test_extra_forbidden(self) -> None:
        """Unknown fields are rejected."""
        with pytest.raises(ValidationError):
            S3Config(**{**_base_kwargs(), "unknown": "x"})  # type: ignore[arg-type]

    def test_empty_buckets_rejected(self) -> None:
        """Empty buckets mapping is rejected."""
        with pytest.raises(ValidationError):
            S3Config(**{**_base_kwargs(), "buckets": {}})  # type: ignore[arg-type]

    def test_empty_bucket_name_rejected(self) -> None:
        """Empty physical bucket names are rejected."""
        with pytest.raises(ValidationError):
            S3Config(**{**_base_kwargs(), "buckets": {"media": ""}})  # type: ignore[arg-type]

    def test_ca_bundle_must_be_file(self, tmp_path: Path) -> None:
        """ca_bundle must point to an existing regular file when set."""
        missing: Path = tmp_path / "missing.pem"
        with pytest.raises(ValidationError):
            S3Config(**{**_base_kwargs(), "ca_bundle": missing})  # type: ignore[arg-type]

        ca_file: Path = tmp_path / "ca.pem"
        ca_file.write_text("dummy", encoding="utf-8")
        config: S3Config = S3Config(**{**_base_kwargs(), "ca_bundle": ca_file})  # type: ignore[arg-type]
        assert config.resolve_verify() == str(ca_file)

    def test_empty_ca_bundle_becomes_none(self) -> None:
        """Empty-string ca_bundle normalizes to None."""
        config: S3Config = S3Config(**{**_base_kwargs(), "ca_bundle": ""})  # type: ignore[arg-type]
        assert config.ca_bundle is None

    def test_presign_defaults(self) -> None:
        """Presign fields default to unset / 900s."""
        config: S3Config = S3Config(**_base_kwargs())  # type: ignore[arg-type]
        assert config.presign_endpoint_url is None
        assert config.presign_expiry_seconds == 900  # noqa: PLR2004
        assert config.resolve_presign_host() is None
        assert config.resolve_presign_path_prefix() is None

    def test_presign_host_and_path_split(self) -> None:
        """Presign endpoint splits into host-only signing URL and path prefix."""
        config: S3Config = S3Config(
            **{
                **_base_kwargs(),
                "presign_endpoint_url": "https://storage.example.com/storage",
            }
        )  # type: ignore[arg-type]
        assert config.resolve_presign_host() == "https://storage.example.com"
        assert config.resolve_presign_path_prefix() == "/storage"

    def test_empty_presign_endpoint_becomes_none(self) -> None:
        """Empty-string presign_endpoint_url normalizes to None."""
        config: S3Config = S3Config(**{**_base_kwargs(), "presign_endpoint_url": ""})  # type: ignore[arg-type]
        assert config.presign_endpoint_url is None
