"""Backward-compatible aliases for S3 plugin state keys."""

from fastapi_factory_utilities.core.plugins.state import S3_BUCKET_PREFIX, S3_CLIENT

STATE_S3_CLIENT_KEY: str = S3_CLIENT.attr
STATE_BUCKET_PREFIX_KEY: str = S3_BUCKET_PREFIX.attr
