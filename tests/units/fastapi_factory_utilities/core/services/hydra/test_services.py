"""Unit tests for the Hydra services."""

# pylint: disable=protected-access

import json
from base64 import b64encode
from http import HTTPStatus
from typing import Any
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from pydantic import HttpUrl, ValidationError

from fastapi_factory_utilities.core.plugins.aiohttp import AioHttpClientResource
from fastapi_factory_utilities.core.plugins.aiohttp.configs import HttpServiceDependencyConfig
from fastapi_factory_utilities.core.plugins.aiohttp.mockers import (
    build_mocked_aiohttp_resource,
    build_mocked_aiohttp_response,
)
from fastapi_factory_utilities.core.services.hydra.exceptions import HydraOperationError
from fastapi_factory_utilities.core.services.hydra.objects import HydraTokenIntrospectObject
from fastapi_factory_utilities.core.services.hydra.services import (
    HydraIntrospectGenericService,
    HydraIntrospectService,
    HydraOAuth2ClientCredentialsService,
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


@pytest.fixture(name="http_config")
def fixture_http_config() -> HttpServiceDependencyConfig:
    """Create an HttpServiceDependencyConfig for testing.

    Returns:
        HttpServiceDependencyConfig: A test HTTP config.
    """
    return HttpServiceDependencyConfig(url=HttpUrl("https://hydra.example.com"))


@pytest.fixture(name="http_config_admin")
def fixture_http_config_admin() -> HttpServiceDependencyConfig:
    """Create an admin HttpServiceDependencyConfig for testing.

    Returns:
        HttpServiceDependencyConfig: A test admin HTTP config.
    """
    return HttpServiceDependencyConfig(url=HttpUrl("https://hydra-admin.example.com"))


@pytest.fixture(name="http_config_public")
def fixture_http_config_public() -> HttpServiceDependencyConfig:
    """Create a public HttpServiceDependencyConfig for testing.

    Returns:
        HttpServiceDependencyConfig: A test public HTTP config.
    """
    return HttpServiceDependencyConfig(url=HttpUrl("https://hydra-public.example.com"))


@pytest.fixture(name="http_resource_admin")
def fixture_http_resource_admin(http_config_admin: HttpServiceDependencyConfig) -> AioHttpClientResource:
    """Create an admin AioHttpClientResource for testing.

    Args:
        http_config_admin (HttpServiceDependencyConfig): Admin HTTP config fixture.

    Returns:
        AioHttpClientResource: A test admin HTTP resource.
    """
    return AioHttpClientResource(dependency_config=http_config_admin)


@pytest.fixture(name="http_resource_public")
def fixture_http_resource_public(http_config_public: HttpServiceDependencyConfig) -> AioHttpClientResource:
    """Create a public AioHttpClientResource for testing.

    Args:
        http_config_public (HttpServiceDependencyConfig): Public HTTP config fixture.

    Returns:
        AioHttpClientResource: A test public HTTP resource.
    """
    return AioHttpClientResource(dependency_config=http_config_public)


@pytest.fixture(name="mock_introspect_data")
def fixture_mock_introspect_data() -> dict[str, Any]:
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


@pytest.fixture(name="mock_jwks_data")
def fixture_mock_jwks_data() -> dict[str, Any]:
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
        self, http_resource_admin: AioHttpClientResource, http_resource_public: AioHttpClientResource
    ) -> HydraIntrospectGenericService[MockIntrospectObject]:
        """Create a concrete implementation for testing.

        Args:
            http_resource_admin (AioHttpClientResource): Admin HTTP resource fixture.
            http_resource_public (AioHttpClientResource): Public HTTP resource fixture.

        Returns:
            HydraIntrospectGenericService[MockIntrospectObject]: Concrete service instance.
        """

        class ConcreteIntrospectService(HydraIntrospectGenericService[MockIntrospectObject]):
            """Concrete implementation for testing."""

            pass

        return ConcreteIntrospectService(
            hydra_admin_http_resource=http_resource_admin,
            hydra_public_http_resource=http_resource_public,
        )

    def test_init(
        self, http_resource_admin: AioHttpClientResource, http_resource_public: AioHttpClientResource
    ) -> None:
        """Test that __init__ properly initializes the service.

        Args:
            http_resource_admin (AioHttpClientResource): Admin HTTP resource fixture.
            http_resource_public (AioHttpClientResource): Public HTTP resource fixture.
        """

        class ConcreteIntrospectService(HydraIntrospectGenericService[MockIntrospectObject]):
            """Concrete implementation for testing."""

            pass

        service = ConcreteIntrospectService(
            hydra_admin_http_resource=http_resource_admin,
            hydra_public_http_resource=http_resource_public,
        )

        assert service._hydra_admin_http_resource == http_resource_admin
        assert service._hydra_public_http_resource == http_resource_public
        assert service._concreate_introspect_object_class == MockIntrospectObject
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

        mock_response = build_mocked_aiohttp_response(
            status=HTTPStatus.OK,
            json=mock_introspect_data,
        )
        mock_resource = build_mocked_aiohttp_resource(post=mock_response)
        service._hydra_admin_http_resource = mock_resource

        result: MockIntrospectObject = await service.introspect(token=token)

        assert result.active == mock_introspect_data["active"]
        assert result.client_id == mock_introspect_data["client_id"]
        assert result.sub == mock_introspect_data["sub"]

    @pytest.mark.parametrize(
        "status_code",
        [
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.UNAUTHORIZED,
            HTTPStatus.FORBIDDEN,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.INTERNAL_SERVER_ERROR,
            HTTPStatus.BAD_GATEWAY,
            HTTPStatus.SERVICE_UNAVAILABLE,
        ],
    )
    @pytest.mark.asyncio
    async def test_introspect_client_response_error(
        self,
        concrete_service: HydraIntrospectGenericService[MockIntrospectObject],
        status_code: HTTPStatus,
    ) -> None:
        """Test introspect raises HydraOperationError on ClientResponseError.

        Args:
            concrete_service (HydraIntrospectGenericService[MockIntrospectObject]): Concrete service fixture.
            status_code (HTTPStatus): HTTP status code.
        """
        service = concrete_service
        token: HydraAccessToken = HydraAccessToken("test_token")

        mock_response = build_mocked_aiohttp_response(
            status=status_code,
            error_message="Error",
        )
        mock_resource = build_mocked_aiohttp_resource(post=mock_response)
        service._hydra_admin_http_resource = mock_resource

        with pytest.raises(HydraOperationError) as exc_info:
            await service.introspect(token=token)

        assert "An error occurred while introspecting the token" in str(exc_info.value)

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

        mock_response = build_mocked_aiohttp_response(status=HTTPStatus.OK)
        mock_response.json = AsyncMock(  # type: ignore[method-assign]
            side_effect=json.JSONDecodeError(msg="Invalid JSON", doc="", pos=0)
        )
        mock_resource = build_mocked_aiohttp_resource(post=mock_response)
        service._hydra_admin_http_resource = mock_resource

        with pytest.raises(HydraOperationError) as exc_info:
            await service.introspect(token=token)

        assert "An error occurred while decoding the introspect response" in str(exc_info.value)

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
        mock_response = build_mocked_aiohttp_response(
            status=HTTPStatus.OK,
            json={"invalid": "data"},
        )
        mock_resource = build_mocked_aiohttp_resource(post=mock_response)
        service._hydra_admin_http_resource = mock_resource

        with pytest.raises(HydraOperationError) as exc_info:
            await service.introspect(token=token)

        assert "An error occurred while validating the introspect response" in str(exc_info.value)
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

        mock_response = build_mocked_aiohttp_response(
            status=HTTPStatus.OK,
            json=mock_jwks_data,
        )
        mock_resource = build_mocked_aiohttp_resource(get=mock_response)
        service._hydra_public_http_resource = mock_resource

        result: jwt.PyJWKSet = await service.get_wellknown_jwks()

        assert isinstance(result, jwt.PyJWKSet)

    @pytest.mark.parametrize(
        "status_code",
        [
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.UNAUTHORIZED,
            HTTPStatus.FORBIDDEN,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.INTERNAL_SERVER_ERROR,
            HTTPStatus.BAD_GATEWAY,
            HTTPStatus.SERVICE_UNAVAILABLE,
        ],
    )
    @pytest.mark.asyncio
    async def test_get_wellknown_jwks_client_response_error(
        self,
        concrete_service: HydraIntrospectGenericService[MockIntrospectObject],
        status_code: HTTPStatus,
    ) -> None:
        """Test get_wellknown_jwks raises HydraOperationError on ClientResponseError.

        Args:
            concrete_service (HydraIntrospectGenericService[MockIntrospectObject]): Concrete service fixture.
            status_code (HTTPStatus): HTTP status code.
        """
        service = concrete_service

        mock_response = build_mocked_aiohttp_response(
            status=status_code,
            error_message="Error",
        )
        mock_resource = build_mocked_aiohttp_resource(get=mock_response)
        service._hydra_public_http_resource = mock_resource

        with pytest.raises(HydraOperationError) as exc_info:
            await service.get_wellknown_jwks()

        assert "Failed to get the JWKS from the Hydra service" in str(exc_info.value)

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

        mock_response = build_mocked_aiohttp_response(status=HTTPStatus.OK)
        mock_response.json = AsyncMock(  # type: ignore[method-assign]
            side_effect=json.JSONDecodeError(msg="Invalid JSON", doc="", pos=0)
        )
        mock_resource = build_mocked_aiohttp_resource(get=mock_response)
        service._hydra_public_http_resource = mock_resource

        with pytest.raises(HydraOperationError) as exc_info:
            await service.get_wellknown_jwks()

        assert "Failed to decode the JWKS from the Hydra service" in str(exc_info.value)

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

        mock_response = build_mocked_aiohttp_response(
            status=HTTPStatus.OK,
            json={"invalid": "jwks"},
        )
        mock_resource = build_mocked_aiohttp_resource(get=mock_response)
        service._hydra_public_http_resource = mock_resource

        # Mock jwt.PyJWKSet.from_dict to raise ValidationError
        with patch("jwt.PyJWKSet.from_dict", side_effect=ValidationError.from_exception_data("TestModel", [])):
            with pytest.raises(HydraOperationError) as exc_info:
                await service.get_wellknown_jwks()

            assert "Failed to validate the JWKS from the Hydra service" in str(exc_info.value)
            assert isinstance(exc_info.value.__cause__, ValidationError)


