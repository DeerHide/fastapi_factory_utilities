"""Provides the builder for the S3 plugin."""

from typing import Any, Self

from botocore.config import Config
from structlog.stdlib import BoundLogger, get_logger

from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol
from fastapi_factory_utilities.core.utils.importlib import get_path_file_in_package
from fastapi_factory_utilities.core.utils.yaml_reader import (
    UnableToReadYamlFileError,
    YamlFileReader,
)

from .configs import S3Config
from .exceptions import S3PluginConfigError

_logger: BoundLogger = get_logger()


class S3Builder:
    """Factory to create S3 configuration and client kwargs for the plugin."""

    CONNECT_TIMEOUT_S: int = 5
    READ_TIMEOUT_S: int = 60
    MAX_ATTEMPTS: int = 5

    def __init__(
        self,
        application: ApplicationAbstractProtocol,
        s3_config: S3Config | None = None,
        keys: list[str] | None = None,
    ) -> None:
        """Initialize the S3 builder.

        Args:
            application: The application providing PACKAGE_NAME for YAML loading.
            s3_config: Optional injected configuration (skips YAML read).
            keys: Optional subset of bucket logical keys to activate.
        """
        self._application: ApplicationAbstractProtocol = application
        self._config: S3Config | None = s3_config
        self._keys: list[str] | None = keys
        self._selected_buckets: dict[str, str] | None = None
        self._client_kwargs: dict[str, Any] | None = None

    @property
    def config(self) -> S3Config | None:
        """Return the S3 configuration when built."""
        return self._config

    @property
    def selected_buckets(self) -> dict[str, str] | None:
        """Return the activated logical-key → bucket-name mapping."""
        return self._selected_buckets

    @property
    def client_kwargs(self) -> dict[str, Any] | None:
        """Return kwargs for ``session.client("s3", **kwargs)``."""
        return self._client_kwargs

    def build_s3_config(self) -> Self:
        """Build the S3 configuration from YAML or use the injected config.

        Returns:
            Self for chaining.

        Raises:
            S3PluginConfigError: If configuration cannot be loaded or validated.
        """
        if self._config is not None:
            return self

        if self._application.PACKAGE_NAME == "":
            raise S3PluginConfigError("The package name must be set in the concrete application class.")

        try:
            yaml_file_content: dict[str, Any] = YamlFileReader(
                file_path=get_path_file_in_package(
                    filename="application.yaml",
                    package=self._application.PACKAGE_NAME,
                ),
                yaml_base_key="s3",
                use_environment_injection=True,
            ).read()
        except (FileNotFoundError, ImportError, UnableToReadYamlFileError) as exception:
            raise S3PluginConfigError("Unable to read the application configuration file.") from exception

        try:
            self._config = S3Config.model_validate(yaml_file_content)
        except ValueError as exception:
            raise S3PluginConfigError("Unable to create the application configuration model.") from exception
        return self

    def build_selected_buckets(self) -> Self:
        """Resolve which configured buckets this plugin instance activates.

        Returns:
            Self for chaining.

        Raises:
            S3PluginConfigError: If config is missing or requested keys are unknown.
        """
        if self._config is None:
            raise S3PluginConfigError(
                "S3 configuration is not set. Provide the S3 configuration using "
                "build_s3_config method or through parameter."
            )

        if self._keys is None:
            self._selected_buckets = dict(self._config.buckets)
            return self

        missing_keys: list[str] = [key for key in self._keys if key not in self._config.buckets]
        if missing_keys:
            raise S3PluginConfigError(
                f"Requested bucket keys are not present in s3.buckets configuration: {missing_keys!r}"
            )
        self._selected_buckets = {key: self._config.buckets[key] for key in self._keys}
        return self

    def build_client_kwargs(self) -> Self:
        """Build aioboto3 / botocore client kwargs from configuration.

        Returns:
            Self for chaining.

        Raises:
            S3PluginConfigError: If configuration is not set.
        """
        if self._config is None:
            raise S3PluginConfigError(
                "S3 configuration is not set. Provide the S3 configuration using "
                "build_s3_config method or through parameter."
            )

        botocore_config: Config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=self.CONNECT_TIMEOUT_S,
            read_timeout=self.READ_TIMEOUT_S,
            retries={"max_attempts": self.MAX_ATTEMPTS, "mode": "standard"},
        )
        self._client_kwargs = {
            "endpoint_url": self._config.endpoint_url,
            "aws_access_key_id": self._config.access_key_id,
            "aws_secret_access_key": self._config.secret_access_key,
            "region_name": self._config.region,
            "verify": self._config.resolve_verify(),
            "config": botocore_config,
        }
        return self

    def build_all(self) -> Self:
        """Build configuration, selected buckets, and client kwargs.

        Returns:
            Self for chaining.
        """
        self.build_s3_config()
        self.build_selected_buckets()
        self.build_client_kwargs()
        return self
