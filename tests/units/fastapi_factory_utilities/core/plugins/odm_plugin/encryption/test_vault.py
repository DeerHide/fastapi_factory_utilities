"""Unit tests for the CSFLE Vault unwrap client."""

import base64
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest

from fastapi_factory_utilities.core.plugins.aiohttp.mockers import (
    build_mocked_aiohttp_response,
)
from fastapi_factory_utilities.core.plugins.odm_plugin.encryption.vault import (
    VaultUnwrapClient,
    _namespace_from_projected_token,
)
from fastapi_factory_utilities.core.plugins.odm_plugin.exceptions import VaultUnwrapError

VAULT_ADDRESS = "https://vault.red.velmios.io"
AUTH_MOUNT = "kubernetes-green"
ROLE = "payments-csfle-stg"
TRANSIT_KEY = "csfle-stg"
CIPHERTEXT = "vault:v1:csfle-stg:AAAA...."
MASTER_KEY = b"m" * 96
PROJECTED_TOKEN = "projected-service-account-token"


def _build_client(tmp_token_path: str) -> VaultUnwrapClient:
    return VaultUnwrapClient(
        vault_address=VAULT_ADDRESS,
        auth_mount=AUTH_MOUNT,
        role=ROLE,
        transit_key=TRANSIT_KEY,
        service_account_token_path=tmp_token_path,
    )


def _write_token(tmp_path, token: str = PROJECTED_TOKEN) -> str:
    token_path = tmp_path / "token"
    token_path.write_text(token)
    return str(token_path)


def _mock_session(responses: list[MagicMock]) -> MagicMock:
    """Build a mocked ``aiohttp.ClientSession`` whose ``post`` yields each response in order."""
    session = MagicMock()
    session.post = MagicMock(side_effect=responses)
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    return session_cm


class TestNamespaceFromProjectedToken:
    """Tests for ``_namespace_from_projected_token``."""

    def test_extracts_namespace_from_kubernetes_io_claim(self) -> None:
        """The namespace is read from the ``kubernetes.io.namespace`` claim when present."""
        token = jwt.encode({"kubernetes.io": {"namespace": "velmios-services-stg"}}, key="secret")

        assert _namespace_from_projected_token(token) == "velmios-services-stg"

    def test_falls_back_to_subject_claim(self) -> None:
        """The namespace is parsed from a legacy ``sub`` claim when the newer claim is absent."""
        token = jwt.encode({"sub": "system:serviceaccount:velmios-services-stg:payments-serviceaccount"}, key="secret")

        assert _namespace_from_projected_token(token) == "velmios-services-stg"

    def test_returns_none_for_undecodable_token(self) -> None:
        """A malformed token yields ``None`` rather than raising."""
        assert _namespace_from_projected_token("not-a-jwt") is None

    def test_returns_none_when_no_namespace_claim_present(self) -> None:
        """A token without any recognizable namespace claim yields ``None``."""
        token = jwt.encode({"sub": "someone-else"}, key="secret")

        assert _namespace_from_projected_token(token) is None


