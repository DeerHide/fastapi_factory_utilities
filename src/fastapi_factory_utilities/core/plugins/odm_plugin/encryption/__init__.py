"""CSFLE (Client-Side Field Level Encryption) support for the ODM plugin."""

from .key_vault import KEY_ALT_NAME, resolve_or_create_data_key
from .schema import (
    ENCRYPT_ALGORITHM,
    STARTUP_PROBE_COLLECTION,
    STARTUP_PROBE_FIELD,
    build_schema_map,
    build_startup_probe_schema,
    validate_no_index_collisions,
)
from .vault import VaultUnwrapClient

__all__ = [
    "ENCRYPT_ALGORITHM",
    "KEY_ALT_NAME",
    "STARTUP_PROBE_COLLECTION",
    "STARTUP_PROBE_FIELD",
    "VaultUnwrapClient",
    "build_schema_map",
    "build_startup_probe_schema",
    "resolve_or_create_data_key",
    "validate_no_index_collisions",
]
