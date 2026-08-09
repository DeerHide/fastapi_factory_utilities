"""S3 test doubles via moto's ThreadedMotoServer + aioboto3."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi_factory_utilities.core.plugins.s3_plugin.resources import S3BucketResource


@asynccontextmanager
async def moto_s3_client(
    *,
    bucket_names: list[str] | None = None,
) -> AsyncIterator[tuple[Any, str, list[str]]]:
    """Start moto S3 and yield ``(aioboto3_client, endpoint_url, bucket_names)``.

    Args:
        bucket_names: Buckets to create; defaults to ``["test-bucket"]``.

    Yields:
        Tuple of async S3 client, endpoint URL, and created bucket names.

    Raises:
        ImportError: When ``moto`` is not installed.
    """
    try:
        from moto.server import ThreadedMotoServer  # pylint: disable=import-outside-toplevel  # noqa: PLC0415
    except ImportError as error:
        raise ImportError(
            "moto[server] is required for S3 test doubles. "
            "Install with: pip install 'fastapi_factory_utilities[testing]'",
        ) from error

    import aioboto3  # pylint: disable=import-outside-toplevel  # noqa: PLC0415

    names = bucket_names or ["test-bucket"]
    server = ThreadedMotoServer(port=0, verbose=False)
    server.start()
    host, port = server.get_host_and_port()
    endpoint_url = f"http://{host}:{port}"
    session = cast(Any, aioboto3).Session()
    async with session.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
        region_name="us-east-1",
    ) as client:
        for name in names:
            await client.create_bucket(Bucket=name)
        try:
            yield client, endpoint_url, names
        finally:
            server.stop()


def build_s3_bucket_resource(
    client: Any,
    *,
    key: str = "default",
    bucket_name: str,
    endpoint_url: str,
    presign_client: Any | None = None,
) -> S3BucketResource:
    """Wrap a moto/aioboto3 client in :class:`S3BucketResource`.

    Args:
        client: Async S3 client.
        key: Logical DI key.
        bucket_name: Physical bucket name.
        endpoint_url: Endpoint used for object URLs.
        presign_client: Optional client for presigning (defaults to ``client``).

    Returns:
        A bucket resource bound to the given client.
    """
    return S3BucketResource(
        key=key,
        bucket_name=bucket_name,
        client=client,
        endpoint_url=endpoint_url,
        presign_client=presign_client if presign_client is not None else client,
    )
