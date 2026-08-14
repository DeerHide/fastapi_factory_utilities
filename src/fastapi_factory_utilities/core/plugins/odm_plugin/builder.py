"""Provides the module for the ODM plugin."""

from typing import Any, ClassVar, Self

from beanie import Document  # pyright: ignore[reportUnknownVariableType]
from bson import CodecOptions
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.mongo_client import AsyncMongoClient
from pymongo.encryption_options import AutoEncryptionOpts
from pymongo.server_api import ServerApi, ServerApiVersion
from structlog.stdlib import get_logger

from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol
from fastapi_factory_utilities.core.utils.configs import build_config_from_file_in_package

from .configs import ODMConfig
from .encryption import (
    VaultUnwrapClient,
    build_schema_map,
    build_startup_probe_schema,
    resolve_or_create_data_key,
    validate_no_index_collisions,
)
from .exceptions import ODMPluginConfigError

_logger = get_logger()


class ODMBuilder:
    """Factory to create the resources for the ODM plugin.

    The factory is responsible for creating the resources for the ODM plugin.
    - The ODM configuration.
    - The ODM client.
    - The ODM database.

    ```python
    # Example of using the ODMFactory
    odm_factory: ODMFactory = ODMFactory(application=application)
    await odm_factory.build_all()
    # Access the ODM database created
    database: AsyncIOMotorDatabase[Any] = odm_factory.database
    ```

    """

    MS_TO_S: ClassVar[int] = 1000
    SLEEP_TIME_S: ClassVar[float] = 0.001

    def __init__(
        self,
        application: ApplicationAbstractProtocol,
        odm_config: ODMConfig | None = None,
        odm_client: AsyncMongoClient[Any] | None = None,
        odm_database: AsyncDatabase[Any] | None = None,
        auto_encryption_opts: AutoEncryptionOpts | None = None,
    ) -> None:
        """Initialize the ODMFactory.

        Args:
            application (BaseApplicationProtocol): The application.
            odm_config (ODMConfig): The ODM configuration for injection. (Default is None)
            odm_client (AsyncMongoClient): The ODM client for injection. (Default is None)
            odm_database (AsyncDatabase): The ODM database for injection. (Default is None)
            auto_encryption_opts (AutoEncryptionOpts): The CSFLE auto encryption options for
                injection. (Default is None)

        """
        self._application: ApplicationAbstractProtocol = application
        self._config: ODMConfig | None = odm_config
        self._odm_client: AsyncMongoClient[Any] | None = odm_client
        self._odm_database: AsyncDatabase[Any] | None = odm_database
        self._auto_encryption_opts: AutoEncryptionOpts | None = auto_encryption_opts

    @property
    def config(self) -> ODMConfig | None:
        """Provide the ODM configuration object.

        Returns:
            ODMConfig: The ODM configuration object.
        """
        return self._config

    @property
    def odm_client(self) -> AsyncMongoClient[Any] | None:
        """Provide the ODM client.

        Returns:
            AsyncMongoClient | None: The ODM client.
        """
        return self._odm_client

    @property
    def odm_database(self) -> AsyncDatabase[Any] | None:
        """Provide the ODM database.

        Returns:
            AsyncDatabase | None: The ODM database.
        """
        return self._odm_database

    @property
    def auto_encryption_opts(self) -> AutoEncryptionOpts | None:
        """Provide the CSFLE auto encryption options, if CSFLE is enabled.

        Returns:
            AutoEncryptionOpts | None: The auto encryption options.
        """
        return self._auto_encryption_opts

    def build_odm_config(
        self,
    ) -> Self:
        """Build the ODM configuration object.

        Returns:
            Self: The ODM factory.

        Raises:
            ODMPluginConfigError: If the package name is not set or the configuration file is not found.
        """
        if self._config is not None:
            return self

        self._config = build_config_from_file_in_package(
            package_name=self._application.PACKAGE_NAME,
            filename="application.yaml",
            config_class=ODMConfig,
            yaml_base_key="odm",
            error_type=ODMPluginConfigError,
        )
        return self

    # ======
    # KEEP IT, Waiting for additional tests
    # @classmethod
    # def _wait_client_to_be_ready(cls, client: AsyncIOMotorClient[Any], timeout_s: int) -> None:
    #     """Wait for the ODM client to be ready.

    #     Args:
    #         client (AsyncIOMotorClient): The ODM client.
    #         timeout_s (int): The timeout in seconds.

    #     Raises:
    #         TimeoutError: If the ODM client is not ready in the given timeout.
    #     """
    #     start_time: float = time.time()
    #     message_time: float = time.time()
    #     while (time.time() - start_time) < (timeout_s):
    #         if len(client.nodes) > 0:  # type: ignore
    #             _logger.info(f"Waiting {(time.time() - start_time)*cls.MS_TO_S}ms for the ODM client to be ready.")
    #             return

    #         if (time.time() - message_time) > 1:
    #             elaps_time: float = time.time() - start_time
    #             _logger.debug(f"Waiting for the ODM client to be ready. (from {int(elaps_time)}s) ")
    #             message_time = time.time()
    #         time.sleep(cls.SLEEP_TIME_S)

    #     raise TimeoutError("The ODM client is not ready in the given timeout.")
    # ======

    async def build_auto_encryption_opts(
        self,
        document_models: list[type[Document]] | None = None,
    ) -> Self:
        """Build the CSFLE ``AutoEncryptionOpts``, if CSFLE is enabled in configuration.

        No-op when ``ODMConfig.csfle_enabled`` is False, or when injected already. Otherwise:
        unwraps the master key from Vault Transit, resolves-or-creates this service's single
        Data Encryption Key, and builds the client-side schema map from every document
        model's ``Settings.encrypted_fields``. Vault is only ever on this startup path.

        Args:
            document_models: The document models to resolve encrypted fields from. Defaults
                to ``self._application.ODM_DOCUMENT_MODELS`` when not provided.

        Returns:
            Self: The ODM factory.

        Raises:
            ODMPluginConfigError: If the ODM configuration is not build or provided.
            VaultUnwrapError: If the Vault login or transit/decrypt call fails.
            EncryptedFieldIndexCollisionError: If a declared encrypted field is also indexed.
        """
        if self._auto_encryption_opts is not None:
            return self

        if self._config is None:
            raise ODMPluginConfigError(
                "ODM configuration is not set. Provide the ODM configuration using "
                "build_odm_config method or through parameter."
            )

        if not self._config.csfle_enabled:
            return self

        resolved_document_models: list[type[Document]] = (
            document_models if document_models is not None else list(self._application.ODM_DOCUMENT_MODELS or [])
        )
        validate_no_index_collisions(resolved_document_models)

        # Guaranteed non-None by ODMConfig's csfle_enabled validator.
        assert self._config.csfle_vault_address is not None
        assert self._config.csfle_vault_auth_mount is not None
        assert self._config.csfle_vault_role is not None
        assert self._config.csfle_vault_transit_key is not None
        assert self._config.csfle_master_key_ciphertext is not None

        vault_client = VaultUnwrapClient(
            vault_address=self._config.csfle_vault_address,
            auth_mount=self._config.csfle_vault_auth_mount,
            role=self._config.csfle_vault_role,
            transit_key=self._config.csfle_vault_transit_key,
        )
        master_key: bytes = await vault_client.unwrap_master_key(ciphertext=self._config.csfle_master_key_ciphertext)
        kms_providers: dict[str, Any] = {"local": {"key": master_key}}

        provisioning_client: AsyncMongoClient[Any] = AsyncMongoClient(
            host=self._config.uri,
            connectTimeoutMS=self._config.connection_timeout_ms,
            serverSelectionTimeoutMS=self._config.connection_timeout_ms,
        )
        try:
            key_id = await resolve_or_create_data_key(
                client=provisioning_client,
                key_vault_database=self._config.database,
                key_vault_collection=self._config.csfle_key_vault_collection,
                kms_providers=kms_providers,
            )
        finally:
            await provisioning_client.close()

        schema_map: dict[str, Any] = build_schema_map(
            resolved_document_models,
            database_name=self._config.database,
            key_id=key_id,
        )
        schema_map.update(build_startup_probe_schema(database_name=self._config.database, key_id=key_id))
        key_vault_namespace: str = f"{self._config.database}.{self._config.csfle_key_vault_collection}"

        self._auto_encryption_opts = AutoEncryptionOpts(
            kms_providers=kms_providers,
            key_vault_namespace=key_vault_namespace,
            schema_map=schema_map,
        )
        return self

    def build_client(
        self,
    ) -> Self:
        """Build the ODM client.

        Returns:
            Self: The ODM factory.

        Raises:
            ODMPluginConfigError: If the ODM configuration is not build or provided.
        """
        if self._odm_client is not None:
            return self

        if self._config is None:
            raise ODMPluginConfigError(
                "ODM configuration is not set. Provide the ODM configuration using "
                "build_odm_config method or through parameter."
            )

        client_kwargs: dict[str, Any] = {
            "host": self._config.uri,
            "connect": True,
            "connectTimeoutMS": self._config.connection_timeout_ms,
            "serverSelectionTimeoutMS": self._config.connection_timeout_ms,
            "minPoolSize": self._config.min_pool_size,
            "maxPoolSize": self._config.max_pool_size,
            "server_api": ServerApi(version=ServerApiVersion.V1),
            "tz_aware": True,
        }
        if self._config.max_idle_time_ms is not None and self._config.max_idle_time_ms > 0:
            client_kwargs["maxIdleTimeMS"] = self._config.max_idle_time_ms
        if self._config.heartbeat_frequency_ms is not None and self._config.heartbeat_frequency_ms > 0:
            client_kwargs["heartbeatFrequencyMS"] = self._config.heartbeat_frequency_ms
        if self._auto_encryption_opts is not None:
            client_kwargs["auto_encryption_opts"] = self._auto_encryption_opts

        self._odm_client = AsyncMongoClient(**client_kwargs)

        # KEEP IT, Waiting for additional tests
        # self._wait_client_to_be_ready(client=self._odm_client, timeout_s=self._config.connection_timeout_s)

        return self

    def build_database(
        self,
    ) -> Self:
        """Build the ODM database.

        The ODM client and ODM configuration are recommended to be provided through call to the build_client and
        build_odm_config methods.

        Returns:
            Any: The ODM database.

        Raises:
            ODMPluginConfigError: If the ODM configuration is not build or provided.
        """
        if self._odm_database is not None:
            return self

        if self._config is None:
            raise ODMPluginConfigError(
                "ODM configuration is not set. Provide the ODM configuration using "
                "build_odm_config method or through parameter."
            )

        database_name: str = self._config.database

        if self._odm_client is None:
            raise ODMPluginConfigError(
                "ODM client is not set. Provide the ODM client using build_client method or through parameter."
            )

        self._odm_database = self._odm_client.get_database(
            name=database_name,
            codec_options=CodecOptions(  # pyright: ignore[reportUnknownArgumentType]
                tz_aware=True,
            ),
        )

        return self

    async def build_all(self, document_models: list[type[Document]] | None = None) -> Self:
        """Build all the resources for the ODM plugin.

        Args:
            document_models: The document models to resolve CSFLE encrypted fields from,
                when CSFLE is enabled. Defaults to ``self._application.ODM_DOCUMENT_MODELS``.

        Returns:
            Self: The ODM factory.

        Raises:
            ODMPluginConfigError: If the ODM configuration is not build or provided.
            VaultUnwrapError: If CSFLE is enabled and the Vault unwrap fails.
            EncryptedFieldIndexCollisionError: If a declared encrypted field is also indexed.
        """
        self.build_odm_config()
        await self.build_auto_encryption_opts(document_models=document_models)
        self.build_client()
        self.build_database()

        return self
