"""Unit tests for the Hydra services."""

import json
from base64 import b64encode
from http import HTTPStatus
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import jwt
import pytest
from pydantic import HttpUrl, ValidationError

from fastapi_factory_utilities.core.app import (
    DependencyConfig,
    HttpServiceDependencyConfig,
)
from fastapi_factory_utilities.core.services.hydra.exceptions import HydraOperationError
from fastapi_factory_utilities.core.services.hydra.objects import HydraTokenIntrospectObject
from fastapi_factory_utilities.core.services.hydra.services import (
    HydraIntrospectGenericService,
    HydraIntrospectService,
    HydraOAuth2ClientCredentialsService,
    depends_hydra_introspect_service,
    depends_hydra_oauth2_client_credentials_service,
)
from fastapi_factory_utilities.core.services.hydra.types import (
    HydraAccessToken,
    HydraClientId,
    HydraClientSecret,
)


# Test model class for generic service testing
class MockIntrospectObject(HydraTokenIntrospectObject):
    """Mock introspect object for testing."""

    pass


@pytest.fixture
def http_config() -> HttpServiceDependencyConfig:
    """Create an HttpServiceDependencyConfig for testing.

    Returns:
        HttpServiceDependencyConfig: A test HTTP config.
    """
    return HttpServiceDependencyConfig(url=HttpUrl("https://hydra.example.com"))


@pytest.fixture
def http_config_admin() -> HttpServiceDependencyConfig:
    """Create an admin HttpServiceDependencyConfig for testing.

    Returns:
        HttpServiceDependencyConfig: A test admin HTTP config.
    """
    return HttpServiceDependencyConfig(url=HttpUrl("https://hydra-admin.example.com"))


@pytest.fixture
def http_config_public() -> HttpServiceDependencyConfig:
    """Create a public HttpServiceDependencyConfig for testing.

    Returns:
        HttpServiceDependencyConfig: A test public HTTP config.
    """
    return HttpServiceDependencyConfig(url=HttpUrl("https://hydra-public.example.com"))


@pytest.fixture
def mock_introspect_data() -> dict[str, Any]:
    """Create mock introspect data.

    Returns:
        dict[str, Any]: Mock introspect data.
    """
    return {
        "active": True,
        "aud": ["audience1", "audience2"],
        "client_id": "test_client_id",
        "exp": 1234567890,
        "iat": 1234567890,
        "iss": "https://hydra.example.com",
        "nbf": 1234567890,
        "scope": "read write",
        "sub": "test_subject",
        "token_type": "Bearer",
        "token_use": "access",
    }


@pytest.fixture
def mock_jwks_data() -> dict[str, Any]:
    """Create mock JWKS data.

    Returns:
        dict[str, Any]: Mock JWKS data.
    """
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-key-id",
                "use": "sig",
                "n": "test-n",
                "e": "AQAB",
            }
        ]
    }


