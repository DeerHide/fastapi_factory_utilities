"""Unit tests for CSFLE key vault provisioning."""

from unittest.mock import AsyncMock, MagicMock, patch

from bson import Binary
from pymongo.errors import DuplicateKeyError

from fastapi_factory_utilities.core.plugins.odm_plugin.encryption.key_vault import (
    KEY_ALT_NAME,
    resolve_or_create_data_key,
)

KEY_VAULT_DATABASE = "payments"
KEY_VAULT_COLLECTION = "__keyVault"
KMS_PROVIDERS = {"local": {"key": b"m" * 96}}
EXISTING_KEY_ID = Binary(b"e" * 16, subtype=4)
NEW_KEY_ID = Binary(b"n" * 16, subtype=4)


def _mock_client(find_one_result: dict[str, object] | None) -> MagicMock:
    collection = MagicMock()
    collection.create_index = AsyncMock(return_value=None)
    collection.find_one = AsyncMock(return_value=find_one_result)

    database = MagicMock()
    database.__getitem__ = MagicMock(return_value=collection)

    client = MagicMock()
    client.__getitem__ = MagicMock(return_value=database)
    client.codec_options = MagicMock()
    return client


class TestResolveOrCreateDataKey:
    """Tests for ``resolve_or_create_data_key``."""

    async def test_ensures_the_unique_index_exists(self) -> None:
        """The unique partial index on ``keyAltNames`` is (re-)created on every call."""
        client = _mock_client(find_one_result={"_id": EXISTING_KEY_ID, "keyAltNames": [KEY_ALT_NAME]})

        await resolve_or_create_data_key(
            client=client,
            key_vault_database=KEY_VAULT_DATABASE,
            key_vault_collection=KEY_VAULT_COLLECTION,
            kms_providers=KMS_PROVIDERS,
        )

        collection = client[KEY_VAULT_DATABASE][KEY_VAULT_COLLECTION]
        collection.create_index.assert_awaited_once_with(
            "keyAltNames",
            unique=True,
            partialFilterExpression={"keyAltNames": {"$exists": True}},
        )

    async def test_reuses_existing_data_key_without_creating_one(self) -> None:
        """When a DEK with the service alias already exists, it is reused as-is."""
        client = _mock_client(find_one_result={"_id": EXISTING_KEY_ID, "keyAltNames": [KEY_ALT_NAME]})

        with patch(
            "fastapi_factory_utilities.core.plugins.odm_plugin.encryption.key_vault.AsyncClientEncryption"
        ) as mock_client_encryption_cls:
            key_id = await resolve_or_create_data_key(
                client=client,
                key_vault_database=KEY_VAULT_DATABASE,
                key_vault_collection=KEY_VAULT_COLLECTION,
                kms_providers=KMS_PROVIDERS,
            )

        assert key_id == EXISTING_KEY_ID
        mock_client_encryption_cls.assert_not_called()

    async def test_creates_data_key_when_none_exists(self) -> None:
        """When no DEK exists yet, one is created with the service's fixed key alias."""
        client = _mock_client(find_one_result=None)
        mock_client_encryption = MagicMock()
        mock_client_encryption.create_data_key = AsyncMock(return_value=NEW_KEY_ID)
        mock_client_encryption.close = AsyncMock(return_value=None)

        with patch(
            "fastapi_factory_utilities.core.plugins.odm_plugin.encryption.key_vault.AsyncClientEncryption",
            return_value=mock_client_encryption,
        ):
            key_id = await resolve_or_create_data_key(
                client=client,
                key_vault_database=KEY_VAULT_DATABASE,
                key_vault_collection=KEY_VAULT_COLLECTION,
                kms_providers=KMS_PROVIDERS,
            )

        assert key_id == NEW_KEY_ID
        mock_client_encryption.create_data_key.assert_awaited_once_with("local", key_alt_names=[KEY_ALT_NAME])
        mock_client_encryption.close.assert_awaited_once()

    async def test_resolves_to_winner_when_create_loses_the_race(self) -> None:
        """A duplicate-key error on create falls back to reading the concurrently-created DEK."""
        client = _mock_client(find_one_result=None)
        collection = client[KEY_VAULT_DATABASE][KEY_VAULT_COLLECTION]
        collection.find_one = AsyncMock(side_effect=[None, {"_id": EXISTING_KEY_ID, "keyAltNames": [KEY_ALT_NAME]}])

        mock_client_encryption = MagicMock()
        mock_client_encryption.create_data_key = AsyncMock(side_effect=DuplicateKeyError("duplicate key"))
        mock_client_encryption.close = AsyncMock(return_value=None)

        with patch(
            "fastapi_factory_utilities.core.plugins.odm_plugin.encryption.key_vault.AsyncClientEncryption",
            return_value=mock_client_encryption,
        ):
            key_id = await resolve_or_create_data_key(
                client=client,
                key_vault_database=KEY_VAULT_DATABASE,
                key_vault_collection=KEY_VAULT_COLLECTION,
                kms_providers=KMS_PROVIDERS,
            )

        assert key_id == EXISTING_KEY_ID
        mock_client_encryption.close.assert_awaited_once()
