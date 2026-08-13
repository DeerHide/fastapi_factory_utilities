"""Vault Transit unwrap client for the CSFLE local master key."""

import base64
from http import HTTPStatus
from pathlib import Path
from typing import Any, Final

import aiohttp
import jwt
from structlog.stdlib import BoundLogger, get_logger

from ..exceptions import VaultUnwrapError

_logger: BoundLogger = get_logger()

DEFAULT_SERVICE_ACCOUNT_TOKEN_PATH: Final[str] = "/var/run/secrets/kubernetes.io/serviceaccount/token"
_REQUEST_TIMEOUT_S: Final[int] = 10


def _namespace_from_projected_token(token: str) -> str | None:
    """Best-effort extraction of the pod's own namespace from its projected token, for logging only.

    Vault is the authority on the token's namespace: it verifies the token server-side via
    TokenReview during `auth/<mount>/login`. This value is never sent to Vault and never used
    to make an authorization decision; it only makes unwrap failures easier to diagnose.

    Args:
        token: The pod's projected ServiceAccount JWT.

    Returns:
        str | None: The namespace claim, or None if it cannot be determined.
    """
    try:
        claims: dict[str, Any] = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError:
        return None

    namespace = claims.get("kubernetes.io", {}).get("namespace")
    if namespace:
        return str(namespace)

    # Fallback for the legacy token shape: "system:serviceaccount:<namespace>:<name>".
    subject_parts = str(claims.get("sub", "")).split(":")
    legacy_subject_part_count = 4
    is_legacy_service_account_subject: bool = (
        len(subject_parts) == legacy_subject_part_count
        and subject_parts[0] == "system"
        and subject_parts[1] == "serviceaccount"
    )
    if is_legacy_service_account_subject:
        return subject_parts[2]
    return None


class VaultUnwrapClient:
    """Recovers the CSFLE local master key from Vault Transit.

    Exactly two HTTP calls, both against the pod's own projected ServiceAccount identity:

    1. `POST /v1/auth/<mount>/login` with the projected token, to obtain a short-lived Vault token.
    2. `POST /v1/transit/decrypt/<transit_key>` with the wrapped master key ciphertext.

    The plaintext master key is returned to the caller and is never written to disk. Vault is
    only ever on the pod *startup* path: once unwrapped, the key lives in process memory for the
    lifetime of the pod.
    """

    def __init__(
        self,
        vault_address: str,
        auth_mount: str,
        role: str,
        transit_key: str,
        service_account_token_path: str = DEFAULT_SERVICE_ACCOUNT_TOKEN_PATH,
    ) -> None:
        """Initialize the Vault unwrap client.

        Args:
            vault_address: Vault's base address, e.g. `https://vault.red.velmios.io`.
            auth_mount: The Kubernetes auth mount to log in against, e.g. `kubernetes-green`.
            role: The Vault role bound to this service's ServiceAccount.
            transit_key: The Transit key used to decrypt the master key ciphertext.
            service_account_token_path: Path to the pod's projected ServiceAccount token.
        """
        self._vault_address: str = vault_address.rstrip("/")
        self._auth_mount: str = auth_mount
        self._role: str = role
        self._transit_key: str = transit_key
        self._service_account_token_path: str = service_account_token_path

    def _read_projected_token(self) -> str:
        try:
            return Path(self._service_account_token_path).read_text(encoding="utf-8").strip()
        except OSError as exception:
            raise VaultUnwrapError(
                f"Unable to read the projected ServiceAccount token at {self._service_account_token_path}."
            ) from exception

    async def _login(self, session: aiohttp.ClientSession, jwt_token: str) -> str:
        url = f"{self._vault_address}/v1/auth/{self._auth_mount}/login"
        try:
            async with session.post(
                url,
                json={"role": self._role, "jwt": jwt_token},
                timeout=aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT_S),
            ) as response:
                if response.status != HTTPStatus.OK:
                    body: str = await response.text()
                    raise VaultUnwrapError(
                        f"Vault login on auth/{self._auth_mount} failed: HTTP {response.status} {body}"
                    )
                payload: dict[str, Any] = await response.json()
        except aiohttp.ClientError as exception:
            raise VaultUnwrapError(f"Vault login on auth/{self._auth_mount} failed.") from exception

        try:
            return str(payload["auth"]["client_token"])
        except (KeyError, TypeError) as exception:
            raise VaultUnwrapError("Vault login response is missing auth.client_token.") from exception

    async def _decrypt(self, session: aiohttp.ClientSession, vault_token: str, ciphertext: str) -> bytes:
        url = f"{self._vault_address}/v1/transit/decrypt/{self._transit_key}"
        try:
            async with session.post(
                url,
                json={"ciphertext": ciphertext},
                headers={"X-Vault-Token": vault_token},
                timeout=aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT_S),
            ) as response:
                if response.status != HTTPStatus.OK:
                    body: str = await response.text()
                    raise VaultUnwrapError(
                        f"Vault transit/decrypt on {self._transit_key} failed: HTTP {response.status} {body}"
                    )
                payload: dict[str, Any] = await response.json()
        except aiohttp.ClientError as exception:
            raise VaultUnwrapError(f"Vault transit/decrypt on {self._transit_key} failed.") from exception

        try:
            plaintext_b64: str = str(payload["data"]["plaintext"])
        except (KeyError, TypeError) as exception:
            raise VaultUnwrapError("Vault transit/decrypt response is missing data.plaintext.") from exception

        try:
            return base64.b64decode(plaintext_b64, validate=True)
        except (ValueError, TypeError) as exception:
            raise VaultUnwrapError("Vault transit/decrypt returned plaintext that is not valid base64.") from exception

    async def unwrap_master_key(self, ciphertext: str) -> bytes:
        """Recover the plaintext CSFLE master key from its Transit ciphertext.

        Args:
            ciphertext: The `vault:v1:<key>:...` ciphertext produced by `transit/encrypt`.

        Returns:
            bytes: The plaintext master key.

        Raises:
            VaultUnwrapError: If the projected token cannot be read, or either Vault call fails.
        """
        jwt_token: str = self._read_projected_token()
        namespace: str | None = _namespace_from_projected_token(jwt_token)
        log: BoundLogger = _logger.bind(
            vault_address=self._vault_address,
            auth_mount=self._auth_mount,
            role=self._role,
            transit_key=self._transit_key,
            namespace=namespace,
        )
        try:
            async with aiohttp.ClientSession() as session:
                vault_token: str = await self._login(session=session, jwt_token=jwt_token)
                log.debug("Vault login succeeded for the CSFLE master key unwrap.")
                master_key: bytes = await self._decrypt(session=session, vault_token=vault_token, ciphertext=ciphertext)
        except VaultUnwrapError:
            log.exception("Failed to unwrap the CSFLE master key from Vault.")
            raise

        log.debug("CSFLE master key unwrapped from Vault.", master_key_length=len(master_key))
        return master_key