class TestHydraIntrospectGenericService:
    """Various tests for the HydraIntrospectGenericService class."""

    @pytest.fixture
    def concrete_service(
        self, http_config_admin: HttpServiceDependencyConfig, http_config_public: HttpServiceDependencyConfig
    ) -> HydraIntrospectGenericService[MockIntrospectObject]:
        """Create a concrete implementation for testing.

        Args:
            http_config_admin (HttpServiceDependencyConfig): Admin HTTP config fixture.
            http_config_public (HttpServiceDependencyConfig): Public HTTP config fixture.

        Returns:
            HydraIntrospectGenericService[MockIntrospectObject]: Concrete service instance.
        """

        class ConcreteIntrospectService(HydraIntrospectGenericService[MockIntrospectObject]):
            """Concrete implementation for testing."""

            pass

        return ConcreteIntrospectService(
            hydra_admin_http_config=http_config_admin,
            hydra_public_http_config=http_config_public,
        )

    def test_init(
        self, http_config_admin: HttpServiceDependencyConfig, http_config_public: HttpServiceDependencyConfig
    ) -> None:
        """Test that __init__ properly initializes the service.

        Args:
            http_config_admin (HttpServiceDependencyConfig): Admin HTTP config fixture.
            http_config_public (HttpServiceDependencyConfig): Public HTTP config fixture.
        """

        class ConcreteIntrospectService(HydraIntrospectGenericService[MockIntrospectObject]):
            """Concrete implementation for testing."""

            pass

        service = ConcreteIntrospectService(
            hydra_admin_http_config=http_config_admin,
            hydra_public_http_config=http_config_public,
        )

        assert service._hydra_admin_http_config == http_config_admin  # type: ignore[attr-defined]
        assert service._hydra_public_http_config == http_config_public  # type: ignore[attr-defined]
        assert service._concreate_introspect_object_class == MockIntrospectObject  # type: ignore[attr-defined]
        assert service.INTROSPECT_ENDPOINT == "/admin/oauth2/introspect"
        assert service.WELLKNOWN_JWKS_ENDPOINT == "/.well-known/jwks.json"

    @pytest.mark.asyncio
    async def test_introspect_success(
        self,
        concrete_service: HydraIntrospectGenericService[MockIntrospectObject],
        mock_introspect_data: dict[str, Any],
    ) -> None:
        """Test successful introspect call.

        Args:
            concrete_service (HydraIntrospectGenericService[MockIntrospectObject]): Concrete service fixture.
            mock_introspect_data (dict[str, Any]): Mock introspect data.
        """
        service = concrete_service

        token: HydraAccessToken = HydraAccessToken("test_token")
        # Use full mock data since MockIntrospectObject extends HydraTokenIntrospectObject
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=mock_introspect_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result: MockIntrospectObject = await service.introspect(token=token)

        assert result.active == mock_introspect_data["active"]
        assert result.client_id == mock_introspect_data["client_id"]
        assert result.sub == mock_introspect_data["sub"]
        mock_session.post.assert_called_once_with(url=service.INTROSPECT_ENDPOINT, data={"token": token})

    @pytest.mark.parametrize(
        "status_code",
        [
            400,
            401,
            403,
            404,
            500,
            502,
            503,
        ],
    )
    @pytest.mark.asyncio
    async def test_introspect_client_response_error(
        self,
        concrete_service: HydraIntrospectGenericService[MockIntrospectObject],
        status_code: int,
    ) -> None:
        """Test introspect raises HydraOperationError on ClientResponseError.

        Args:
            concrete_service (HydraIntrospectGenericService[MockIntrospectObject]): Concrete service fixture.
            status_code (int): HTTP status code.
        """
        service = concrete_service

        token: HydraAccessToken = HydraAccessToken("test_token")
        error = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=status_code,
            message="Error",
        )

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock(side_effect=error)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(HydraOperationError) as exc_info:
                await service.introspect(token=token)

            assert "Failed to introspect the token" in str(exc_info.value)
            assert exc_info.value.status_code == status_code  # type: ignore[attr-defined]
            assert exc_info.value.__cause__ == error

    @pytest.mark.asyncio
    async def test_introspect_json_decode_error(
        self,
        concrete_service: HydraIntrospectGenericService[MockIntrospectObject],
    ) -> None:
        """Test introspect raises HydraOperationError on JSONDecodeError.

        Args:
            concrete_service (HydraIntrospectGenericService[MockIntrospectObject]): Concrete service fixture.
        """
        service = concrete_service

        token: HydraAccessToken = HydraAccessToken("test_token")
        error = json.JSONDecodeError(msg="Invalid JSON", doc="", pos=0)

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(side_effect=error)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(HydraOperationError) as exc_info:
                await service.introspect(token=token)

            assert "Failed to decode the introspect response" in str(exc_info.value)
            assert exc_info.value.__cause__ == error

    @pytest.mark.asyncio
    async def test_introspect_validation_error(
        self,
        concrete_service: HydraIntrospectGenericService[MockIntrospectObject],
    ) -> None:
        """Test introspect raises HydraOperationError on ValidationError.

        Args:
            concrete_service (HydraIntrospectGenericService[MockIntrospectObject]): Concrete service fixture.
        """
        service = concrete_service

        token: HydraAccessToken = HydraAccessToken("test_token")
        # Return invalid data that will cause ValidationError
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"invalid": "data"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(HydraOperationError) as exc_info:
                await service.introspect(token=token)

            assert "Failed to validate the introspect response" in str(exc_info.value)
            assert isinstance(exc_info.value.__cause__, ValidationError)

    @pytest.mark.asyncio
    async def test_get_wellknown_jwks_success(
        self,
        concrete_service: HydraIntrospectGenericService[MockIntrospectObject],
        mock_jwks_data: dict[str, Any],
    ) -> None:
        """Test successful get_wellknown_jwks call.

        Args:
            concrete_service (HydraIntrospectGenericService[MockIntrospectObject]): Concrete service fixture.
            mock_jwks_data (dict[str, Any]): Mock JWKS data.
        """
        service = concrete_service

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=mock_jwks_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result: jwt.PyJWKSet = await service.get_wellknown_jwks()

        assert isinstance(result, jwt.PyJWKSet)
        mock_session.get.assert_called_once_with(url=service.WELLKNOWN_JWKS_ENDPOINT)

    @pytest.mark.parametrize(
        "status_code",
        [
            400,
            401,
            403,
            404,
            500,
            502,
            503,
        ],
    )
    @pytest.mark.asyncio
    async def test_get_wellknown_jwks_client_response_error(
        self,
        concrete_service: HydraIntrospectGenericService[MockIntrospectObject],
        status_code: int,
    ) -> None:
        """Test get_wellknown_jwks raises HydraOperationError on ClientResponseError.

        Args:
            concrete_service (HydraIntrospectGenericService[MockIntrospectObject]): Concrete service fixture.
            status_code (int): HTTP status code.
        """
        service = concrete_service

        error = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=status_code,
            message="Error",
        )

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock(side_effect=error)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(HydraOperationError) as exc_info:
                await service.get_wellknown_jwks()

            assert "Failed to get the JWKS from the Hydra service" in str(exc_info.value)
            assert exc_info.value.status_code == status_code  # type: ignore[attr-defined]
            assert exc_info.value.__cause__ == error

    @pytest.mark.asyncio
    async def test_get_wellknown_jwks_json_decode_error(
        self,
        concrete_service: HydraIntrospectGenericService[MockIntrospectObject],
    ) -> None:
        """Test get_wellknown_jwks raises HydraOperationError on JSONDecodeError.

        Args:
            concrete_service (HydraIntrospectGenericService[MockIntrospectObject]): Concrete service fixture.
        """
        service = concrete_service

        error = json.JSONDecodeError(msg="Invalid JSON", doc="", pos=0)

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(side_effect=error)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(HydraOperationError) as exc_info:
                await service.get_wellknown_jwks()

            assert "Failed to decode the JWKS from the Hydra service" in str(exc_info.value)
            assert exc_info.value.__cause__ == error

    @pytest.mark.asyncio
    async def test_get_wellknown_jwks_validation_error(
        self,
        concrete_service: HydraIntrospectGenericService[MockIntrospectObject],
    ) -> None:
        """Test get_wellknown_jwks raises HydraOperationError on ValidationError.

        Args:
            concrete_service (HydraIntrospectGenericService[MockIntrospectObject]): Concrete service fixture.
        """
        service = concrete_service

        # Return invalid JWKS data that will cause ValidationError in jwt.PyJWKSet.from_dict
        # Actually, jwt.PyJWKSet.from_dict might not raise ValidationError, but let's test the error path
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"invalid": "jwks"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # Mock jwt.PyJWKSet.from_dict to raise ValidationError
        with patch("aiohttp.ClientSession", return_value=mock_session):
            with patch("jwt.PyJWKSet.from_dict", side_effect=ValidationError.from_exception_data("TestModel", [])):
                with pytest.raises(HydraOperationError) as exc_info:
                    await service.get_wellknown_jwks()

                assert "Failed to validate the JWKS from the Hydra service" in str(exc_info.value)
                assert isinstance(exc_info.value.__cause__, ValidationError)


