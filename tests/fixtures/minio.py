"""Fixtures for MinIO / S3 plugin integration tests."""

from collections.abc import AsyncGenerator, Callable, Generator
from typing import Any
from uuid import uuid4

import aioboto3
import pytest
import pytest_asyncio
from testcontainers.community.minio import MinioContainer

from fastapi_factory_utilities.core.plugins.s3_plugin import S3Config, S3Plugin


@pytest.fixture(scope="session", name="minio_container")
def fixture_minio_container() -> Generator[MinioContainer, None, None]:
    """Start a session-scoped MinIO container."""
    with MinioContainer() as container:
        yield container


def build_s3_config_from_container(
    minio_container: MinioContainer,
    buckets: dict[str, str],
) -> S3Config:
    """Build an ``S3Config`` pointed at a running MinIO container.

    Args:
        minio_container: Running MinIO testcontainer.
        buckets: Logical key → physical bucket name mapping.

    Returns:
        An ``S3Config`` suitable for ``S3Plugin`` injection.
    """
    config: dict[str, str] = minio_container.get_config()
    return S3Config.model_validate(
        {
            "endpoint_url": f"http://{config['endpoint']}",
            "access_key_id": config["access_key"],
            "secret_access_key": config["secret_key"],
            "region": "us-east-1",
            "tls_verify": False,
            "buckets": buckets,
        }
    )


@pytest_asyncio.fixture(scope="function", name="s3_buckets")
async def fixture_s3_buckets(minio_container: MinioContainer) -> AsyncGenerator[dict[str, str], None]:
    """Create two uniquely named buckets and yield their logical→physical mapping.

    Args:
        minio_container: Running MinIO testcontainer.

    Yields:
        Mapping with ``media`` and ``thumbs`` logical keys.
    """
    suffix: str = uuid4().hex[:8]
    buckets: dict[str, str] = {
        "media": f"media-{suffix}",
        "thumbs": f"thumbs-{suffix}",
    }
    config: S3Config = build_s3_config_from_container(minio_container=minio_container, buckets=buckets)
    session: aioboto3.Session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=config.endpoint_url,
        aws_access_key_id=config.access_key_id,
        aws_secret_access_key=config.secret_access_key,
        region_name=config.region,
        verify=False,
    ) as client:
        for bucket_name in buckets.values():
            await client.create_bucket(Bucket=bucket_name)
        yield buckets
        for bucket_name in buckets.values():
            try:
                response: dict[str, Any] = await client.list_objects_v2(Bucket=bucket_name)
                for obj in response.get("Contents") or []:
                    await client.delete_object(Bucket=bucket_name, Key=obj["Key"])
                await client.delete_bucket(Bucket=bucket_name)
            except Exception:  # pylint: disable=broad-except
                pass


@pytest.fixture(scope="function", name="s3_plugin_factory")
def fixture_s3_plugin_factory(
    minio_container: MinioContainer,
    s3_buckets: dict[str, str],
) -> Callable[[list[str] | None], S3Plugin]:
    """Build an ``S3Plugin`` factory bound to the MinIO container and test buckets.

    Args:
        minio_container: Running MinIO testcontainer.
        s3_buckets: Physical buckets already created for this test.

    Returns:
        Factory that returns a configured ``S3Plugin``.
    """

    def _factory(keys: list[str] | None = None) -> S3Plugin:
        return S3Plugin(
            keys=keys,
            s3_config=build_s3_config_from_container(minio_container=minio_container, buckets=s3_buckets),
        )

    return _factory


@pytest_asyncio.fixture(scope="function", name="s3_plugin")
async def fixture_s3_plugin(
    s3_plugin_factory: Callable[[list[str] | None], S3Plugin],
) -> S3Plugin:
    """Create an unstarted ``S3Plugin`` for the current MinIO + buckets."""
    return s3_plugin_factory(None)
