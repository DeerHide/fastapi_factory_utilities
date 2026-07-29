"""Provides FastAPI dependencies for the S3 plugin."""

from typing import Any

from fastapi import Request
from fastapi.datastructures import State

from .constants import STATE_BUCKET_PREFIX_KEY, STATE_S3_CLIENT_KEY
from .exceptions import S3BucketResourceNotFoundError
from .resources import S3BucketResource


def depends_s3_client(request: Request) -> Any:
    """Acquire the shared async S3 client from the request.

    Args:
        request: The incoming FastAPI request.

    Returns:
        The shared aiobotocore S3 client.
    """
    return getattr(request.app.state, STATE_S3_CLIENT_KEY)


class S3BucketDepends:
    """FastAPI dependency that resolves a named S3 bucket resource."""

    def __init__(self, key: str) -> None:
        """Initialize the bucket depends.

        Args:
            key: Logical bucket key declared in ``s3.buckets``.
        """
        self._key: str = key

    @classmethod
    def export_from_state(cls, state: State, key: str) -> S3BucketResource:
        """Export the S3 bucket resource from application state.

        Args:
            state: FastAPI application state.
            key: Logical bucket key.

        Returns:
            The bucket-scoped resource.

        Raises:
            S3BucketResourceNotFoundError: If the key is not present in state.
        """
        resource: S3BucketResource | None = getattr(state, f"{STATE_BUCKET_PREFIX_KEY}{key}", None)
        if resource is None:
            raise S3BucketResourceNotFoundError(
                "S3 bucket resource not found in the application state.",
                key=key,
            )
        return resource

    def __call__(self, request: Request) -> S3BucketResource:
        """Resolve the bucket resource for the given request.

        Args:
            request: The incoming FastAPI request.

        Returns:
            The bucket-scoped resource.
        """
        return self.export_from_state(state=request.app.state, key=self._key)
