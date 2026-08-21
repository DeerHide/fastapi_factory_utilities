"""S3 / MinIO Plugin Module."""

# ruff: noqa: E402
from fastapi_factory_utilities.core.plugins.extras import require_extra

require_extra("s3", "aioboto3")

from .configs import S3Config
from .constants import STATE_BUCKET_PREFIX_KEY, STATE_S3_CLIENT_KEY
from .depends import S3BucketDepends, depends_s3_client
from .exceptions import (
    S3BucketNotFoundError,
    S3BucketResourceNotFoundError,
    S3PluginBaseError,
    S3PluginConfigError,
    S3PresignNotConfiguredError,
)
from .plugins import S3Plugin
from .resources import S3BucketResource
from .urls import parse_bucket_and_key

__all__: list[str] = [
    "STATE_BUCKET_PREFIX_KEY",
    "STATE_S3_CLIENT_KEY",
    "S3BucketDepends",
    "S3BucketNotFoundError",
    "S3BucketResource",
    "S3BucketResourceNotFoundError",
    "S3Config",
    "S3Plugin",
    "S3PluginBaseError",
    "S3PluginConfigError",
    "S3PresignNotConfiguredError",
    "depends_s3_client",
    "parse_bucket_and_key",
]
