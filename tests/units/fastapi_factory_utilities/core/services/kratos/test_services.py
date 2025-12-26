"""Unit tests for the Kratos services."""

import datetime
import json
import uuid
from http import HTTPStatus
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
from pydantic import BaseModel, HttpUrl, ValidationError

from fastapi_factory_utilities.core.plugins.aiohttp import AioHttpClientResource
from fastapi_factory_utilities.core.plugins.aiohttp.configs import HttpServiceDependencyConfig
from fastapi_factory_utilities.core.services.kratos.enums import AuthenticationMethodEnum
from fastapi_factory_utilities.core.services.kratos.exceptions import (
    KratosOperationError,
    KratosSessionInvalidError,
)
from fastapi_factory_utilities.core.services.kratos.services import (
    KratosGenericWhoamiService,
    KratosIdentityGenericService,
)
from fastapi_factory_utilities.core.services.kratos.types import (
    KratosIdentityId,
    KratosRecoveryLink,
)


# Test model classes
class MockSessionObject(BaseModel):
    """Mock session object for testing."""

    id: uuid.UUID
    active: bool
    data: dict[str, Any]


class MockIdentityObject(BaseModel):
    """Mock identity object for testing."""

    id: KratosIdentityId
    email: str
    data: dict[str, Any]


@pytest.fixture(name="http_config")
def fixture_http_config() -> HttpServiceDependencyConfig:
    """Create an HttpServiceDependencyConfig for testing.

    Returns:
        HttpServiceDependencyConfig: A test HTTP config.
    """
    return HttpServiceDependencyConfig(url=HttpUrl("https://kratos.example.com"))


@pytest.fixture(name="http_resource_public")
def fixture_http_resource_public(http_config: HttpServiceDependencyConfig) -> AioHttpClientResource:
    """Create a public AioHttpClientResource for testing.

    Args:
        http_config (HttpServiceDependencyConfig): HTTP config fixture.

    Returns:
        AioHttpClientResource: A test public HTTP resource.
    """
    return AioHttpClientResource(dependency_config=http_config)


@pytest.fixture(name="http_resource_admin")
def fixture_http_resource_admin(http_config: HttpServiceDependencyConfig) -> AioHttpClientResource:
    """Create an admin AioHttpClientResource for testing.

    Args:
        http_config (HttpServiceDependencyConfig): HTTP config fixture.

    Returns:
        AioHttpClientResource: A test admin HTTP resource.
    """
    return AioHttpClientResource(dependency_config=http_config)


@pytest.fixture(name="mock_session_data")
def fixture_mock_session_data() -> dict[str, Any]:
    """Create mock session data.

    Returns:
        dict[str, Any]: Mock session data.
    """
    return {
        "id": str(uuid.uuid4()),
        "active": True,
        "data": {"test": "value"},
    }


@pytest.fixture(name="mock_identity_data")
def fixture_mock_identity_data() -> dict[str, Any]:
    """Create mock identity data.

    Returns:
        dict[str, Any]: Mock identity data.
    """
    return {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "data": {"test": "value"},
    }


@pytest.fixture(name="identity_id")
def fixture_identity_id() -> KratosIdentityId:
    """Create a test identity ID.

    Returns:
        KratosIdentityId: A test identity ID.
    """
    return KratosIdentityId(uuid.uuid4())


def mock_acquire_client_session(mock_session: AsyncMock) -> AsyncMock:
    """Mock acquire_client_session context manager.

    Args:
        mock_session (AsyncMock): The mocked session to yield.

    Returns:
        AsyncMock: An async context manager that yields the mocked session.
    """
    mock_context_manager = AsyncMock()
    mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context_manager.__aexit__ = AsyncMock(return_value=None)
    return mock_context_manager


