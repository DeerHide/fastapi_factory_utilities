"""Provides the configuration for the ODM plugin."""

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

# CSFLE fields required together when csfle_enabled is True. No shared-library path field:
# mongocryptd is resolved from PATH (installed via each service's Aptfile), not configured here.
_CSFLE_REQUIRED_FIELDS: tuple[str, ...] = (
    "csfle_vault_address",
    "csfle_vault_auth_mount",
    "csfle_vault_role",
    "csfle_vault_transit_key",
    "csfle_master_key_ciphertext",
)


class ODMConfig(BaseModel):
    """Provides the configuration model for the ODM plugin."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    uri: str

    database: str = "test"

    connection_timeout_ms: int = 4000

    min_pool_size: int = 0

    max_pool_size: int = 100

    max_idle_time_ms: int | None = None

    heartbeat_frequency_ms: int | None = None

    csfle_enabled: bool = False
    """Enable CSFLE (Client-Side Field Level Encryption) for document models that declare
    ``Settings.encrypted_fields``. Switchable per service so onboarding is independent."""

    csfle_vault_address: str | None = None
    """Vault's base address, e.g. ``https://vault.red.velmios.io``."""

    csfle_vault_auth_mount: str | None = None
    """The Kubernetes auth mount to log in against, e.g. ``kubernetes-green``."""

    csfle_vault_role: str | None = None
    """The Vault role bound to this service's ServiceAccount, e.g. ``payments-csfle-stg``."""

    csfle_vault_transit_key: str | None = None
    """The Transit key that wraps the master key, e.g. ``csfle-stg``."""

    csfle_master_key_ciphertext: str | None = None
    """The ``vault:v1:<key>:...`` Transit ciphertext of the local KMS master key. Not a
    secret by itself (its confidentiality rests entirely on the Transit key, which never
    leaves Vault) — see env var ``MONGO_CSFLE_MASTER_KEY_CIPHERTEXT``."""

    csfle_key_vault_collection: str = "__keyVault"
    """The collection, in this service's own database, holding its Data Encryption Key."""

    @model_validator(mode="after")
    def _validate_csfle_fields_when_enabled(self) -> Self:
        if not self.csfle_enabled:
            return self
        missing_fields: list[str] = [
            field_name for field_name in _CSFLE_REQUIRED_FIELDS if getattr(self, field_name) is None
        ]
        if missing_fields:
            joined_fields: str = ", ".join(missing_fields)
            raise ValueError(f"csfle_enabled requires the following fields to be set: {joined_fields}")
        return self
