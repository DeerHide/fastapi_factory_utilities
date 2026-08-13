"""Schema-map building and index-collision validation for CSFLE encrypted fields.

Services declare encrypted field paths as data, on the document class, rather than as
encrypt/decrypt call sites in application code:

```python
class ProcessorCredsDocument(BaseDocument):
    class Settings(BaseDocument.Settings):
        encrypted_fields = ["creds.client_secret"]
```

This module resolves those declarations into a client-side ``schemaMap`` for
``AutoEncryptionOpts``, keyed ``<database>.<collection>`` so the same declaration works
across environments where only the database name differs.
"""

from collections.abc import Iterable
from typing import Any, Final

from beanie import Document  # pyright: ignore[reportUnknownVariableType]
from beanie.odm.utils.typing import get_index_attributes  # pyright: ignore[reportMissingTypeStubs]
from bson import Binary

from ..exceptions import EncryptedFieldIndexCollisionError

# Every declared field uses randomized encryption: none of them is ever queried by value,
# and randomized encryption (unlike deterministic) leaks nothing about equal plaintexts.
ENCRYPT_ALGORITHM: Final[str] = "AEAD_AES_256_CBC_HMAC_SHA_512-Random"

# Dedicated collection for ODMPlugin's startup smoke test (see design.md decision 3):
# mongocryptd spawns lazily on the first automatically-encrypted operation, unlike
# crypt_shared, which loads eagerly at client construction. A throwaway encrypted
# insert+delete against this collection, right after init_beanie, forces that spawn at
# startup instead of leaving it to the first real request.
STARTUP_PROBE_COLLECTION: Final[str] = "__csfle_startup_probe"
STARTUP_PROBE_FIELD: Final[str] = "probe"


def _resolve_collection_name(document_class: type[Document]) -> str:
    """Resolve the MongoDB collection name the same way Beanie's ``init_beanie`` does.

    Args:
        document_class: The Beanie document class.

    Returns:
        str: ``Settings.name`` if set, otherwise the class name.
    """
    settings_class: Any = getattr(document_class, "Settings", None)
    name: str | None = getattr(settings_class, "name", None)
    return name or document_class.__name__


def _encrypted_fields(document_class: type[Document]) -> list[str]:
    settings_class: Any = getattr(document_class, "Settings", None)
    return list(getattr(settings_class, "encrypted_fields", None) or [])


def _indexed_top_level_fields(document_class: type[Document]) -> set[str]:
    """Collect every top-level field name that is indexed, by any mechanism Beanie supports.

    Covers both per-field ``Indexed()``/``Annotated[..., Indexed()]`` declarations and
    compound indexes declared in ``Settings.indexes``.

    Args:
        document_class: The Beanie document class.

    Returns:
        set[str]: The indexed top-level field names.
    """
    indexed: set[str] = set()

    for field_name, field_info in document_class.model_fields.items():
        # ponytail: reuses beanie's own internal helper rather than re-implementing detection
        # of both `Indexed(str)` and `Annotated[str, Indexed()]` field shapes.
        if get_index_attributes(field_info) is not None:
            indexed.add(field_name)

    settings_class: Any = getattr(document_class, "Settings", None)
    for index_model in getattr(settings_class, "indexes", None) or []:
        key: Any = getattr(index_model, "document", {}).get("key", {})
        indexed.update(key)

    return indexed


def validate_no_index_collisions(document_models: Iterable[type[Document]]) -> None:
    """Reject any declared encrypted field that is also indexed.

    A randomly-encrypted field can never be filtered on by value, so an index on it can
    only ever be dead weight at best, and a startup-time signal that a field was declared
    encrypted by mistake at worst.

    Args:
        document_models: The document classes to validate.

    Raises:
        EncryptedFieldIndexCollisionError: Naming the offending document and field.
    """
    for document_class in document_models:
        encrypted_fields: list[str] = _encrypted_fields(document_class)
        if not encrypted_fields:
            continue
        indexed_fields: set[str] = _indexed_top_level_fields(document_class)
        for field_path in encrypted_fields:
            top_level_field: str = field_path.split(".", 1)[0]
            if top_level_field in indexed_fields:
                raise EncryptedFieldIndexCollisionError(
                    f"{document_class.__name__}.{field_path} is declared encrypted but "
                    f"'{top_level_field}' is also indexed. Randomly-encrypted fields cannot "
                    "be queried by value; remove the index or the encrypted declaration."
                )


def _set_nested_encrypt(properties: dict[str, Any], path_parts: list[str]) -> None:
    field_name, *rest = path_parts
    if not rest:
        properties[field_name] = {
            "encrypt": {
                "bsonType": "string",
                "algorithm": ENCRYPT_ALGORITHM,
            }
        }
        return

    node: dict[str, Any] = properties.setdefault(
        field_name,
        {"bsonType": "object", "properties": {}},
    )
    _set_nested_encrypt(node["properties"], rest)


def build_schema_map(
    document_models: Iterable[type[Document]],
    database_name: str,
    key_id: Binary,
) -> dict[str, Any]:
    """Build the client-side ``schemaMap`` for ``AutoEncryptionOpts``.

    All declared fields, across all document classes, share the single per-service DEK
    (`key_id`) — see design decision 2: cross-service isolation comes from Mongo user
    scoping, not from per-service master keys.

    Args:
        document_models: The document classes to resolve. Classes with no
            ``Settings.encrypted_fields`` are skipped.
        database_name: The service's own database name.
        key_id: The service's Data Encryption Key id.

    Returns:
        dict[str, Any]: A schema map keyed ``<database_name>.<collection>``, empty if no
            document model declares any encrypted field.
    """
    schema_map: dict[str, Any] = {}

    for document_class in document_models:
        encrypted_fields: list[str] = _encrypted_fields(document_class)
        if not encrypted_fields:
            continue

        collection_name: str = _resolve_collection_name(document_class)
        properties: dict[str, Any] = {}
        for field_path in encrypted_fields:
            _set_nested_encrypt(properties, field_path.split("."))

        schema_map[f"{database_name}.{collection_name}"] = {
            "bsonType": "object",
            "encryptMetadata": {"keyId": [key_id]},
            "properties": properties,
        }

    return schema_map


def build_startup_probe_schema(database_name: str, key_id: Binary) -> dict[str, Any]:
    """Build the schema entry for the throwaway startup smoke-test collection.

    Args:
        database_name: The service's own database name.
        key_id: The service's Data Encryption Key id.

    Returns:
        dict[str, Any]: A single-entry schema map for ``STARTUP_PROBE_COLLECTION``.
    """
    return {
        f"{database_name}.{STARTUP_PROBE_COLLECTION}": {
            "bsonType": "object",
            "encryptMetadata": {"keyId": [key_id]},
            "properties": {
                STARTUP_PROBE_FIELD: {
                    "encrypt": {
                        "bsonType": "string",
                        "algorithm": ENCRYPT_ALGORITHM,
                    }
                }
            },
        }
    }
