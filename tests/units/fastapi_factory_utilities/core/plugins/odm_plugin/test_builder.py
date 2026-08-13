"""Unit tests for ODM builder."""

from typing import Annotated, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import Indexed  # pyright: ignore[reportUnknownVariableType]
from pymongo.encryption_options import AutoEncryptionOpts
from pymongo.server_api import ServerApiVersion

from fastapi_factory_utilities.core.plugins.odm_plugin.builder import ODMBuilder
from fastapi_factory_utilities.core.plugins.odm_plugin.configs import ODMConfig
from fastapi_factory_utilities.core.plugins.odm_plugin.documents import BaseDocument
from fastapi_factory_utilities.core.plugins.odm_plugin.exceptions import (
    EncryptedFieldIndexCollisionError,
)

DEFAULT_CONNECTION_TIMEOUT_MS = 4000
DEFAULT_MAX_POOL_SIZE = 100
CUSTOM_MIN_POOL_SIZE = 5
CUSTOM_MAX_POOL_SIZE = 50
CUSTOM_MAX_IDLE_TIME_MS = 60000
CUSTOM_HEARTBEAT_FREQUENCY_MS = 5000


class TestODMBuilderBuildClient:
    """Tests for ``ODMBuilder.build_client``."""

    @patch("fastapi_factory_utilities.core.plugins.odm_plugin.builder.AsyncMongoClient")
    def test_build_client_passes_pool_settings(self, mock_async_mongo_client: MagicMock) -> None:
        """Pool tuning from config is forwarded to ``AsyncMongoClient``."""
        odm_config: ODMConfig = ODMConfig(
            uri="mongodb://localhost:27017",
            min_pool_size=CUSTOM_MIN_POOL_SIZE,
            max_pool_size=CUSTOM_MAX_POOL_SIZE,
            max_idle_time_ms=CUSTOM_MAX_IDLE_TIME_MS,
            heartbeat_frequency_ms=CUSTOM_HEARTBEAT_FREQUENCY_MS,
        )
        builder: ODMBuilder = ODMBuilder(application=MagicMock(), odm_config=odm_config)

        builder.build_client()

        mock_async_mongo_client.assert_called_once()
        client_kwargs: dict[str, Any] = mock_async_mongo_client.call_args.kwargs
        assert client_kwargs["host"] == "mongodb://localhost:27017"
        assert client_kwargs["connect"] is True
        assert client_kwargs["connectTimeoutMS"] == DEFAULT_CONNECTION_TIMEOUT_MS
        assert client_kwargs["serverSelectionTimeoutMS"] == DEFAULT_CONNECTION_TIMEOUT_MS
        assert client_kwargs["minPoolSize"] == CUSTOM_MIN_POOL_SIZE
        assert client_kwargs["maxPoolSize"] == CUSTOM_MAX_POOL_SIZE
        assert client_kwargs["maxIdleTimeMS"] == CUSTOM_MAX_IDLE_TIME_MS
        assert client_kwargs["heartbeatFrequencyMS"] == CUSTOM_HEARTBEAT_FREQUENCY_MS
        assert client_kwargs["server_api"].version == ServerApiVersion.V1
        assert client_kwargs["tz_aware"] is True

    @patch("fastapi_factory_utilities.core.plugins.odm_plugin.builder.AsyncMongoClient")
    def test_build_client_omits_optional_pool_settings_when_unset(
        self,
        mock_async_mongo_client: MagicMock,
    ) -> None:
        """Optional pool settings are omitted when not configured."""
        odm_config: ODMConfig = ODMConfig(uri="mongodb://localhost:27017")
        builder: ODMBuilder = ODMBuilder(application=MagicMock(), odm_config=odm_config)

        builder.build_client()

        client_kwargs: dict[str, Any] = mock_async_mongo_client.call_args.kwargs
        assert "maxIdleTimeMS" not in client_kwargs
        assert "heartbeatFrequencyMS" not in client_kwargs
        assert client_kwargs["minPoolSize"] == 0
        assert client_kwargs["maxPoolSize"] == DEFAULT_MAX_POOL_SIZE

    @patch("fastapi_factory_utilities.core.plugins.odm_plugin.builder.AsyncMongoClient")
    def test_build_client_omits_max_idle_time_ms_when_zero(
        self,
        mock_async_mongo_client: MagicMock,
    ) -> None:
        """Zero max idle time means no limit and must not be forwarded to PyMongo."""
        odm_config: ODMConfig = ODMConfig(
            uri="mongodb://localhost:27017",
            max_idle_time_ms=0,
            heartbeat_frequency_ms=0,
        )
        builder: ODMBuilder = ODMBuilder(application=MagicMock(), odm_config=odm_config)

        builder.build_client()

        client_kwargs: dict[str, Any] = mock_async_mongo_client.call_args.kwargs
        assert "maxIdleTimeMS" not in client_kwargs
        assert "heartbeatFrequencyMS" not in client_kwargs

    @patch("fastapi_factory_utilities.core.plugins.odm_plugin.builder.AsyncMongoClient")
    def test_build_client_omits_auto_encryption_opts_when_csfle_disabled(
        self,
        mock_async_mongo_client: MagicMock,
    ) -> None:
        """No ``auto_encryption_opts`` kwarg is forwarded when CSFLE was never built."""
        odm_config: ODMConfig = ODMConfig(uri="mongodb://localhost:27017")
        builder: ODMBuilder = ODMBuilder(application=MagicMock(), odm_config=odm_config)

        builder.build_client()

        client_kwargs: dict[str, Any] = mock_async_mongo_client.call_args.kwargs
        assert "auto_encryption_opts" not in client_kwargs

    @patch("fastapi_factory_utilities.core.plugins.odm_plugin.builder.AsyncMongoClient")
    def test_build_client_forwards_injected_auto_encryption_opts(
        self,
        mock_async_mongo_client: MagicMock,
    ) -> None:
        """A pre-built ``AutoEncryptionOpts`` (from injection or a prior build step) is forwarded as-is.

        No ``crypt_shared_lib_path``/``crypt_shared_lib_required`` are set anywhere in this
        library: ``mongocryptd`` is resolved from ``PATH`` with PyMongo's default spawn behavior.
        """
        odm_config: ODMConfig = ODMConfig(uri="mongodb://localhost:27017")
        auto_encryption_opts: AutoEncryptionOpts = AutoEncryptionOpts(
            kms_providers={"local": {"key": b"k" * 96}},
            key_vault_namespace="test.__keyVault",
        )
        builder: ODMBuilder = ODMBuilder(
            application=MagicMock(), odm_config=odm_config, auto_encryption_opts=auto_encryption_opts
        )

        builder.build_client()

        client_kwargs: dict[str, Any] = mock_async_mongo_client.call_args.kwargs
        assert client_kwargs["auto_encryption_opts"] is auto_encryption_opts


