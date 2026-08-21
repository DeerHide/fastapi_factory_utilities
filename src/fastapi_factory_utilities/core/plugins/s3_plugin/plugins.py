"""S3 / MinIO plugin package."""

from contextlib import AsyncExitStack
from typing import Any

from aioboto3.session import Session
from botocore.exceptions import ClientError
from structlog.stdlib import BoundLogger, get_logger

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.plugins.state import S3_BUCKET_PREFIX, S3_CLIENT
from fastapi_factory_utilities.core.plugins.status import PluginStatusMixin
from fastapi_factory_utilities.core.services.status.enums import ComponentTypeEnum

from .builder import S3Builder
from .configs import S3Config
from .exceptions import S3BucketNotFoundError
from .resources import S3BucketResource

_logger: BoundLogger = get_logger()


class S3Plugin(PluginStatusMixin, PluginAbstract):
    """S3 / MinIO plugin using a shared long-lived aioboto3 client."""

    def __init__(
        self,
        keys: list[str] | None = None,
        s3_config: S3Config | None = None,
    ) -> None:
        """Initialize the S3 plugin.

        Args:
            keys: Optional subset of ``s3.buckets`` logical keys to activate.
            s3_config: Optional injected configuration (skips YAML).
        """
        super().__init__()
        self._keys: list[str] | None = keys
        self._s3_config: S3Config | None = s3_config
        self._builder: S3Builder | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._s3_client: Any | None = None
        self._presign_client: Any | None = None
        self._bucket_resources: dict[str, S3BucketResource] = {}

    def on_load(self) -> None:
        """Parse and validate S3 configuration without opening network connections."""
        assert self._application is not None
        self._builder = S3Builder(
            application=self._application,
            s3_config=self._s3_config,
            keys=self._keys,
        ).build_all()
        _logger.debug("S3 plugin loaded.", buckets=list((self._builder.selected_buckets or {}).keys()))

    async def _ensure_buckets_exist(self, client: Any, buckets: dict[str, str]) -> None:
        """Hard-fail when a configured physical bucket is missing.

        Args:
            client: Entered aiobotocore S3 client.
            buckets: Logical key → physical bucket name mapping.

        Raises:
            S3BucketNotFoundError: If a declared bucket does not exist.
        """
        for key, bucket_name in buckets.items():
            try:
                await client.head_bucket(Bucket=bucket_name)
            except ClientError as exception:
                error_code: str = str(exception.response.get("Error", {}).get("Code", ""))
                if error_code in {"404", "NoSuchBucket", "NotFound", "403", "AccessDenied"}:
                    # 403 from MinIO/AWS can mean the bucket is missing or inaccessible;
                    # treat both as not ready for declared buckets.
                    raise S3BucketNotFoundError(
                        f"Configured S3 bucket {bucket_name!r} for key {key!r} is missing or inaccessible.",
                        bucket_name=bucket_name,
                        key=key,
                    ) from exception
                raise

    async def on_startup(self) -> None:
        """Open the shared S3 client and register bucket resources."""
        assert self._application is not None
        assert self._builder is not None
        assert self._builder.client_kwargs is not None
        assert self._builder.selected_buckets is not None
        assert self._builder.config is not None

        self._setup_status(component_type=ComponentTypeEnum.STORAGE, identifier="S3")

        try:
            session: Session = Session()
            self._exit_stack = AsyncExitStack()
            # Long-lived stack: enter once here, close in on_shutdown.
            await self._exit_stack.__aenter__()

            self._s3_client = await self._exit_stack.enter_async_context(
                session.client("s3", **self._builder.client_kwargs)
            )
            assert self._s3_client is not None
            await self._warm_soft(self._s3_client.list_buckets, what="S3 connection")
            await self._ensure_buckets_exist(client=self._s3_client, buckets=self._builder.selected_buckets)

            if self._builder.presign_client_kwargs is not None:
                # Public proxy is GET-only; do not warm or head_bucket.
                self._presign_client = await self._exit_stack.enter_async_context(
                    session.client("s3", **self._builder.presign_client_kwargs)
                )
        except Exception:
            self._report_unhealthy()
            if self._exit_stack is not None:
                await self._exit_stack.aclose()
                self._exit_stack = None
                self._s3_client = None
                self._presign_client = None
            _logger.exception("S3 plugin failed to start.")
            raise

        config: S3Config = self._builder.config
        self._add_to_state(key=S3_CLIENT, value=self._s3_client)
        self._bucket_resources = {}
        for key, bucket_name in self._builder.selected_buckets.items():
            resource: S3BucketResource = S3BucketResource(
                key=key,
                bucket_name=bucket_name,
                client=self._s3_client,
                endpoint_url=config.endpoint_url,
                presign_client=self._presign_client,
                presign_path_prefix=config.resolve_presign_path_prefix(),
                presign_expiry_seconds=config.presign_expiry_seconds,
            )
            self._bucket_resources[key] = resource
            self._add_to_state(key=S3_BUCKET_PREFIX.resource_attr(key), value=resource)

        _logger.info(
            "S3 plugin started.",
            endpoint_url=config.endpoint_url,
            buckets=list(self._builder.selected_buckets.keys()),
            presign_configured=self._presign_client is not None,
        )
        self._report_healthy()

    async def on_shutdown(self) -> None:
        """Close the shared S3 client and clear references."""
        if self._exit_stack is not None:
            await self._exit_stack.aclose()
            self._exit_stack = None
        self._s3_client = None
        self._presign_client = None
        self._bucket_resources = {}
        _logger.debug("S3 plugin shutdown.")