class TestKratosGenericWhoamiService:
    """Various tests for the KratosGenericWhoamiService class."""

    @pytest.fixture
    def concrete_service(
        self, http_resource_public: AioHttpClientResource
    ) -> KratosGenericWhoamiService[MockSessionObject]:
        """Create a concrete implementation for testing.

        Args:
            http_resource_public (AioHttpClientResource): Public HTTP resource fixture.

        Returns:
            KratosGenericWhoamiService[MockSessionObject]: Concrete service instance.
        """

        class ConcreteWhoamiService(KratosGenericWhoamiService[MockSessionObject]):
            """Concrete implementation for testing."""

            pass

        return ConcreteWhoamiService(kratos_public_http_resource=http_resource_public)

    def test_init(self, http_resource_public: AioHttpClientResource) -> None:
        """Test that __init__ properly initializes the service.

        Args:
            http_resource_public (AioHttpClientResource): Public HTTP resource fixture.
        """

        class ConcreteWhoamiService(KratosGenericWhoamiService[MockSessionObject]):
            """Concrete implementation for testing."""

            pass

        service = ConcreteWhoamiService(kratos_public_http_resource=http_resource_public)

        assert service._kratos_public_http_resource == http_resource_public  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert service._concreate_session_object_class == MockSessionObject  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert service.COOKIE_NAME == "ory_kratos_session"

    @pytest.mark.asyncio
    async def test_whoami_success(
        self,
        concrete_service: KratosGenericWhoamiService[MockSessionObject],
        mock_session_data: dict[str, Any],
    ) -> None:
        """Test successful whoami call.

        Args:
            concrete_service (KratosGenericWhoamiService[MockSessionObject]): Concrete service fixture.
            mock_session_data (dict[str, Any]): Mock session data.
        """
        service = concrete_service

        cookie_value: str = "test_cookie_value"
        mock_response = AsyncMock()
        mock_response.status = HTTPStatus.OK
        mock_response.reason = "OK"
        mock_response.json = AsyncMock(return_value=mock_session_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        service._kratos_public_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
            return_value=mock_acquire_client_session(mock_session)
        )
        result: MockSessionObject = await service.whoami(cookie_value=cookie_value)

        assert result.id == uuid.UUID(mock_session_data["id"])
        assert result.active == mock_session_data["active"]
        assert result.data == mock_session_data["data"]
        mock_session.get.assert_called_once_with(url="/sessions/whoami")

    @pytest.mark.asyncio
    async def test_whoami_cookie_set(
        self,
        concrete_service: KratosGenericWhoamiService[MockSessionObject],
        mock_session_data: dict[str, Any],
    ) -> None:
        """Test that cookie is correctly set in request.

        Args:
            concrete_service (KratosGenericWhoamiService[MockSessionObject]): Concrete service fixture.
            mock_session_data (dict[str, Any]): Mock session data.
        """
        service = concrete_service

        cookie_value: str = "test_cookie_value"
        mock_response = AsyncMock()
        mock_response.status = HTTPStatus.OK
        mock_response.reason = "OK"
        mock_response.json = AsyncMock(return_value=mock_session_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        service._kratos_public_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
            return_value=mock_acquire_client_session(mock_session)
        )
        await service.whoami(cookie_value=cookie_value)

        # Verify the session was used (the cookies are passed to acquire_client_session)
        service._kratos_public_http_resource.acquire_client_session.assert_called_once()  # type: ignore[attr-defined]

    @pytest.mark.parametrize(
        "status_code,expected_exception",
        [
            (500, KratosOperationError),
            (501, KratosOperationError),
            (502, KratosOperationError),
            (503, KratosOperationError),
            (504, KratosOperationError),
            (400, KratosOperationError),
            (403, KratosOperationError),
            (404, KratosOperationError),
        ],
    )
    @pytest.mark.asyncio
    async def test_whoami_error_status_codes(
        self,
        concrete_service: KratosGenericWhoamiService[MockSessionObject],
        status_code: int,
        expected_exception: type[Exception],
    ) -> None:
        """Test whoami raises appropriate exceptions for different status codes.

        Args:
            concrete_service (KratosGenericWhoamiService[MockSessionObject]): Concrete service fixture.
            status_code (int): HTTP status code.
            expected_exception (type[Exception]): Expected exception type.
        """
        service = concrete_service

        cookie_value: str = "test_cookie_value"
        mock_response = AsyncMock()
        mock_response.status = status_code
        mock_response.reason = "Error"
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        service._kratos_public_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
            return_value=mock_acquire_client_session(mock_session)
        )
        with pytest.raises(expected_exception) as exc_info:
            await service.whoami(cookie_value=cookie_value)

        assert str(status_code) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_whoami_unauthorized(
        self,
        concrete_service: KratosGenericWhoamiService[MockSessionObject],
    ) -> None:
        """Test whoami raises KratosSessionInvalidError on 401.

        Args:
            concrete_service (KratosGenericWhoamiService[MockSessionObject]): Concrete service fixture.
        """
        service = concrete_service

        cookie_value: str = "test_cookie_value"
        mock_response = AsyncMock()
        mock_response.status = HTTPStatus.UNAUTHORIZED
        mock_response.reason = "Unauthorized"
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        service._kratos_public_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
            return_value=mock_acquire_client_session(mock_session)
        )
        with pytest.raises(KratosSessionInvalidError) as exc_info:
            await service.whoami(cookie_value=cookie_value)

        assert "Kratos session invalid" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_whoami_validation_error(
        self,
        concrete_service: KratosGenericWhoamiService[MockSessionObject],
    ) -> None:
        """Test whoami raises KratosOperationError on ValidationError.

        Args:
            concrete_service (KratosGenericWhoamiService[MockSessionObject]): Concrete service fixture.
        """
        service = concrete_service

        cookie_value: str = "test_cookie_value"
        mock_response = AsyncMock()
        mock_response.status = HTTPStatus.OK
        mock_response.reason = "OK"
        # Return invalid data that will cause ValidationError
        mock_response.json = AsyncMock(return_value={"invalid": "data"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        service._kratos_public_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
            return_value=mock_acquire_client_session(mock_session)
        )
        with pytest.raises(KratosOperationError) as exc_info:
            await service.whoami(cookie_value=cookie_value)

        assert "Kratos service error" in str(exc_info.value)


class TestKratosIdentityGenericService:
    """Various tests for the KratosIdentityGenericService class."""

    @pytest.fixture
    def concrete_service(
        self, http_resource_admin: AioHttpClientResource
    ) -> KratosIdentityGenericService[MockIdentityObject, MockSessionObject]:
        """Create a concrete implementation for testing.

        Args:
            http_resource_admin (AioHttpClientResource): Admin HTTP resource fixture.

        Returns:
            KratosIdentityGenericService[MockIdentityObject, MockSessionObject]: Concrete service instance.
        """

        class ConcreteIdentityService(KratosIdentityGenericService[MockIdentityObject, MockSessionObject]):
            """Concrete implementation for testing."""

            pass

        return ConcreteIdentityService(kratos_admin_http_resource=http_resource_admin)

    def test_init(self, http_resource_admin: AioHttpClientResource) -> None:
        """Test that __init__ properly initializes the service.

        Args:
            http_resource_admin (AioHttpClientResource): Admin HTTP resource fixture.
        """

        class ConcreteIdentityService(KratosIdentityGenericService[MockIdentityObject, MockSessionObject]):
            """Concrete implementation for testing."""

            pass

        service = ConcreteIdentityService(kratos_admin_http_resource=http_resource_admin)

        assert service._kratos_admin_http_resource == http_resource_admin  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert service._concreate_identity_object_class == MockIdentityObject  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert service._concreate_session_object_class == MockSessionObject  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert service.IDENTITY_ENDPOINT == "/admin/identities"

    @pytest.mark.asyncio
    async def test_get_identity_success(
        self,
        concrete_service: KratosIdentityGenericService[MockIdentityObject, MockSessionObject],
        identity_id: KratosIdentityId,
        mock_identity_data: dict[str, Any],
    ) -> None:
        """Test successful get_identity call.

        Args:
            concrete_service: Concrete service fixture.
            identity_id: Identity ID fixture.
            mock_identity_data: Mock identity data.
        """
        service = concrete_service

        mock_identity_data["id"] = str(identity_id)
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=mock_identity_data)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        service._kratos_admin_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
            return_value=mock_acquire_client_session(mock_session)
        )
        result: MockIdentityObject = await service.get_identity(identity_id=identity_id)

        assert result.id == identity_id
        assert result.email == mock_identity_data["email"]
        mock_session.get.assert_called_once_with(url=f"{service.IDENTITY_ENDPOINT}/{identity_id}")

    @pytest.mark.parametrize(
        "exception_class,exception_kwargs",
        [
            (aiohttp.ClientResponseError, {"status": 404, "message": "Not Found"}),
            (json.JSONDecodeError, {"msg": "Invalid JSON", "doc": "", "pos": 0}),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_identity_errors(
        self,
        concrete_service: KratosIdentityGenericService[MockIdentityObject, MockSessionObject],
        identity_id: KratosIdentityId,
        exception_class: type[Exception],
        exception_kwargs: dict[str, Any],
    ) -> None:
        """Test get_identity error scenarios.

        Args:
            concrete_service: Concrete service fixture.
            identity_id (KratosIdentityId): Identity ID fixture.
            exception_class (type[Exception]): Exception class to raise.
            exception_kwargs (dict[str, Any]): Exception kwargs.
        """
        service = concrete_service

        if exception_class == aiohttp.ClientResponseError:
            error = aiohttp.ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=exception_kwargs["status"],
                message=exception_kwargs["message"],
            )
        elif exception_class == json.JSONDecodeError:
            error = json.JSONDecodeError(
                msg=exception_kwargs["msg"],
                doc=exception_kwargs["doc"],
                pos=exception_kwargs["pos"],
            )
        else:  # ValidationError
            # Create a ValidationError by trying to validate invalid data
            try:
                MockSessionObject.model_validate({"invalid": "data"})
            except ValidationError as e:
                error = e
            else:
                # This should never happen, but satisfy type checker
                error = ValidationError.from_exception_data("TestModel", [])

        mock_response = AsyncMock()
        if exception_class == aiohttp.ClientResponseError:
            mock_response.raise_for_status = MagicMock(side_effect=error)
        else:
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(side_effect=error)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        service._kratos_admin_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
            return_value=mock_acquire_client_session(mock_session)
        )
        with pytest.raises(KratosOperationError) as exc_info:
            await service.get_identity(identity_id=identity_id)

            assert "Failed to get the Kratos identity" in str(exc_info.value)
            assert exc_info.value.__cause__ == error
            # Check that identity_id is in exception context
            assert hasattr(exc_info.value, "identity_id") or str(identity_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_identity_validation_error(
        self,
        concrete_service: KratosIdentityGenericService[MockIdentityObject, MockSessionObject],
        identity_id: KratosIdentityId,
    ) -> None:
        """Test get_identity with ValidationError.

        Args:
            concrete_service: Concrete service fixture.
            identity_id (KratosIdentityId): Identity ID fixture.
        """
        service = concrete_service

        # Create a ValidationError by trying to validate invalid data
        try:
            MockIdentityObject.model_validate({"invalid": "data"})
            error: ValidationError = ValidationError.from_exception_data("TestModel", [])
        except ValidationError as e:
            error = e
        else:
            # This should never happen, but satisfy type checker
            error = ValidationError.from_exception_data("TestModel", [])

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(side_effect=error)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        service._kratos_admin_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
            return_value=mock_acquire_client_session(mock_session)
        )
        with pytest.raises(KratosOperationError) as exc_info:
            await service.get_identity(identity_id=identity_id)

            assert "Failed to get the Kratos identity" in str(exc_info.value)
            assert exc_info.value.__cause__ == error

    @pytest.mark.asyncio
    async def test_create_identity_not_implemented(
        self,
        concrete_service: KratosIdentityGenericService[MockIdentityObject, MockSessionObject],
    ) -> None:
        """Test create_identity raises NotImplementedError.

        Args:
            concrete_service: Concrete service fixture.
        """
        service = concrete_service

        identity = MockIdentityObject(
            id=KratosIdentityId(uuid.uuid4()),
            email="test@example.com",
            data={},
        )

        with pytest.raises(NotImplementedError):
            await service.create_identity(identity=identity)

    @pytest.mark.parametrize(
        "credentials_type,identifier",
        [
            (AuthenticationMethodEnum.PASSWORD, None),
            (AuthenticationMethodEnum.TOTP, None),
            (AuthenticationMethodEnum.WEBAUTHN, None),
            (AuthenticationMethodEnum.OIDC, "test_identifier"),
            (AuthenticationMethodEnum.SAML, "test_identifier"),
        ],
    )
    @pytest.mark.asyncio
    async def test_delete_identity_credentials_success(
        self,
        concrete_service: KratosIdentityGenericService[MockIdentityObject, MockSessionObject],
        identity_id: KratosIdentityId,
        credentials_type: AuthenticationMethodEnum,
        identifier: str | None,
    ) -> None:
        """Test successful delete_identity_credentials scenarios.

        Args:
            concrete_service: Concrete service fixture.
            identity_id (KratosIdentityId): Identity ID fixture.
            credentials_type (AuthenticationMethodEnum): Credentials type.
            identifier (str | None): Identifier.
        """
        service = concrete_service

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.delete = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        service._kratos_admin_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
            return_value=mock_acquire_client_session(mock_session)
        )
        await service.delete_identity_credentials(
            identity_id=identity_id,
            credentials_type=credentials_type,
            identifier=identifier,
        )

        # Verify delete was called with correct params
        call_kwargs = mock_session.delete.call_args[1]
        assert call_kwargs["url"] == f"{service.IDENTITY_ENDPOINT}/{identity_id}/credentials"
        if identifier is not None:
            assert call_kwargs["params"]["identifier"] == identifier
        else:
            assert "params" not in call_kwargs or "identifier" not in call_kwargs.get("params", {})

    @pytest.mark.parametrize(
        "credentials_type,identifier,expected_error",
        [
            (AuthenticationMethodEnum.PASSWORD, "test_identifier", "Identifier is only supported"),
            (AuthenticationMethodEnum.TOTP, "test_identifier", "Identifier is only supported"),
            (AuthenticationMethodEnum.OIDC, None, "Identifier is mandatory"),
            (AuthenticationMethodEnum.SAML, None, "Identifier is mandatory"),
        ],
    )
    @pytest.mark.asyncio
    async def test_delete_identity_credentials_validation_errors(
        self,
        concrete_service: KratosIdentityGenericService[MockIdentityObject, MockSessionObject],
        identity_id: KratosIdentityId,
        credentials_type: AuthenticationMethodEnum,
        identifier: str | None,
        expected_error: str,
    ) -> None:
        """Test delete_identity_credentials validation error scenarios.

        Args:
            concrete_service: Concrete service fixture.
            identity_id (KratosIdentityId): Identity ID fixture.
            credentials_type (AuthenticationMethodEnum): Credentials type.
            identifier (str | None): Identifier.
            expected_error (str): Expected error message.
        """
        service = concrete_service

        with pytest.raises(ValueError, match=expected_error):
            await service.delete_identity_credentials(
                identity_id=identity_id,
                credentials_type=credentials_type,
                identifier=identifier,
            )

    @pytest.mark.asyncio
    async def test_delete_identity_credentials_errors(
        self,
        concrete_service: KratosIdentityGenericService[MockIdentityObject, MockSessionObject],
        identity_id: KratosIdentityId,
    ) -> None:
        """Test delete_identity_credentials error scenarios.

        Args:
            concrete_service: Concrete service fixture.
            identity_id (KratosIdentityId): Identity ID fixture.
        """
        service = concrete_service

        error = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=404,
            message="Not Found",
        )

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock(side_effect=error)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.delete = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        service._kratos_admin_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
            return_value=mock_acquire_client_session(mock_session)
        )
        with pytest.raises(KratosOperationError) as exc_info:
            await service.delete_identity_credentials(
                identity_id=identity_id,
                credentials_type=AuthenticationMethodEnum.PASSWORD,
            )

        assert "Failed to delete the credentials" in str(exc_info.value)
        assert exc_info.value.__cause__ == error

    @pytest.mark.asyncio
    async def test_delete_identity_sessions_success(
        self,
        concrete_service: KratosIdentityGenericService[MockIdentityObject, MockSessionObject],
        identity_id: KratosIdentityId,
    ) -> None:
        """Test successful delete_identity_sessions call.

        Args:
            concrete_service: Concrete service fixture.
            identity_id (KratosIdentityId): Identity ID fixture.
        """
        service = concrete_service

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.delete = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        service._kratos_admin_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
            return_value=mock_acquire_client_session(mock_session)
        )
        await service.delete_identity_sessions(identity_id=identity_id)

        mock_session.delete.assert_called_once_with(url=f"{service.IDENTITY_ENDPOINT}/{identity_id}/sessions")

    @pytest.mark.asyncio
    async def test_delete_identity_sessions_errors(
        self,
        concrete_service: KratosIdentityGenericService[MockIdentityObject, MockSessionObject],
        identity_id: KratosIdentityId,
    ) -> None:
        """Test delete_identity_sessions error scenarios.

        Args:
            concrete_service: Concrete service fixture.
            identity_id (KratosIdentityId): Identity ID fixture.
        """
        service = concrete_service

        error = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=404,
            message="Not Found",
        )

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock(side_effect=error)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.delete = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        service._kratos_admin_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
            return_value=mock_acquire_client_session(mock_session)
        )
        with pytest.raises(KratosOperationError) as exc_info:
            await service.delete_identity_sessions(identity_id=identity_id)

            assert "Failed to delete the sessions" in str(exc_info.value)
            assert exc_info.value.__cause__ == error

    @pytest.mark.asyncio
    async def test_delete_identity_success(
        self,
        concrete_service: KratosIdentityGenericService[MockIdentityObject, MockSessionObject],
        identity_id: KratosIdentityId,
    ) -> None:
        """Test successful delete_identity call.

        Args:
            concrete_service: Concrete service fixture.
            identity_id (KratosIdentityId): Identity ID fixture.
        """
        service = concrete_service

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.delete = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        service._kratos_admin_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
            return_value=mock_acquire_client_session(mock_session)
        )
        await service.delete_identity(identity_id=identity_id)

        mock_session.delete.assert_called_once_with(url=f"{service.IDENTITY_ENDPOINT}/{identity_id}")

    @pytest.mark.asyncio
    async def test_delete_identity_errors(
        self,
        concrete_service: KratosIdentityGenericService[MockIdentityObject, MockSessionObject],
        identity_id: KratosIdentityId,
    ) -> None:
        """Test delete_identity error scenarios.

        Args:
            concrete_service: Concrete service fixture.
            identity_id (KratosIdentityId): Identity ID fixture.
        """
        service = concrete_service

        error = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=404,
            message="Not Found",
        )

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock(side_effect=error)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.delete = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        service._kratos_admin_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
            return_value=mock_acquire_client_session(mock_session)
        )
        with pytest.raises(KratosOperationError) as exc_info:
            await service.delete_identity(identity_id=identity_id)

        assert "Failed to delete the Kratos identity" in str(exc_info.value)
        assert exc_info.value.__cause__ == error

    @pytest.mark.parametrize(
        "active,page_size,page_token,link_header,expected_next_token",
        [
            (True, 250, None, None, None),
            (False, 100, None, None, None),
            (True, 50, "token123", None, None),
            (
                True,
                250,
                None,
                '</admin/identities/123/sessions?page_size=250&active=true&page_token=next123>; rel="next"',
                "next123",
            ),
            (
                False,
                100,
                "token123",
                '</admin/identities/123/sessions?page_size=100&active=false&page_token=next456>; rel="next"',
                "next456",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_list_sessions_success(  # noqa: PLR0913
        self,
        concrete_service: KratosIdentityGenericService[MockIdentityObject, MockSessionObject],
        identity_id: KratosIdentityId,
        active: bool,
        page_size: int,
        page_token: str | None,
        link_header: str | None,
        expected_next_token: str | None,
    ) -> None:
        """Test successful list_sessions scenarios.

        Args:
            concrete_service: Concrete service fixture.
            identity_id (KratosIdentityId): Identity ID fixture.
            active (bool): Active filter.
            page_size (int): Page size.
            page_token (str | None): Page token.
            link_header (str | None): Link header.
            expected_next_token (str | None): Expected next page token.
        """
        service = concrete_service

        sessions_data = [
            {
                "id": str(uuid.uuid4()),
                "active": True,
                "data": {"test": "value1"},
            },
            {
                "id": str(uuid.uuid4()),
                "active": True,
                "data": {"test": "value2"},
            },
        ]

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=sessions_data)
        mock_response.headers = {"Link": link_header} if link_header else {}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        service._kratos_admin_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
            return_value=mock_acquire_client_session(mock_session)
        )
        sessions, next_token = await service.list_sessions(
            identity_id=identity_id,
            active=active,
            page_size=page_size,
            page_token=page_token,
        )

        assert len(sessions) == len(sessions_data)
        assert next_token == expected_next_token

        # Verify query parameters
        call_kwargs = mock_session.get.call_args[1]
        assert call_kwargs["url"] == f"{service.IDENTITY_ENDPOINT}/{identity_id}/sessions"
        assert call_kwargs["params"]["page_size"] == str(page_size)
        assert call_kwargs["params"]["active"] == str(active)
        if page_token is not None:
            assert call_kwargs["params"]["page_token"] == page_token

    @pytest.mark.parametrize(
        "exception_class,exception_kwargs",
        [
            (aiohttp.ClientResponseError, {"status": 404, "message": "Not Found"}),
            (json.JSONDecodeError, {"msg": "Invalid JSON", "doc": "", "pos": 0}),
            (ValidationError, {}),
        ],
    )
    @pytest.mark.asyncio
    async def test_list_sessions_errors(
        self,
        concrete_service: KratosIdentityGenericService[MockIdentityObject, MockSessionObject],
        identity_id: KratosIdentityId,
        exception_class: type[Exception],
        exception_kwargs: dict[str, Any],
    ) -> None:
        """Test list_sessions error scenarios.

        Args:
            concrete_service: Concrete service fixture.
            identity_id (KratosIdentityId): Identity ID fixture.
            exception_class (type[Exception]): Exception class to raise.
            exception_kwargs (dict[str, Any]): Exception kwargs.
        """
        service = concrete_service

        if exception_class == aiohttp.ClientResponseError:
            error = aiohttp.ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=exception_kwargs["status"],
                message=exception_kwargs["message"],
            )
        elif exception_class == json.JSONDecodeError:
            error = json.JSONDecodeError(
                msg=exception_kwargs["msg"],
                doc=exception_kwargs["doc"],
                pos=exception_kwargs["pos"],
            )
        else:  # ValidationError
            # Create a ValidationError by trying to validate invalid data
            try:
                MockSessionObject.model_validate({"invalid": "data"})
            except ValidationError as e:
                error = e
            else:
                # This should never happen, but satisfy type checker
                error = ValidationError.from_exception_data("TestModel", [])

        mock_response = AsyncMock()
        if exception_class == aiohttp.ClientResponseError:
            mock_response.raise_for_status = MagicMock(side_effect=error)
        else:
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(side_effect=error)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        service._kratos_admin_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
            return_value=mock_acquire_client_session(mock_session)
        )
        with pytest.raises(KratosOperationError) as exc_info:
            await service.list_sessions(identity_id=identity_id)

            assert "Failed to list the sessions" in str(exc_info.value)
            assert exc_info.value.__cause__ == error

    @pytest.mark.asyncio
    async def test_create_recovery_link_success(
        self,
        concrete_service: KratosIdentityGenericService[MockIdentityObject, MockSessionObject],
        identity_id: KratosIdentityId,
    ) -> None:
        """Test successful create_recovery_link call.

        Args:
            concrete_service: Concrete service fixture.
            identity_id (KratosIdentityId): Identity ID fixture.
        """
        service = concrete_service

        expires_in = datetime.timedelta(hours=1)
        recovery_link_value = "https://kratos.example.com/recovery?token=abc123"
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=recovery_link_value)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        service._kratos_admin_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
            return_value=mock_acquire_client_session(mock_session)
        )
        result: KratosRecoveryLink = await service.create_recovery_link(
            identity_id=identity_id,
            expires_in=expires_in,
        )

        assert result == KratosRecoveryLink(recovery_link_value)

        # Verify post was called with correct params
        call_kwargs = mock_session.post.call_args[1]
        assert call_kwargs["url"] == f"{service.ADMIN_ENDPOINT}/recovery/link"
        assert call_kwargs["json"]["expires_in"] == f"{int(expires_in.total_seconds())}s"
        assert call_kwargs["json"]["identity_id"] == str(identity_id)

    @pytest.mark.parametrize(
        "exception_class,exception_kwargs",
        [
            (aiohttp.ClientResponseError, {"status": 404, "message": "Not Found"}),
            (aiohttp.ClientResponseError, {"status": 500, "message": "Internal Server Error"}),
            (json.JSONDecodeError, {"msg": "Invalid JSON", "doc": "", "pos": 0}),
        ],
    )
    @pytest.mark.asyncio
    async def test_create_recovery_link_errors(
        self,
        concrete_service: KratosIdentityGenericService[MockIdentityObject, MockSessionObject],
        identity_id: KratosIdentityId,
        exception_class: type[Exception],
        exception_kwargs: dict[str, Any],
    ) -> None:
        """Test create_recovery_link error scenarios.

        Args:
            concrete_service: Concrete service fixture.
            identity_id (KratosIdentityId): Identity ID fixture.
            exception_class (type[Exception]): Exception class to raise.
            exception_kwargs (dict[str, Any]): Exception kwargs.
        """
        service = concrete_service

        expires_in = datetime.timedelta(hours=1)

        if exception_class == aiohttp.ClientResponseError:
            error = aiohttp.ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=exception_kwargs["status"],
                message=exception_kwargs["message"],
            )
        elif exception_class == json.JSONDecodeError:
            error = json.JSONDecodeError(
                msg=exception_kwargs["msg"],
                doc=exception_kwargs["doc"],
                pos=exception_kwargs["pos"],
            )
        else:  # ValidationError
            # Create a ValidationError by trying to validate invalid data
            try:
                MockSessionObject.model_validate({"invalid": "data"})
            except ValidationError as e:
                error = e
            else:
                # This should never happen, but satisfy type checker
                error = ValidationError.from_exception_data("TestModel", [])

        mock_response = AsyncMock()
        if exception_class == aiohttp.ClientResponseError:
            mock_response.raise_for_status = MagicMock(side_effect=error)
        else:
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(side_effect=error)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        service._kratos_admin_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
            return_value=mock_acquire_client_session(mock_session)
        )
        with pytest.raises(KratosOperationError) as exc_info:
            await service.create_recovery_link(
                identity_id=identity_id,
                expires_in=expires_in,
            )

            assert "Failed to create the recovery link" in str(exc_info.value)
            assert exc_info.value.__cause__ == error
            # Check that identity_id and expires_in are in exception context
            assert hasattr(exc_info.value, "identity_id") or str(identity_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_recovery_link_expires_in_conversion(
        self,
        concrete_service: KratosIdentityGenericService[MockIdentityObject, MockSessionObject],
        identity_id: KratosIdentityId,
    ) -> None:
        """Test that expires_in is correctly converted to seconds string.

        Args:
            concrete_service: Concrete service fixture.
            identity_id (KratosIdentityId): Identity ID fixture.
        """
        service = concrete_service

        # Test with different timedelta values
        test_cases = [
            (datetime.timedelta(seconds=30), "30s"),
            (datetime.timedelta(minutes=5), "300s"),
            (datetime.timedelta(hours=2), "7200s"),
            (datetime.timedelta(days=1), "86400s"),
        ]

        for expires_in, expected_seconds_str in test_cases:
            recovery_link_value = "https://kratos.example.com/recovery?token=abc123"
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value=recovery_link_value)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            service._kratos_admin_http_resource.acquire_client_session = MagicMock(  # type: ignore[method-assign]
                return_value=mock_acquire_client_session(mock_session)
            )
            await service.create_recovery_link(
                identity_id=identity_id,
                expires_in=expires_in,
            )

            # Verify expires_in was converted correctly
            call_kwargs = mock_session.post.call_args[1]
            assert call_kwargs["json"]["expires_in"] == expected_seconds_str
