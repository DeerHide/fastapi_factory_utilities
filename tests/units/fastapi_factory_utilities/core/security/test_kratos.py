"""Unit tests for the Kratos session authentication."""

from http import HTTPStatus
from typing import TypeAlias
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Request

from fastapi_factory_utilities.core.security.kratos import KratosSessionAuthenticationService
from fastapi_factory_utilities.core.services.kratos import (
    KratosGenericWhoamiService,
    KratosIdentityObject,
    KratosOperationError,
    KratosSessionInvalidError,
    KratosSessionObject,
    KratosTraitsObject,
    MetadataObject,
)

# Type alias for concrete session object used in tests
ConcreteKratosSessionObject: TypeAlias = KratosSessionObject[
    KratosIdentityObject[KratosTraitsObject, MetadataObject, MetadataObject]
]


class TestKratosSessionAuthenticationService:
    """Test cases for KratosSessionAuthenticationService class."""

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        """Create a mock request with cookies.

        Returns:
            MagicMock: A mock request object.
        """
        request = MagicMock(spec=Request)
        request.cookies = {}
        return request

    @pytest.fixture
    def mock_kratos_service(self) -> AsyncMock:
        """Create a mock KratosGenericWhoamiService.

        Returns:
            AsyncMock: A mock KratosGenericWhoamiService object.
        """
        return AsyncMock(spec=KratosGenericWhoamiService)

    @pytest.fixture
    def session_auth(
        self, mock_kratos_service: AsyncMock
    ) -> KratosSessionAuthenticationService[ConcreteKratosSessionObject]:
        """Create a KratosSessionAuthenticationService instance.

        Args:
            mock_kratos_service (AsyncMock): Mock KratosGenericWhoamiService object.

        Returns:
            KratosSessionAuthenticationService[ConcreteKratosSessionObject]: A
                KratosSessionAuthenticationService instance.
        """
        return KratosSessionAuthenticationService(kratos_service=mock_kratos_service)

    def test_init_with_default_values(self, mock_kratos_service: AsyncMock) -> None:
        """Test initialization with default values.

        Args:
            mock_kratos_service (AsyncMock): Mock KratosGenericWhoamiService object.
        """
        auth = KratosSessionAuthenticationService(kratos_service=mock_kratos_service)
        assert auth._cookie_name == "ory_kratos_session"  # pylint: disable=protected-access
        assert auth._raise_exception is True  # pylint: disable=protected-access

    def test_init_with_custom_values(self, mock_kratos_service: AsyncMock) -> None:
        """Test initialization with custom values.

        Args:
            mock_kratos_service (AsyncMock): Mock KratosGenericWhoamiService object.
        """
        auth = KratosSessionAuthenticationService(
            kratos_service=mock_kratos_service, cookie_name="custom_cookie", raise_exception=False
        )
        assert auth._cookie_name == "custom_cookie"  # pylint: disable=protected-access
        assert auth._raise_exception is False  # pylint: disable=protected-access

    def test_extract_cookie_when_cookie_exists(self, mock_request: MagicMock, mock_kratos_service: AsyncMock) -> None:
        """Test cookie extraction when cookie exists.

        Args:
            mock_request (MagicMock): Mock request object.
            mock_kratos_service (AsyncMock): Mock KratosGenericWhoamiService object.
        """
        mock_request.cookies = {"ory_kratos_session": "test_cookie"}
        auth = KratosSessionAuthenticationService(kratos_service=mock_kratos_service)
        cookie = auth._extract_cookie(mock_request)  # pylint: disable=protected-access
        assert cookie == "test_cookie"

    def test_extract_cookie_when_cookie_missing(self, mock_request: MagicMock, mock_kratos_service: AsyncMock) -> None:
        """Test cookie extraction when cookie is missing.

        Args:
            mock_request (MagicMock): Mock request object.
            mock_kratos_service (AsyncMock): Mock KratosGenericWhoamiService object.
        """
        auth = KratosSessionAuthenticationService(kratos_service=mock_kratos_service)
        cookie = auth._extract_cookie(mock_request)  # pylint: disable=protected-access
        assert cookie is None

    @pytest.mark.asyncio
    async def test_authenticate_with_valid_session(
        self,
        mock_request: MagicMock,
        mock_kratos_service: AsyncMock,
        session_auth: KratosSessionAuthenticationService[ConcreteKratosSessionObject],
    ) -> None:
        """Test successful session validation.

        Args:
            mock_request (MagicMock): Mock request object.
            mock_kratos_service (AsyncMock): Mock KratosGenericWhoamiService object.
            session_auth (KratosSessionAuthenticationService): KratosSessionAuthenticationService instance.
        """
        mock_request.cookies = {"ory_kratos_session": "valid_cookie"}
        mock_session = MagicMock(spec=KratosSessionObject)
        mock_kratos_service.whoami.return_value = mock_session

        await session_auth.authenticate(mock_request)

        assert session_auth.session == mock_session
        mock_kratos_service.whoami.assert_called_once_with(cookie_value="valid_cookie")

    @pytest.mark.asyncio
    async def test_authenticate_with_missing_cookie_raise_exception(
        self,
        mock_request: MagicMock,
        session_auth: KratosSessionAuthenticationService[ConcreteKratosSessionObject],
    ) -> None:
        """Test behavior when cookie is missing and raise_exception is True.

        Args:
            mock_request (MagicMock): Mock request object.
            session_auth (KratosSessionAuthenticationService): KratosSessionAuthenticationService instance.
        """
        with pytest.raises(HTTPException) as exc_info:
            await session_auth.authenticate(mock_request)

        assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED
        assert exc_info.value.detail == "Missing Credentials"

    @pytest.mark.asyncio
    async def test_authenticate_with_missing_cookie_no_raise(
        self,
        mock_request: MagicMock,
        mock_kratos_service: AsyncMock,
    ) -> None:
        """Test behavior when cookie is missing and raise_exception is False.

        Args:
            mock_request (MagicMock): Mock request object.
            mock_kratos_service (AsyncMock): Mock KratosGenericWhoamiService object.
        """
        auth = KratosSessionAuthenticationService(kratos_service=mock_kratos_service, raise_exception=False)
        await auth.authenticate(mock_request)

        assert auth.has_errors() is True
        assert len(auth._errors) == 1  # pylint: disable=protected-access
        assert isinstance(auth._errors[0], HTTPException)  # pylint: disable=protected-access
        assert auth._errors[0].status_code == HTTPStatus.UNAUTHORIZED  # pylint: disable=protected-access
        assert auth._errors[0].detail == "Missing Credentials"  # pylint: disable=protected-access

    @pytest.mark.asyncio
    async def test_authenticate_with_invalid_session_raise_exception(
        self,
        mock_request: MagicMock,
        mock_kratos_service: AsyncMock,
        session_auth: KratosSessionAuthenticationService[ConcreteKratosSessionObject],
    ) -> None:
        """Test behavior when session is invalid and raise_exception is True.

        Args:
            mock_request (MagicMock): Mock request object.
            mock_kratos_service (AsyncMock): Mock KratosGenericWhoamiService object.
            session_auth (KratosSessionAuthenticationService): KratosSessionAuthenticationService instance.
        """
        mock_request.cookies = {"ory_kratos_session": "invalid_cookie"}
        mock_kratos_service.whoami.side_effect = KratosSessionInvalidError()

        with pytest.raises(HTTPException) as exc_info:
            await session_auth.authenticate(mock_request)

        assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED
        assert exc_info.value.detail == "Invalid Credentials"

    @pytest.mark.asyncio
    async def test_authenticate_with_invalid_session_no_raise(
        self,
        mock_request: MagicMock,
        mock_kratos_service: AsyncMock,
    ) -> None:
        """Test behavior when session is invalid and raise_exception is False.

        Args:
            mock_request (MagicMock): Mock request object.
            mock_kratos_service (AsyncMock): Mock KratosGenericWhoamiService object.
        """
        auth = KratosSessionAuthenticationService(kratos_service=mock_kratos_service, raise_exception=False)
        mock_request.cookies = {"ory_kratos_session": "invalid_cookie"}
        mock_kratos_service.whoami.side_effect = KratosSessionInvalidError()

        await auth.authenticate(mock_request)

        assert auth.has_errors() is True
        assert len(auth._errors) == 1  # pylint: disable=protected-access
        assert isinstance(auth._errors[0], HTTPException)  # pylint: disable=protected-access
        assert auth._errors[0].status_code == HTTPStatus.UNAUTHORIZED  # pylint: disable=protected-access
        assert auth._errors[0].detail == "Invalid Credentials"  # pylint: disable=protected-access

    @pytest.mark.asyncio
    async def test_authenticate_with_operation_error_raise_exception(
        self,
        mock_request: MagicMock,
        mock_kratos_service: AsyncMock,
        session_auth: KratosSessionAuthenticationService[ConcreteKratosSessionObject],
    ) -> None:
        """Test behavior when operation error occurs and raise_exception is True.

        Args:
            mock_request (MagicMock): Mock request object.
            mock_kratos_service (AsyncMock): Mock KratosGenericWhoamiService object.
            session_auth (KratosSessionAuthenticationService): KratosSessionAuthenticationService instance.
        """
        mock_request.cookies = {"ory_kratos_session": "valid_cookie"}
        mock_kratos_service.whoami.side_effect = KratosOperationError()

        with pytest.raises(HTTPException) as exc_info:
            await session_auth.authenticate(mock_request)

        assert exc_info.value.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert exc_info.value.detail == "Internal Server Error"

    @pytest.mark.asyncio
    async def test_authenticate_with_operation_error_no_raise(
        self,
        mock_request: MagicMock,
        mock_kratos_service: AsyncMock,
    ) -> None:
        """Test behavior when operation error occurs and raise_exception is False.

        Args:
            mock_request (MagicMock): Mock request object.
            mock_kratos_service (AsyncMock): Mock KratosGenericWhoamiService object.
        """
        auth = KratosSessionAuthenticationService(kratos_service=mock_kratos_service, raise_exception=False)
        mock_request.cookies = {"ory_kratos_session": "valid_cookie"}
        mock_kratos_service.whoami.side_effect = KratosOperationError()

        await auth.authenticate(mock_request)

        assert auth.has_errors() is True
        assert len(auth._errors) == 1  # pylint: disable=protected-access
        assert isinstance(auth._errors[0], HTTPException)  # pylint: disable=protected-access
        assert auth._errors[0].status_code == HTTPStatus.INTERNAL_SERVER_ERROR  # pylint: disable=protected-access
        assert auth._errors[0].detail == "Internal Server Error"  # pylint: disable=protected-access