class TestHydraIntrospectService:
    """Various tests for the HydraIntrospectService class."""

    def test_init(
        self, http_config_admin: HttpServiceDependencyConfig, http_config_public: HttpServiceDependencyConfig
    ) -> None:
        """Test that __init__ properly initializes the service.

        Args:
            http_config_admin (HttpServiceDependencyConfig): Admin HTTP config fixture.
            http_config_public (HttpServiceDependencyConfig): Public HTTP config fixture.
        """
        service = HydraIntrospectService(
            hydra_admin_http_config=http_config_admin,
            hydra_public_http_config=http_config_public,
        )

        assert service._hydra_admin_http_config == http_config_admin  # type: ignore[attr-defined]
        assert service._hydra_public_http_config == http_config_public  # type: ignore[attr-defined]
        assert service._concreate_introspect_object_class == HydraTokenIntrospectObject  # type: ignore[attr-defined]
        assert isinstance(service, HydraIntrospectGenericService)

    @pytest.mark.asyncio
    async def test_introspect_with_default_object(
        self,
        http_config_admin: HttpServiceDependencyConfig,
        http_config_public: HttpServiceDependencyConfig,
        mock_introspect_data: dict[str, Any],
    ) -> None:
        """Test introspect with default HydraTokenIntrospectObject.

        Args:
            http_config_admin (HttpServiceDependencyConfig): Admin HTTP config fixture.
            http_config_public (HttpServiceDependencyConfig): Public HTTP config fixture.
            mock_introspect_data (dict[str, Any]): Mock introspect data.
        """
        service = HydraIntrospectService(
            hydra_admin_http_config=http_config_admin,
            hydra_public_http_config=http_config_public,
        )

        token: HydraAccessToken = HydraAccessToken("test_token")
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=mock_introspect_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result: HydraTokenIntrospectObject = await service.introspect(token=token)

        assert result.active == mock_introspect_data["active"]
        assert result.client_id == mock_introspect_data["client_id"]
        assert result.sub == mock_introspect_data["sub"]