class TestVaultUnwrapClientUnwrapMasterKey:
    """Tests for ``VaultUnwrapClient.unwrap_master_key``."""

    async def test_unwraps_master_key_on_success(self, tmp_path) -> None:
        """A successful login and decrypt round trip returns the plaintext master key."""
        token_path = _write_token(tmp_path)
        client = _build_client(token_path)
        login_response = build_mocked_aiohttp_response(
            status=HTTPStatus.OK, json={"auth": {"client_token": "vault-token-abc"}}
        )
        decrypt_response = build_mocked_aiohttp_response(
            status=HTTPStatus.OK,
            json={"data": {"plaintext": base64.b64encode(MASTER_KEY).decode()}},
        )
        session_cm = _mock_session([login_response, decrypt_response])

        with patch(
            "fastapi_factory_utilities.core.plugins.odm_plugin.encryption.vault.aiohttp.ClientSession",
            return_value=session_cm,
        ):
            result = await client.unwrap_master_key(ciphertext=CIPHERTEXT)

        assert result == MASTER_KEY
        login_call = session_cm.__aenter__.return_value.post.call_args_list[0]
        assert login_call.args[0] == f"{VAULT_ADDRESS}/v1/auth/{AUTH_MOUNT}/login"
        assert login_call.kwargs["json"] == {"role": ROLE, "jwt": PROJECTED_TOKEN}
        decrypt_call = session_cm.__aenter__.return_value.post.call_args_list[1]
        assert decrypt_call.args[0] == f"{VAULT_ADDRESS}/v1/transit/decrypt/{TRANSIT_KEY}"
        assert decrypt_call.kwargs["headers"] == {"X-Vault-Token": "vault-token-abc"}

    async def test_raises_when_token_file_is_missing(self, tmp_path) -> None:
        """A missing projected ServiceAccount token file fails closed."""
        client = _build_client(str(tmp_path / "does-not-exist"))

        with pytest.raises(VaultUnwrapError, match="projected ServiceAccount token"):
            await client.unwrap_master_key(ciphertext=CIPHERTEXT)

    async def test_raises_on_login_http_error(self, tmp_path) -> None:
        """A non-200 login response fails closed with the response body in the error."""
        token_path = _write_token(tmp_path)
        client = _build_client(token_path)
        login_response = build_mocked_aiohttp_response(status=HTTPStatus.FORBIDDEN, text="permission denied")
        session_cm = _mock_session([login_response])

        with (
            patch(
                "fastapi_factory_utilities.core.plugins.odm_plugin.encryption.vault.aiohttp.ClientSession",
                return_value=session_cm,
            ),
            pytest.raises(VaultUnwrapError, match="Vault login"),
        ):
            await client.unwrap_master_key(ciphertext=CIPHERTEXT)

    async def test_raises_on_login_response_missing_client_token(self, tmp_path) -> None:
        """A login response without ``auth.client_token`` fails closed."""
        token_path = _write_token(tmp_path)
        client = _build_client(token_path)
        login_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"auth": {}})
        session_cm = _mock_session([login_response])

        with (
            patch(
                "fastapi_factory_utilities.core.plugins.odm_plugin.encryption.vault.aiohttp.ClientSession",
                return_value=session_cm,
            ),
            pytest.raises(VaultUnwrapError, match="client_token"),
        ):
            await client.unwrap_master_key(ciphertext=CIPHERTEXT)

    async def test_raises_on_decrypt_http_error(self, tmp_path) -> None:
        """A non-200 decrypt response fails closed, e.g. when the policy denies the operation."""
        token_path = _write_token(tmp_path)
        client = _build_client(token_path)
        login_response = build_mocked_aiohttp_response(
            status=HTTPStatus.OK, json={"auth": {"client_token": "vault-token-abc"}}
        )
        decrypt_response = build_mocked_aiohttp_response(status=HTTPStatus.FORBIDDEN, text="permission denied")
        session_cm = _mock_session([login_response, decrypt_response])

        with (
            patch(
                "fastapi_factory_utilities.core.plugins.odm_plugin.encryption.vault.aiohttp.ClientSession",
                return_value=session_cm,
            ),
            pytest.raises(VaultUnwrapError, match="transit/decrypt"),
        ):
            await client.unwrap_master_key(ciphertext=CIPHERTEXT)

    async def test_raises_on_decrypt_response_missing_plaintext(self, tmp_path) -> None:
        """A decrypt response without ``data.plaintext`` fails closed."""
        token_path = _write_token(tmp_path)
        client = _build_client(token_path)
        login_response = build_mocked_aiohttp_response(
            status=HTTPStatus.OK, json={"auth": {"client_token": "vault-token-abc"}}
        )
        decrypt_response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={"data": {}})
        session_cm = _mock_session([login_response, decrypt_response])

        with (
            patch(
                "fastapi_factory_utilities.core.plugins.odm_plugin.encryption.vault.aiohttp.ClientSession",
                return_value=session_cm,
            ),
            pytest.raises(VaultUnwrapError, match="plaintext"),
        ):
            await client.unwrap_master_key(ciphertext=CIPHERTEXT)

    async def test_raises_on_non_base64_plaintext(self, tmp_path) -> None:
        """A decrypt response whose plaintext is not valid base64 fails closed."""
        token_path = _write_token(tmp_path)
        client = _build_client(token_path)
        login_response = build_mocked_aiohttp_response(
            status=HTTPStatus.OK, json={"auth": {"client_token": "vault-token-abc"}}
        )
        decrypt_response = build_mocked_aiohttp_response(
            status=HTTPStatus.OK, json={"data": {"plaintext": "!!!not-b64"}}
        )
        session_cm = _mock_session([login_response, decrypt_response])

        with (
            patch(
                "fastapi_factory_utilities.core.plugins.odm_plugin.encryption.vault.aiohttp.ClientSession",
                return_value=session_cm,
            ),
            pytest.raises(VaultUnwrapError, match="base64"),
        ):
            await client.unwrap_master_key(ciphertext=CIPHERTEXT)
