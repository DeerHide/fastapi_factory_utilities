"""Unit tests for S3 plugin builder."""

from unittest.mock import MagicMock

import pytest
from botocore.config import Config

from fastapi_factory_utilities.core.plugins.s3_plugin.builder import S3Builder
from fastapi_factory_utilities.core.plugins.s3_plugin.configs import S3Config
from fastapi_factory_utilities.core.plugins.s3_plugin.exceptions import S3PluginConfigError


def _config(**overrides: object) -> S3Config:
    """Build an S3Config for tests."""
    payload: dict[str, object] = {
        "endpoint_url": "http://localhost:9000",
        "access_key_id": "akid",
        "secret_access_key": "secret",
        "buckets": {"media": "media-bucket", "thumbs": "thumbs-bucket"},
    }
    payload.update(overrides)
    return S3Config.model_validate(payload)


class TestS3Builder:
    """Tests for ``S3Builder``."""

    def test_build_all_with_injected_config(self) -> None:
        """Injected config skips YAML and builds client kwargs plus buckets."""
        mock_app: MagicMock = MagicMock()
        mock_app.PACKAGE_NAME = "unused"
        builder: S3Builder = S3Builder(application=mock_app, s3_config=_config()).build_all()

        assert builder.config is not None
        assert builder.selected_buckets == {"media": "media-bucket", "thumbs": "thumbs-bucket"}
        assert builder.client_kwargs is not None
        assert builder.client_kwargs["endpoint_url"] == "http://localhost:9000"
        assert builder.client_kwargs["aws_access_key_id"] == "akid"
        assert builder.client_kwargs["region_name"] == "us-east-1"
        assert builder.client_kwargs["verify"] is True
        assert isinstance(builder.client_kwargs["config"], Config)

    def test_keys_subset(self) -> None:
        """Constructor keys select a subset of configured buckets."""
        mock_app: MagicMock = MagicMock()
        builder: S3Builder = S3Builder(
            application=mock_app,
            s3_config=_config(),
            keys=["media"],
        ).build_all()

        assert builder.selected_buckets == {"media": "media-bucket"}

    def test_unknown_keys_raise(self) -> None:
        """Unknown requested keys raise a configuration error."""
        mock_app: MagicMock = MagicMock()
        with pytest.raises(S3PluginConfigError, match="Requested bucket keys"):
            S3Builder(application=mock_app, s3_config=_config(), keys=["missing"]).build_all()

    def test_missing_package_name_without_injected_config(self) -> None:
        """YAML load without PACKAGE_NAME fails."""
        mock_app: MagicMock = MagicMock()
        mock_app.PACKAGE_NAME = ""
        with pytest.raises(S3PluginConfigError, match="package name"):
            S3Builder(application=mock_app).build_all()

    def test_botocore_config_production_defaults(self) -> None:
        """Client botocore Config uses path-style addressing and retries."""
        mock_app: MagicMock = MagicMock()
        builder: S3Builder = S3Builder(application=mock_app, s3_config=_config()).build_all()
        assert builder.client_kwargs is not None
        botocore_config: Config = builder.client_kwargs["config"]
        assert botocore_config.signature_version == "s3v4"
        assert botocore_config.s3.get("addressing_style") == "path"  # type: ignore[union-attr]
        assert botocore_config.connect_timeout == S3Builder.CONNECT_TIMEOUT_S
        assert botocore_config.read_timeout == S3Builder.READ_TIMEOUT_S
        assert botocore_config.retries.get("max_attempts") == S3Builder.MAX_ATTEMPTS  # type: ignore[union-attr]
        assert botocore_config.retries.get("mode") == "standard"  # type: ignore[union-attr]
        assert builder.presign_client_kwargs is None

    def test_presign_client_kwargs_uses_host_only(self) -> None:
        """Presign client signs against scheme://netloc, not the path prefix."""
        mock_app: MagicMock = MagicMock()
        builder: S3Builder = S3Builder(
            application=mock_app,
            s3_config=_config(presign_endpoint_url="https://storage.example.com/storage"),
        ).build_all()
        assert builder.presign_client_kwargs is not None
        assert builder.presign_client_kwargs["endpoint_url"] == "https://storage.example.com"
