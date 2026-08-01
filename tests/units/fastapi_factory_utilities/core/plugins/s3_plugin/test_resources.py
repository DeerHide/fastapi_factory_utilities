"""Unit tests for S3BucketResource."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from botocore.exceptions import ClientError

from fastapi_factory_utilities.core.plugins.s3_plugin.exceptions import S3PresignNotConfiguredError
from fastapi_factory_utilities.core.plugins.s3_plugin.resources import S3BucketResource


def _resource(**overrides: Any) -> S3BucketResource:
    """Build a resource with a MagicMock client."""
    kwargs: dict[str, Any] = {
        "key": "media",
        "bucket_name": "media-bucket",
        "client": MagicMock(),
        "endpoint_url": "http://localhost:9000",
    }
    kwargs.update(overrides)
    return S3BucketResource(**kwargs)


class TestS3BucketResource:
    """Tests for ``S3BucketResource``."""

    def test_properties(self) -> None:
        """Resource exposes key, bucket_name, client, and endpoint."""
        client: MagicMock = MagicMock()
        resource: S3BucketResource = _resource(client=client)

        assert resource.key == "media"
        assert resource.bucket_name == "media-bucket"
        assert resource.client is client
        assert resource.endpoint_url == "http://localhost:9000"

    def test_object_url_percent_encodes_key(self) -> None:
        """Writer percent-encodes unsafe key characters."""
        resource: S3BucketResource = _resource()
        assert resource.object_url("a b/c#d") == "http://localhost:9000/media-bucket/a%20b/c%23d"

    def test_key_from_url_path_style_and_vhost(self) -> None:
        """Reader accepts path-style and virtual-host style."""
        resource: S3BucketResource = _resource()
        assert resource.key_from_url("http://other-host/media-bucket/realms/x.pdf") == "realms/x.pdf"
        assert resource.key_from_url("http://media-bucket.example.com/realms/x.pdf") == "realms/x.pdf"
        assert resource.key_from_url("http://host/other-bucket/x.pdf") is None

    @pytest.mark.asyncio
    async def test_get_bytes_closes_body(self) -> None:
        """get_bytes reads and closes the response body."""
        body: MagicMock = MagicMock()
        body.read = AsyncMock(return_value=b"payload")
        body.close = MagicMock()
        client: MagicMock = MagicMock()
        client.get_object = AsyncMock(return_value={"Body": body})
        resource: S3BucketResource = _resource(client=client)

        assert await resource.get_bytes("obj") == b"payload"
        body.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_put_bytes_returns_object_url(self) -> None:
        """put_bytes uploads and returns the canonical URL."""
        client: MagicMock = MagicMock()
        client.put_object = AsyncMock(return_value={})
        resource: S3BucketResource = _resource(client=client)

        url: str = await resource.put_bytes("k.txt", b"data", content_type="text/plain")
        assert url == "http://localhost:9000/media-bucket/k.txt"
        client.put_object.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_put_file(self, tmp_path: Path) -> None:
        """put_file uploads via upload_file."""
        path: Path = tmp_path / "f.bin"
        path.write_bytes(b"x")
        client: MagicMock = MagicMock()
        client.upload_file = AsyncMock(return_value=None)
        resource: S3BucketResource = _resource(client=client)

        url: str = await resource.put_file("k.bin", path, content_type="application/octet-stream")
        assert url.endswith("/media-bucket/k.bin")
        client.upload_file.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_head_or_none_404(self) -> None:
        """head_or_none returns None on missing objects."""
        client: MagicMock = MagicMock()
        client.head_object = AsyncMock(
            side_effect=ClientError(
                error_response={"Error": {"Code": "404", "Message": "Not Found"}},
                operation_name="HeadObject",
            )
        )
        resource: S3BucketResource = _resource(client=client)
        assert await resource.head_or_none("missing") is None

    @pytest.mark.asyncio
    async def test_list_keys(self) -> None:
        """list_keys paginates list_objects_v2."""

        async def _pages(**_kwargs: object) -> Any:
            yield {"Contents": [{"Key": "a"}, {"Key": "b"}]}
            yield {"Contents": [{"Key": "c"}]}

        paginator: MagicMock = MagicMock()
        paginator.paginate = _pages
        client: MagicMock = MagicMock()
        client.get_paginator.return_value = paginator
        resource: S3BucketResource = _resource(client=client)

        assert await resource.list_keys("prefix/") == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        """Delete calls delete_object."""
        client: MagicMock = MagicMock()
        client.delete_object = AsyncMock(return_value={})
        resource: S3BucketResource = _resource(client=client)
        await resource.delete("k")
        client.delete_object.assert_awaited_once_with(Bucket="media-bucket", Key="k")

    @pytest.mark.asyncio
    async def test_presigned_get_url_requires_presign_client(self) -> None:
        """presigned_get_url raises when presign is not configured."""
        resource: S3BucketResource = _resource()
        with pytest.raises(S3PresignNotConfiguredError):
            await resource.presigned_get_url("k")

    @pytest.mark.asyncio
    async def test_presigned_get_url_injects_path_prefix(self) -> None:
        """presigned_get_url re-injects the public path prefix after signing."""
        presign_client: MagicMock = MagicMock()
        presign_client.generate_presigned_url = AsyncMock(
            return_value="https://storage.example.com/media-bucket/k?X-Amz-Signature=abc"
        )
        resource: S3BucketResource = _resource(
            presign_client=presign_client,
            presign_path_prefix="/storage",
            presign_expiry_seconds=60,
        )
        url: str = await resource.presigned_get_url(
            "k",
            content_disposition='inline; filename="k"',
            content_type="video/mp4",
        )
        assert url.startswith("https://storage.example.com/storage/media-bucket/k?")
        presign_client.generate_presigned_url.assert_awaited_once()
