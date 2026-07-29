"""S3 / MinIO Plugin Module."""

from .configs import S3Config
from .constants import STATE_BUCKET_PREFIX_KEY, STATE_S3_CLIENT_KEY
from .depends import S3BucketDepends, depends_s3_client
from .exceptions import (
    S3BucketNotFoundError,
    S3BucketResourceNotFoundError,
    S3PluginBaseError,
    S3PluginConfigError,
)
from .plugins import S3Plugin
from .resources import S3BucketResource

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
    "depends_s3_client",
]