class TestHydraIntrospectService:
    """Various tests for the HydraIntrospectService class."""

    def test_init(
        self, http_resource_admin: AioHttpClientResource, http_resource_public: AioHttpClientResource
    ) -> None:
        """Test that __init__ properly initializes the service.

        Args:
            http_resource_admin (AioHttpClientResource): Admin HTTP resource fixture.
            http_resource_public (AioHttpClientResource): Public HTTP resource fixture.
        """
        service = HydraIntrospectService(
            hydra_admin_http_resource=http_resource_admin,
            hydra_public_http_resource=http_resource_public,
        )

        assert service._hydra_admin_http_resource == http_resource_admin
        assert service._hydra_public_http_resource == http_resource_public
        assert service._concreate_introspect_object_class == HydraTokenIntrospectObject
        assert isinstance(service, HydraIntrospectGenericService)

    @pytest.mark.asyncio
    async def test_introspect_with_default_object(
        self,
        http_resource_admin: AioHttpClientResource,
        http_resource_public: AioHttpClientResource,
        mock_introspect_data: dict[str, Any],
    ) -> None:
        """Test introspect with default HydraTokenIntrospectObject.

        Args:
            http_resource_admin (AioHttpClientResource): Admin HTTP resource fixture.
            http_resource_public (AioHttpClientResource): Public HTTP resource fixture.
            mock_introspect_data (dict[str, Any]): Mock introspect data.
        """
        service = HydraIntrospectService(
            hydra_admin_http_resource=http_resource_admin,
            hydra_public_http_resource=http_resource_public,
        )

        token: HydraAccessToken = HydraAccessToken("test_token")

        mock_response = build_mocked_aiohttp_response(
            status=HTTPStatus.OK,
            json=mock_introspect_data,
        )
        mock_resource = build_mocked_aiohttp_resource(post=mock_response)
        service._hydra_admin_http_resource = mock_resource

        result: HydraTokenIntrospectObject = await service.introspect(token=token)

        assert result.active == mock_introspect_data["active"]
        assert result.client_id == mock_introspect_data["client_id"]
        assert result.sub == mock_introspect_data["sub"]


