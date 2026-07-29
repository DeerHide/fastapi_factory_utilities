"""Unit tests for S3BucketResource."""

from unittest.mock import MagicMock

from fastapi_factory_utilities.core.plugins.s3_plugin.resources import S3BucketResource


class TestS3BucketResource:
    """Tests for ``S3BucketResource``."""

    def test_properties(self) -> None:
        """Resource exposes key, bucket_name, and shared client."""
        client: MagicMock = MagicMock()
        resource: S3BucketResource = S3BucketResource(key="media", bucket_name="media-bucket", client=client)

        assert resource.key == "media"
        assert resource.bucket_name == "media-bucket"
        assert resource.client is client
