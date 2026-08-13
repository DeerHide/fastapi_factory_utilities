"""Key vault provisioning for the CSFLE per-service Data Encryption Key."""

from typing import Any, Final

from bson import Binary
from pymongo.asynchronous.encryption import AsyncClientEncryption
from pymongo.asynchronous.mongo_client import AsyncMongoClient
from pymongo.errors import DuplicateKeyError
from structlog.stdlib import BoundLogger, get_logger

_logger: BoundLogger = get_logger()

# One DEK per service (design decision 2): every declared field, across every document
# model, is wrapped by this single alias, so restarts and replicas resolve the same key
# rather than minting a new one on every boot.
KEY_ALT_NAME: Final[str] = "primary"


async def resolve_or_create_data_key(
    client: AsyncMongoClient[Any],
    key_vault_database: str,
    key_vault_collection: str,
    kms_providers: dict[str, Any],
) -> Binary:
    """Ensure the key vault collection, its unique index, and the service DEK all exist.

    Idempotent and safe to call on every pod startup, including concurrently across
    replicas: the unique partial index on ``keyAltNames`` guarantees at most one
    ``create_data_key`` call ever wins, and any loser resolves the winner's key instead of
    erroring.

    Args:
        client: A plain (non-encrypting) MongoDB client.
        key_vault_database: The database holding the key vault collection.
        key_vault_collection: The key vault collection name.
        kms_providers: The libmongocrypt ``local`` KMS provider, keyed by the unwrapped
            master key.

    Returns:
        Binary: The service's Data Encryption Key id.
    """
    key_vault_namespace: str = f"{key_vault_database}.{key_vault_collection}"
    collection = client[key_vault_database][key_vault_collection]

    await collection.create_index(
        "keyAltNames",
        unique=True,
        partialFilterExpression={"keyAltNames": {"$exists": True}},
    )

    existing_key: dict[str, Any] | None = await collection.find_one({"keyAltNames": KEY_ALT_NAME})
    if existing_key is not None:
        return existing_key["_id"]

    client_encryption: AsyncClientEncryption[Any] = AsyncClientEncryption(
        kms_providers=kms_providers,
        key_vault_namespace=key_vault_namespace,
        key_vault_client=client,
        codec_options=client.codec_options,
    )
    try:
        try:
            key_id: Binary = await client_encryption.create_data_key("local", key_alt_names=[KEY_ALT_NAME])
        except DuplicateKeyError:
            # Lost the create race to another replica booting concurrently.
            existing_key = await collection.find_one({"keyAltNames": KEY_ALT_NAME})
            if existing_key is None:
                raise
            key_id = existing_key["_id"]
        else:
            _logger.info("Created the CSFLE Data Encryption Key.", key_vault_namespace=key_vault_namespace)
    finally:
        await client_encryption.close()

    return key_id
