"""Provides FastAPI dependencies for the S3 plugin."""

from typing import Any

from fastapi import Request

from fastapi_factory_utilities.core.plugins.depends import NamedResourceDepends
from fastapi_factory_utilities.core.plugins.s3_plugin.exceptions import S3BucketResourceNotFoundError
from fastapi_factory_utilities.core.plugins.s3_plugin.resources import S3BucketResource
from fastapi_factory_utilities.core.plugins.state import S3_BUCKET_PREFIX, S3_CLIENT, get_from_state


def depends_s3_client(request: Request) -> Any:
    """Acquire the shared async S3 client from the request.

    Args:
        request: The incoming FastAPI request.

    Returns:
        The shared aiobotocore S3 client.
    """
    return get_from_state(request.app.state, S3_CLIENT)


class S3BucketDepends(NamedResourceDepends[S3BucketResource]):
    """FastAPI dependency that resolves a named S3 bucket resource."""

    prefix = S3_BUCKET_PREFIX
    not_found_error = S3BucketResourceNotFoundError
    not_found_message = "S3 bucket resource not found in the application state."