class _EncryptedCredsDocument(BaseDocument):
    """Document fixture with a single declared encrypted field, no index collision."""

    processor_vault_token: str

    class Settings(BaseDocument.Settings):
        """Settings for ``_EncryptedCredsDocument``."""

        encrypted_fields = ["processor_vault_token"]  # noqa: RUF012


class _IndexedEncryptedDocument(BaseDocument):
    """Document fixture whose declared encrypted field is also indexed (invalid)."""

    access_token: Annotated[str, Indexed()]

    class Settings(BaseDocument.Settings):
        """Settings for ``_IndexedEncryptedDocument``."""

        encrypted_fields = ["access_token"]  # noqa: RUF012


class TestODMBuilderBuildAutoEncryptionOpts:
    """Tests for ``ODMBuilder.build_auto_encryption_opts``."""

    async def test_noop_when_csfle_disabled(self) -> None:
        """Nothing is built, and no Vault call is made, when CSFLE is disabled."""
        odm_config: ODMConfig = ODMConfig(uri="mongodb://localhost:27017")
        builder: ODMBuilder = ODMBuilder(application=MagicMock(), odm_config=odm_config)

        await builder.build_auto_encryption_opts()

        assert builder.auto_encryption_opts is None

    async def test_returns_injected_opts_without_rebuilding(self) -> None:
        """An already-injected ``AutoEncryptionOpts`` short-circuits the whole build."""
        odm_config: ODMConfig = ODMConfig(uri="mongodb://localhost:27017", csfle_enabled=False)
        injected = AutoEncryptionOpts(kms_providers={"local": {"key": b"k" * 96}}, key_vault_namespace="test.kv")
        builder: ODMBuilder = ODMBuilder(application=MagicMock(), odm_config=odm_config, auto_encryption_opts=injected)

        await builder.build_auto_encryption_opts()

        assert builder.auto_encryption_opts is injected

    @patch("fastapi_factory_utilities.core.plugins.odm_plugin.builder.AsyncMongoClient")
    @patch("fastapi_factory_utilities.core.plugins.odm_plugin.builder.resolve_or_create_data_key")
    @patch("fastapi_factory_utilities.core.plugins.odm_plugin.builder.VaultUnwrapClient")
    async def test_builds_opts_from_vault_and_document_models_when_enabled(
        self,
        mock_vault_client_cls: MagicMock,
        mock_resolve_or_create_data_key: AsyncMock,
        mock_async_mongo_client: MagicMock,
    ) -> None:
        """CSFLE-enabled config unwraps the key, resolves the DEK, and builds a schema map."""
        mock_vault_client_instance = MagicMock()
        mock_vault_client_instance.unwrap_master_key = AsyncMock(return_value=b"m" * 96)
        mock_vault_client_cls.return_value = mock_vault_client_instance
        mock_resolve_or_create_data_key.return_value = "fake-key-id"
        mock_async_mongo_client.return_value.close = AsyncMock(return_value=None)

        odm_config: ODMConfig = ODMConfig(
            uri="mongodb://localhost:27017",
            database="payments",
            csfle_enabled=True,
            csfle_vault_address="https://vault.red.velmios.io",
            csfle_vault_auth_mount="kubernetes-green",
            csfle_vault_role="payments-csfle-stg",
            csfle_vault_transit_key="csfle-stg",
            csfle_master_key_ciphertext="vault:v1:csfle-stg:AAAA....",
        )
        builder: ODMBuilder = ODMBuilder(application=MagicMock(), odm_config=odm_config)

        await builder.build_auto_encryption_opts(document_models=[_EncryptedCredsDocument])

        mock_vault_client_instance.unwrap_master_key.assert_awaited_once_with(ciphertext="vault:v1:csfle-stg:AAAA....")
        mock_resolve_or_create_data_key.assert_awaited_once()
        assert builder.auto_encryption_opts is not None

    async def test_rejects_encrypted_field_that_collides_with_an_index(self) -> None:
        """Index-collision validation runs before any Vault call is attempted."""
        odm_config: ODMConfig = ODMConfig(
            uri="mongodb://localhost:27017",
            csfle_enabled=True,
            csfle_vault_address="https://vault.red.velmios.io",
            csfle_vault_auth_mount="kubernetes-green",
            csfle_vault_role="payments-csfle-stg",
            csfle_vault_transit_key="csfle-stg",
            csfle_master_key_ciphertext="vault:v1:csfle-stg:AAAA....",
        )
        builder: ODMBuilder = ODMBuilder(application=MagicMock(), odm_config=odm_config)

        with pytest.raises(EncryptedFieldIndexCollisionError, match="access_token"):
            await builder.build_auto_encryption_opts(document_models=[_IndexedEncryptedDocument])