class TestHydraOAuth2ClientCredentialsService:
    """Various tests for the HydraOAuth2ClientCredentialsService class."""

    def test_init(self, http_config_public: HttpServiceDependencyConfig) -> None:
        """Test that __init__ properly initializes the service.

        Args:
            http_config_public (HttpServiceDependencyConfig): Public HTTP config fixture.
        """
        service = HydraOAuth2ClientCredentialsService(hydra_public_http_config=http_config_public)

        assert service._hydra_public_http_config == http_config_public  # type: ignore[attr-defined]
        assert service.CLIENT_CREDENTIALS_ENDPOINT == "/oauth2/token"

    def test_build_bearer_header(self) -> None:
        """Test build_bearer_header class method."""
        client_id: HydraClientId = HydraClientId("test_client_id")
        client_secret: HydraClientSecret = HydraClientSecret("test_client_secret")

        result: str = HydraOAuth2ClientCredentialsService.build_bearer_header(
            client_id=client_id, client_secret=client_secret
        )

        auth_string = f"{client_id}:{client_secret}"
        expected_b64 = b64encode(auth_string.encode("utf-8")).decode("utf-8")
        assert result == f"Basic {expected_b64}"
        assert result.startswith("Basic ")

    @pytest.mark.parametrize(
        "client_id,client_secret",
        [
            ("client1", "secret1"),
            ("client_with_special:chars", "secret_with_special:chars"),
            ("", ""),
            ("very_long_client_id_" * 10, "very_long_secret_" * 10),
        ],
    )
    def test_build_bearer_header_various_combinations(self, client_id: str, client_secret: str) -> None:
        """Test build_bearer_header with various client_id and client_secret combinations.

        Args:
            client_id (str): Client ID to test.
            client_secret (str): Client secret to test.
        """
        client_id_typed: HydraClientId = HydraClientId(client_id)
        client_secret_typed: HydraClientSecret = HydraClientSecret(client_secret)

        result: str = HydraOAuth2ClientCredentialsService.build_bearer_header(
            client_id=client_id_typed, client_secret=client_secret_typed
        )

        auth_string = f"{client_id}:{client_secret}"
        expected_b64 = b64encode(auth_string.encode("utf-8")).decode("utf-8")
        assert result == f"Basic {expected_b64}"

    @pytest.mark.asyncio
    async def test_oauth2_client_credentials_success(self, http_config_public: HttpServiceDependencyConfig) -> None:
        """Test successful oauth2_client_credentials call.

        Args:
            http_config_public (HttpServiceDependencyConfig): Public HTTP config fixture.
        """
        service = HydraOAuth2ClientCredentialsService(hydra_public_http_config=http_config_public)

        client_id: HydraClientId = HydraClientId("test_client_id")
        client_secret: HydraClientSecret = HydraClientSecret("test_client_secret")
        scopes: list[str] = ["read", "write", "admin"]
        access_token = "test_access_token"

        response_data = {"access_token": access_token, "token_type": "Bearer", "expires_in": 3600}

        mock_response = AsyncMock()
        mock_response.status = HTTPStatus.OK
        mock_response.json = AsyncMock(return_value=response_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result: HydraAccessToken = await service.oauth2_client_credentials(
                client_id=client_id, client_secret=client_secret, scopes=scopes
            )

        assert result == access_token

        # Verify the call was made correctly
        call_kwargs = mock_session.post.call_args[1]
        assert call_kwargs["url"] == service.CLIENT_CREDENTIALS_ENDPOINT
        assert call_kwargs["headers"]["Authorization"] == service.build_bearer_header(client_id, client_secret)
        assert call_kwargs["data"]["grant_type"] == "client_credentials"
        assert call_kwargs["data"]["scope"] == " ".join(scopes)

    @pytest.mark.asyncio
    async def test_oauth2_client_credentials_single_scope(
        self, http_config_public: HttpServiceDependencyConfig
    ) -> None:
        """Test oauth2_client_credentials with single scope.

        Args:
            http_config_public (HttpServiceDependencyConfig): Public HTTP config fixture.
        """
        service = HydraOAuth2ClientCredentialsService(hydra_public_http_config=http_config_public)

        client_id: HydraClientId = HydraClientId("test_client_id")
        client_secret: HydraClientSecret = HydraClientSecret("test_client_secret")
        scopes: list[str] = ["read"]
        access_token = "test_access_token"

        response_data = {"access_token": access_token}

        mock_response = AsyncMock()
        mock_response.status = HTTPStatus.OK
        mock_response.json = AsyncMock(return_value=response_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result: HydraAccessToken = await service.oauth2_client_credentials(
                client_id=client_id, client_secret=client_secret, scopes=scopes
            )

        assert result == access_token

        # Verify scope is correctly formatted
        call_kwargs = mock_session.post.call_args[1]
        assert call_kwargs["data"]["scope"] == "read"

    @pytest.mark.parametrize(
        "status_code",
        [
            400,
            401,
            403,
            404,
            500,
        ],
    )
    @pytest.mark.asyncio
    async def test_oauth2_client_credentials_error_status(
        self, http_config_public: HttpServiceDependencyConfig, status_code: int
    ) -> None:
        """Test oauth2_client_credentials raises HydraOperationError on non-200 status.

        Args:
            http_config_public (HttpServiceDependencyConfig): Public HTTP config fixture.
            status_code (int): HTTP status code.
        """
        service = HydraOAuth2ClientCredentialsService(hydra_public_http_config=http_config_public)

        client_id: HydraClientId = HydraClientId("test_client_id")
        client_secret: HydraClientSecret = HydraClientSecret("test_client_secret")
        scopes: list[str] = ["read"]

        response_data = {"error": "invalid_client", "error_description": "Invalid client credentials"}

        mock_response = AsyncMock()
        mock_response.status = status_code
        mock_response.json = AsyncMock(return_value=response_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(HydraOperationError) as exc_info:
                await service.oauth2_client_credentials(client_id=client_id, client_secret=client_secret, scopes=scopes)

            assert "Failed to get client credentials" in str(exc_info.value)
            assert str(response_data) in str(exc_info.value)


class TestDependencyInjectionFunctions:
    """Various tests for dependency injection functions."""

    def test_depends_hydra_introspect_service_success(
        self, http_config_admin: HttpServiceDependencyConfig, http_config_public: HttpServiceDependencyConfig
    ) -> None:
        """Test depends_hydra_introspect_service with valid configuration.

        Args:
            http_config_admin (HttpServiceDependencyConfig): Admin HTTP config fixture.
            http_config_public (HttpServiceDependencyConfig): Public HTTP config fixture.
        """
        dependency_config = DependencyConfig(
            hydra_admin=http_config_admin,
            hydra_public=http_config_public,
        )

        service = depends_hydra_introspect_service(dependency_config=dependency_config)

        assert isinstance(service, HydraIntrospectService)
        assert service._hydra_admin_http_config == http_config_admin  # type: ignore[attr-defined]
        assert service._hydra_public_http_config == http_config_public  # type: ignore[attr-defined]

    def test_depends_hydra_introspect_service_missing_admin(
        self, http_config_public: HttpServiceDependencyConfig
    ) -> None:
        """Test depends_hydra_introspect_service raises error when hydra_admin is missing.

        Args:
            http_config_public (HttpServiceDependencyConfig): Public HTTP config fixture.
        """
        dependency_config = DependencyConfig(
            hydra_admin=None,
            hydra_public=http_config_public,
        )

        with pytest.raises(HydraOperationError) as exc_info:
            depends_hydra_introspect_service(dependency_config=dependency_config)

        assert "Hydra admin dependency not configured" in str(exc_info.value)

    def test_depends_hydra_introspect_service_missing_public(
        self, http_config_admin: HttpServiceDependencyConfig
    ) -> None:
        """Test depends_hydra_introspect_service raises error when hydra_public is missing.

        Args:
            http_config_admin (HttpServiceDependencyConfig): Admin HTTP config fixture.
        """
        dependency_config = DependencyConfig(
            hydra_admin=http_config_admin,
            hydra_public=None,
        )

        with pytest.raises(HydraOperationError) as exc_info:
            depends_hydra_introspect_service(dependency_config=dependency_config)

        assert "Hydra public dependency not configured" in str(exc_info.value)

    def test_depends_hydra_oauth2_client_credentials_service_success(
        self, http_config_public: HttpServiceDependencyConfig
    ) -> None:
        """Test depends_hydra_oauth2_client_credentials_service with valid configuration.

        Args:
            http_config_public (HttpServiceDependencyConfig): Public HTTP config fixture.
        """
        dependency_config = DependencyConfig(
            hydra_public=http_config_public,
        )

        service = depends_hydra_oauth2_client_credentials_service(dependency_config=dependency_config)

        assert isinstance(service, HydraOAuth2ClientCredentialsService)
        assert service._hydra_public_http_config == http_config_public  # type: ignore[attr-defined]

    def test_depends_hydra_oauth2_client_credentials_service_missing_public(self) -> None:
        """Test depends_hydra_oauth2_client_credentials_service raises error when hydra_public is missing."""
        dependency_config = DependencyConfig(
            hydra_public=None,
        )

        with pytest.raises(HydraOperationError) as exc_info:
            depends_hydra_oauth2_client_credentials_service(dependency_config=dependency_config)

        assert "Hydra public dependency not configured" in str(exc_info.value)