class TestHydraOAuth2ClientCredentialsService:
    """Various tests for the HydraOAuth2ClientCredentialsService class."""

    def test_init(self, http_resource_public: AioHttpClientResource) -> None:
        """Test that __init__ properly initializes the service.

        Args:
            http_resource_public (AioHttpClientResource): Public HTTP resource fixture.
        """
        service = HydraOAuth2ClientCredentialsService(hydra_public_http_resource=http_resource_public)

        assert service._hydra_public_http_resource == http_resource_public
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
    async def test_oauth2_client_credentials_success(self, http_resource_public: AioHttpClientResource) -> None:
        """Test successful oauth2_client_credentials call.

        Args:
            http_resource_public (AioHttpClientResource): Public HTTP resource fixture.
        """
        service = HydraOAuth2ClientCredentialsService(hydra_public_http_resource=http_resource_public)

        client_id: HydraClientId = HydraClientId("test_client_id")
        client_secret: HydraClientSecret = HydraClientSecret("test_client_secret")
        scopes: list[str] = ["read", "write", "admin"]
        access_token = "test_access_token"

        response_data = {"access_token": access_token, "token_type": "Bearer", "expires_in": 3600}

        mock_response = build_mocked_aiohttp_response(
            status=HTTPStatus.OK,
            json=response_data,
        )
        mock_resource = build_mocked_aiohttp_resource(post=mock_response)
        service._hydra_public_http_resource = mock_resource

        result: HydraAccessToken = await service.oauth2_client_credentials(
            client_id=client_id, client_secret=client_secret, scopes=scopes
        )

        assert result == access_token

    @pytest.mark.asyncio
    async def test_oauth2_client_credentials_single_scope(self, http_resource_public: AioHttpClientResource) -> None:
        """Test oauth2_client_credentials with single scope.

        Args:
            http_resource_public (AioHttpClientResource): Public HTTP resource fixture.
        """
        service = HydraOAuth2ClientCredentialsService(hydra_public_http_resource=http_resource_public)

        client_id: HydraClientId = HydraClientId("test_client_id")
        client_secret: HydraClientSecret = HydraClientSecret("test_client_secret")
        scopes: list[str] = ["read"]
        access_token = "test_access_token"

        response_data = {"access_token": access_token}

        mock_response = build_mocked_aiohttp_response(
            status=HTTPStatus.OK,
            json=response_data,
        )
        mock_resource = build_mocked_aiohttp_resource(post=mock_response)
        service._hydra_public_http_resource = mock_resource

        result: HydraAccessToken = await service.oauth2_client_credentials(
            client_id=client_id, client_secret=client_secret, scopes=scopes
        )

        assert result == access_token

    @pytest.mark.parametrize(
        "status_code",
        [
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.UNAUTHORIZED,
            HTTPStatus.FORBIDDEN,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.INTERNAL_SERVER_ERROR,
        ],
    )
    @pytest.mark.asyncio
    async def test_oauth2_client_credentials_error_status(
        self, http_resource_public: AioHttpClientResource, status_code: HTTPStatus
    ) -> None:
        """Test oauth2_client_credentials raises HydraOperationError on non-200 status.

        Args:
            http_resource_public (AioHttpClientResource): Public HTTP resource fixture.
            status_code (HTTPStatus): HTTP status code.
        """
        service = HydraOAuth2ClientCredentialsService(hydra_public_http_resource=http_resource_public)

        client_id: HydraClientId = HydraClientId("test_client_id")
        client_secret: HydraClientSecret = HydraClientSecret("test_client_secret")
        scopes: list[str] = ["read"]

        response_data = {"error": "invalid_client", "error_description": "Invalid client credentials"}

        mock_response = build_mocked_aiohttp_response(
            status=status_code,
            json=response_data,
        )
        mock_resource = build_mocked_aiohttp_resource(post=mock_response)
        service._hydra_public_http_resource = mock_resource

        with pytest.raises(HydraOperationError) as exc_info:
            await service.oauth2_client_credentials(client_id=client_id, client_secret=client_secret, scopes=scopes)

        assert "An error occurred while getting the client credentials" in str(exc_info.value)
