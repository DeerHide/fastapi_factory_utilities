"""Unit tests for S3 plugin depends."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from opentelemetry.trace import INVALID_SPAN

from fastapi_factory_utilities.core.plugins.s3_plugin.constants import (
    STATE_BUCKET_PREFIX_KEY,
    STATE_S3_CLIENT_KEY,
)
from fastapi_factory_utilities.core.plugins.s3_plugin.depends import S3BucketDepends, depends_s3_client
from fastapi_factory_utilities.core.plugins.s3_plugin.exceptions import S3BucketResourceNotFoundError
from fastapi_factory_utilities.core.plugins.s3_plugin.resources import S3BucketResource


class TestDependsS3Client:
    """Tests for ``depends_s3_client``."""

    def test_returns_shared_client(self) -> None:
        """Shared client is read from application state."""
        mock_client: MagicMock = MagicMock()
        mock_request: MagicMock = MagicMock()
        setattr(mock_request.app.state, STATE_S3_CLIENT_KEY, mock_client)

        assert depends_s3_client(mock_request) is mock_client


class TestS3BucketDepends:
    """Tests for ``S3BucketDepends``."""

    def test_call_resolves_resource(self) -> None:
        """Named bucket resource is resolved from state."""
        resource: S3BucketResource = S3BucketResource(key="media", bucket_name="media-bucket", client=MagicMock())
        mock_request: MagicMock = MagicMock()
        setattr(mock_request.app.state, f"{STATE_BUCKET_PREFIX_KEY}media", resource)

        result: S3BucketResource = S3BucketDepends("media")(mock_request)
        assert result is resource
        assert result.bucket_name == "media-bucket"

    def test_call_missing_key_raises(self) -> None:
        """Unknown logical key raises not-found error."""
        mock_request: MagicMock = MagicMock()
        mock_request.app.state = MagicMock(spec=[])

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN
                with pytest.raises(S3BucketResourceNotFoundError) as exc_info:
                    S3BucketDepends("missing")(mock_request)

        assert getattr(exc_info.value, "key") == "missing"

    def test_multiple_keys(self) -> None:
        """Different depends instances resolve distinct resources sharing a client."""
        shared_client: MagicMock = MagicMock()
        media: S3BucketResource = S3BucketResource(key="media", bucket_name="media-bucket", client=shared_client)
        thumbs: S3BucketResource = S3BucketResource(key="thumbs", bucket_name="thumbs-bucket", client=shared_client)
        mock_request: MagicMock = MagicMock()
        setattr(mock_request.app.state, f"{STATE_BUCKET_PREFIX_KEY}media", media)
        setattr(mock_request.app.state, f"{STATE_BUCKET_PREFIX_KEY}thumbs", thumbs)

        resolved_media: S3BucketResource = S3BucketDepends("media")(mock_request)
        resolved_thumbs: S3BucketResource = S3BucketDepends("thumbs")(mock_request)

        assert resolved_media is media
        assert resolved_thumbs is thumbs
        assert resolved_media.client is resolved_thumbs.client
