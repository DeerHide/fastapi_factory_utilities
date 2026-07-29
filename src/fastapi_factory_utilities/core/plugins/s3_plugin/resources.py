"""S3 / MinIO bucket resource types."""

from typing import Any


class S3BucketResource:
    """Bucket-scoped handle wrapping a shared async S3 client."""

    def __init__(self, *, key: str, bucket_name: str, client: Any) -> None:
        """Initialize the bucket resource.

        Args:
            key: Logical bucket key from configuration (DI key).
            bucket_name: Physical S3 / MinIO bucket name.
            client: Shared aiobotocore S3 client.
        """
        self._key: str = key
        self._bucket_name: str = bucket_name
        self._client: Any = client

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
