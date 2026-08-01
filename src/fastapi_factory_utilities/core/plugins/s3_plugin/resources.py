"""S3 / MinIO bucket resource types."""

from pathlib import Path
from typing import Any

from botocore.exceptions import ClientError

from .exceptions import S3PresignNotConfiguredError
from .urls import build_object_url, inject_public_path_prefix
from .urls import key_from_url as _key_from_url


class S3BucketResource:
    """Bucket-scoped handle wrapping a shared async S3 client."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        key: str,
        bucket_name: str,
        client: Any,
        endpoint_url: str,
        presign_client: Any | None = None,
        presign_path_prefix: str | None = None,
        presign_expiry_seconds: int = 900,
    ) -> None:
        """Initialize the bucket resource.

        Args:
            key: Logical bucket key from configuration (DI key).
            bucket_name: Physical S3 / MinIO bucket name.
            client: Shared aiobotocore S3 client for data-plane ops.
            endpoint_url: Internal endpoint used to build persisted object URLs.
            presign_client: Optional client bound to the public signing host.
            presign_path_prefix: Path segment to re-inject after signing (e.g. ``/storage``).
            presign_expiry_seconds: Default presigned GET lifetime.
        """
        self._key: str = key
        self._bucket_name: str = bucket_name
        self._client: Any = client
        self._endpoint_url: str = endpoint_url
        self._presign_client: Any | None = presign_client
        self._presign_path_prefix: str | None = presign_path_prefix
        self._presign_expiry_seconds: int = presign_expiry_seconds

    @property
    def key(self) -> str:
        """Return the logical bucket key."""
        return self._key

    @property
    def bucket_name(self) -> str:
        """Return the physical bucket name."""
        return self._bucket_name

    @property
    def client(self) -> Any:
        """Return the shared async S3 client."""
        return self._client

    @property
    def endpoint_url(self) -> str:
        """Return the internal endpoint URL used for object URLs."""
        return self._endpoint_url

    def object_url(self, key: str) -> str:
        """Build a path-style object URL for ``key``."""
        return build_object_url(endpoint_url=self._endpoint_url, bucket_name=self._bucket_name, key=key)

    def key_from_url(self, url: str) -> str | None:
        """Extract the object key for this bucket from a stored URL."""
        return _key_from_url(url=url, bucket_name=self._bucket_name)

    async def get_bytes(self, key: str) -> bytes:
        """Download object bytes.

        Args:
            key: Object key inside the bucket.

        Returns:
            Object body.
        """
        response = await self._client.get_object(Bucket=self._bucket_name, Key=key)
        body = response["Body"]
        try:
            return await body.read()
        finally:
            body.close()

    async def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> str:
        """Upload bytes and return the internal object URL.

        Args:
            key: Object key inside the bucket.
            data: Object body.
            content_type: Optional Content-Type.

        Returns:
            Path-style object URL.
        """
        kwargs: dict[str, Any] = {"Bucket": self._bucket_name, "Key": key, "Body": data}
        if content_type is not None:
            kwargs["ContentType"] = content_type
        await self._client.put_object(**kwargs)
        return self.object_url(key)

    async def put_file(self, key: str, path: Path, *, content_type: str | None = None) -> str:
        """Upload a local file and return the internal object URL.

        Args:
            key: Object key inside the bucket.
            path: Local file path.
            content_type: Optional Content-Type.

        Returns:
            Path-style object URL.
        """
        extra_args: dict[str, str] | None = {"ContentType": content_type} if content_type else None
        await self._client.upload_file(
            Filename=str(path),
            Bucket=self._bucket_name,
            Key=key,
            ExtraArgs=extra_args,
        )
        return self.object_url(key)

    async def download_to_file(self, key: str, path: Path) -> None:
        """Download an object to a local file path.

        Args:
            key: Object key inside the bucket.
            path: Destination path (parent directories must exist).
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as file_obj:
            await self._client.download_fileobj(Bucket=self._bucket_name, Key=key, Fileobj=file_obj)

    async def head_or_none(self, key: str) -> dict[str, Any] | None:
        """Return ``head_object`` metadata, or ``None`` when the object is missing.

        Args:
            key: Object key inside the bucket.

        Returns:
            Head-object response dict, or ``None`` for 404 / NoSuchKey.
        """
        try:
            return await self._client.head_object(Bucket=self._bucket_name, Key=key)
        except ClientError as exception:
            error_code: str = str(exception.response.get("Error", {}).get("Code", ""))
            if error_code in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise

    async def list_keys(self, prefix: str) -> list[str]:
        """List object keys under ``prefix``.

        Args:
            prefix: Key prefix filter.

        Returns:
            Object keys (non-recursive filter is still recursive listing under prefix).
        """
        keys: list[str] = []
        paginator = self._client.get_paginator("list_objects_v2")
        async for page in paginator.paginate(Bucket=self._bucket_name, Prefix=prefix):
            for item in page.get("Contents") or []:
                object_key: str | None = item.get("Key")
                if object_key:
                    keys.append(object_key)
        return keys

    async def delete(self, key: str) -> None:
        """Delete an object.

        Args:
            key: Object key inside the bucket.
        """
        await self._client.delete_object(Bucket=self._bucket_name, Key=key)

    async def presigned_get_url(
        self,
        key: str,
        *,
        expires_in: int | None = None,
        content_disposition: str | None = None,
        content_type: str | None = None,
    ) -> str:
        """Build a presigned GET URL on the public signing endpoint.

        Args:
            key: Object key inside the bucket.
            expires_in: Lifetime in seconds; defaults to configured ``presign_expiry_seconds``.
            content_disposition: Optional ``response-content-disposition``.
            content_type: Optional ``response-content-type``.

        Returns:
            Presigned GET URL with public path prefix applied when configured.

        Raises:
            S3PresignNotConfiguredError: When no presign client is available.
        """
        if self._presign_client is None:
            raise S3PresignNotConfiguredError(
                "presign_endpoint_url is not configured; cannot build a presigned GET URL.",
            )
        params: dict[str, str] = {"Bucket": self._bucket_name, "Key": key}
        if content_disposition is not None:
            params["ResponseContentDisposition"] = content_disposition
        if content_type is not None:
            params["ResponseContentType"] = content_type
        signed: str = await self._presign_client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expires_in if expires_in is not None else self._presign_expiry_seconds,
        )
        return inject_public_path_prefix(signed, self._presign_path_prefix)
