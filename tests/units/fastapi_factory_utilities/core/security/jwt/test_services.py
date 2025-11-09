"""Unit tests for the JWT authentication services."""

import datetime
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Request

from fastapi_factory_utilities.core.security.jwt.configs import JWTBearerAuthenticationConfig
from fastapi_factory_utilities.core.security.jwt.decoders import (
    JWTBearerTokenDecoder,
    JWTBearerTokenDecoderAbstract,
)
from fastapi_factory_utilities.core.security.jwt.exceptions import (
    InvalidJWTError,
    InvalidJWTPayploadError,
    MissingJWTCredentialsError,
    NotVerifiedJWTError,
)
from fastapi_factory_utilities.core.security.jwt.objects import JWTPayload
from fastapi_factory_utilities.core.security.jwt.services import (
    JWTAuthenticationService,
    JWTAuthenticationServiceAbstract,
)
from fastapi_factory_utilities.core.security.jwt.stores import JWKStoreAbstract
from fastapi_factory_utilities.core.security.jwt.types import JWTToken
from fastapi_factory_utilities.core.security.jwt.verifiers import (
    JWTNoneVerifier,
    JWTVerifierAbstract,
)


class TestJWTAuthenticationServiceAbstract:  # pylint: disable=protected-access
    """Various tests for the JWTAuthenticationServiceAbstract class."""

    @pytest.fixture
    def jwt_config(self) -> JWTBearerAuthenticationConfig:
        """Create a JWT bearer authentication config.

        Returns:
            JWTBearerAuthenticationConfig: A JWT bearer authentication config.
        """
        return JWTBearerAuthenticationConfig(
            audience="test_audience",
            authorized_algorithms=["RS256"],
        )

    @pytest.fixture
    def mock_verifier(self) -> MagicMock:
        """Create a mock JWT verifier.

        Returns:
            MagicMock: A mock JWT verifier.
        """
        verifier = MagicMock(spec=JWTVerifierAbstract)
        verifier.verify = AsyncMock(return_value=None)
        return verifier

    @pytest.fixture
    def mock_decoder(self) -> MagicMock:
        """Create a mock JWT decoder.

        Returns:
            MagicMock: A mock JWT decoder.
        """
        decoder = MagicMock(spec=JWTBearerTokenDecoderAbstract)
        return decoder

    @pytest.fixture
    def jwt_payload(self) -> JWTPayload:
        """Create a JWT bearer payload.

        Returns:
            JWTPayload: A JWT bearer payload.
        """
        now = datetime.datetime.now(tz=datetime.UTC)
        exp = now + datetime.timedelta(hours=1)
        nbf = now - datetime.timedelta(minutes=5)

        return JWTPayload(  # type: ignore[arg-type]
            scope="read write",
            aud="api1 api2",
            iss="https://example.com",
            exp=int(exp.timestamp()),
            iat=int(now.timestamp()),
            nbf=int(nbf.timestamp()),
            sub="user123",
        )

    @pytest.fixture
    def concrete_service(
        self,
        jwt_config: JWTBearerAuthenticationConfig,
        mock_verifier: MagicMock,
        mock_decoder: MagicMock,
    ) -> JWTAuthenticationServiceAbstract[JWTPayload]:
        """Create a concrete implementation of JWTAuthenticationServiceAbstract.

        Args:
            jwt_config (JWTBearerAuthenticationConfig): The JWT config.
            mock_verifier (MagicMock): The mock verifier.
            mock_decoder (MagicMock): The mock decoder.

        Returns:
            JWTAuthenticationServiceAbstract[JWTPayload]: A concrete service instance.
        """

        class ConcreteService(JWTAuthenticationServiceAbstract[JWTPayload]):
            """Concrete implementation for testing."""

            pass

        return ConcreteService(
            jwt_bearer_authentication_config=jwt_config,
            jwt_verifier=mock_verifier,
            jwt_decoder=mock_decoder,
        )

    def test_abstract_class_cannot_be_instantiated(self) -> None:
        """Test that the abstract class cannot be instantiated directly."""
        with pytest.raises(TypeError):
            # pylint: disable=abstract-class-instantiated,no-value-for-parameter
            JWTAuthenticationServiceAbstract()  # type: ignore[abstract]

    def test_extract_authorization_header_from_request_success(self) -> None:
        """Test extracting authorization header from request successfully."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test.token.here"}

        result = JWTAuthenticationServiceAbstract.extract_authorization_header_from_request(request=request)

        assert result == "Bearer test.token.here"

    def test_extract_authorization_header_from_request_missing(self) -> None:
        """Test extracting authorization header when it's missing."""
        request = MagicMock(spec=Request)
        request.headers = {}

        with pytest.raises(MissingJWTCredentialsError) as exc_info:
            JWTAuthenticationServiceAbstract.extract_authorization_header_from_request(request=request)

        assert "Missing Credentials" in str(exc_info.value)

    def test_extract_authorization_header_from_request_none(self) -> None:
        """Test extracting authorization header when it's None."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": None}

        with pytest.raises(MissingJWTCredentialsError) as exc_info:
            JWTAuthenticationServiceAbstract.extract_authorization_header_from_request(request=request)

        assert "Missing Credentials" in str(exc_info.value)

    def test_extract_bearer_token_from_authorization_header_success(self) -> None:
        """Test extracting bearer token from authorization header successfully."""
        authorization_header = "Bearer test.token.here"

        result = JWTAuthenticationServiceAbstract.extract_bearer_token_from_authorization_header(
            authorization_header=authorization_header
        )

        assert result == JWTToken("test.token.here")
        assert str(result) == "test.token.here"

    def test_extract_bearer_token_from_authorization_header_invalid_prefix(self) -> None:
        """Test extracting bearer token when prefix is invalid."""
        authorization_header = "Basic test.token.here"

        with pytest.raises(InvalidJWTError) as exc_info:
            JWTAuthenticationServiceAbstract.extract_bearer_token_from_authorization_header(
                authorization_header=authorization_header
            )

        assert "Invalid Credentials" in str(exc_info.value)

    def test_extract_bearer_token_from_authorization_header_no_space(self) -> None:
        """Test extracting bearer token when there's no space after Bearer."""
        authorization_header = "Bearertest.token.here"

        with pytest.raises(InvalidJWTError) as exc_info:
            JWTAuthenticationServiceAbstract.extract_bearer_token_from_authorization_header(
                authorization_header=authorization_header
            )

        assert "Invalid Credentials" in str(exc_info.value)

    def test_extract_bearer_token_from_authorization_header_empty_token(self) -> None:
        """Test extracting bearer token when token is empty."""
        authorization_header = "Bearer "

        result = JWTAuthenticationServiceAbstract.extract_bearer_token_from_authorization_header(
            authorization_header=authorization_header
        )

        assert result == JWTToken("")
        assert str(result) == ""

    def test_has_errors_initially_false(self, concrete_service: JWTAuthenticationServiceAbstract[JWTPayload]) -> None:
        """Test that has_errors returns False initially.

        Args:
            concrete_service (JWTAuthenticationServiceAbstract[JWTPayload]): The service instance.
        """
        assert concrete_service.has_errors() is False

    def test_has_errors_after_error(self, concrete_service: JWTAuthenticationServiceAbstract[JWTPayload]) -> None:
        """Test that has_errors returns True after an error is added.

        Args:
            concrete_service (JWTAuthenticationServiceAbstract[JWTPayload]): The service instance.
        """
        concrete_service._errors.append(InvalidJWTError("Test error"))  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert concrete_service.has_errors() is True

    def test_payload_initially_none(self, concrete_service: JWTAuthenticationServiceAbstract[JWTPayload]) -> None:
        """Test that payload property returns None initially.

        Args:
            concrete_service (JWTAuthenticationServiceAbstract[JWTPayload]): The service instance.
        """
        assert concrete_service.payload is None

    def test_payload_after_authentication(
        self,
        concrete_service: JWTAuthenticationServiceAbstract[JWTPayload],
        jwt_payload: JWTPayload,
    ) -> None:
        """Test that payload property returns the payload after authentication.

        Args:
            concrete_service (JWTAuthenticationServiceAbstract[JWTPayload]): The service instance.
            jwt_payload (JWTPayload): The JWT payload.
        """
        concrete_service._jwt_payload = jwt_payload  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert concrete_service.payload == jwt_payload

    @pytest.mark.asyncio
    async def test_authenticate_success(
        self,
        concrete_service: JWTAuthenticationServiceAbstract[JWTPayload],
        jwt_payload: JWTPayload,
    ) -> None:
        """Test successful authentication.

        Args:
            concrete_service (JWTAuthenticationServiceAbstract[JWTPayload]): The service instance.
            jwt_payload (JWTPayload): The JWT payload.
        """
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test.token.here"}

        concrete_service._jwt_decoder.decode_payload = AsyncMock(return_value=jwt_payload)  # type: ignore[assignment]

        await concrete_service.authenticate(request=request)

        assert concrete_service.payload == jwt_payload
        assert concrete_service.has_errors() is False
        concrete_service._jwt_decoder.decode_payload.assert_called_once()  # type: ignore[attr-defined]
        concrete_service._jwt_verifier.verify.assert_called_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_authenticate_missing_credentials_raises(
        self,
        concrete_service: JWTAuthenticationServiceAbstract[JWTPayload],
    ) -> None:
        """Test authentication raises exception when credentials are missing.

        Args:
            concrete_service (JWTAuthenticationServiceAbstract[JWTPayload]): The service instance.
        """
        request = MagicMock(spec=Request)
        request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            await concrete_service.authenticate(request=request)

        assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED
        assert "Missing Credentials" in str(exc_info.value.detail)
        assert concrete_service.payload is None
        assert concrete_service.has_errors() is False

    @pytest.mark.asyncio
    async def test_authenticate_missing_credentials_no_raise(
        self,
        jwt_config: JWTBearerAuthenticationConfig,
        mock_verifier: MagicMock,
        mock_decoder: MagicMock,
    ) -> None:
        """Test authentication collects error when credentials are missing and raise_exception is False.

        Args:
            jwt_config (JWTBearerAuthenticationConfig): The JWT config.
            mock_verifier (MagicMock): The mock verifier.
            mock_decoder (MagicMock): The mock decoder.
        """

        class ConcreteService(JWTAuthenticationServiceAbstract[JWTPayload]):
            """Concrete implementation for testing."""

            pass

        service = ConcreteService(
            jwt_bearer_authentication_config=jwt_config,
            jwt_verifier=mock_verifier,
            jwt_decoder=mock_decoder,
            raise_exception=False,
        )

        request = MagicMock(spec=Request)
        request.headers = {}

        await service.authenticate(request=request)

        assert service.payload is None
        assert service.has_errors() is True
        assert len(service._errors) == 1  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert isinstance(service._errors[0], HTTPException)  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert service._errors[0].status_code == HTTPStatus.UNAUTHORIZED  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert "Missing Credentials" in str(service._errors[0].detail)  # type: ignore[attr-defined] # pylint: disable=protected-access

    @pytest.mark.asyncio
    async def test_authenticate_invalid_jwt_raises(
        self,
        concrete_service: JWTAuthenticationServiceAbstract[JWTPayload],
    ) -> None:
        """Test authentication raises exception when JWT is invalid.

        Args:
            concrete_service (JWTAuthenticationServiceAbstract[JWTPayload]): The service instance.
        """
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Basic test.token.here"}

        with pytest.raises(HTTPException) as exc_info:
            await concrete_service.authenticate(request=request)

        assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED
        assert "Invalid Credentials" in str(exc_info.value.detail)
        assert concrete_service.payload is None
        assert concrete_service.has_errors() is False

    @pytest.mark.asyncio
    async def test_authenticate_invalid_jwt_no_raise(
        self,
        jwt_config: JWTBearerAuthenticationConfig,
        mock_verifier: MagicMock,
        mock_decoder: MagicMock,
    ) -> None:
        """Test authentication collects error when JWT is invalid and raise_exception is False.

        Args:
            jwt_config (JWTBearerAuthenticationConfig): The JWT config.
            mock_verifier (MagicMock): The mock verifier.
            mock_decoder (MagicMock): The mock decoder.
        """

        class ConcreteService(JWTAuthenticationServiceAbstract[JWTPayload]):
            """Concrete implementation for testing."""

            pass

        service = ConcreteService(
            jwt_bearer_authentication_config=jwt_config,
            jwt_verifier=mock_verifier,
            jwt_decoder=mock_decoder,
            raise_exception=False,
        )

        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Basic test.token.here"}

        await service.authenticate(request=request)

        assert service.payload is None
        assert service.has_errors() is True
        assert len(service._errors) == 1  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert isinstance(service._errors[0], HTTPException)  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert service._errors[0].status_code == HTTPStatus.UNAUTHORIZED  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert "Invalid Credentials" in str(service._errors[0].detail)  # type: ignore[attr-defined] # pylint: disable=protected-access

    @pytest.mark.asyncio
    async def test_authenticate_invalid_payload_raises(
        self,
        concrete_service: JWTAuthenticationServiceAbstract[JWTPayload],
    ) -> None:
        """Test authentication raises exception when payload is invalid.

        Args:
            concrete_service (JWTAuthenticationServiceAbstract[JWTPayload]): The service instance.
        """
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test.token.here"}

        concrete_service._jwt_decoder.decode_payload = AsyncMock(  # type: ignore[assignment]
            side_effect=InvalidJWTPayploadError("Invalid payload")
        )

        with pytest.raises(HTTPException) as exc_info:
            await concrete_service.authenticate(request=request)

        assert exc_info.value.status_code == HTTPStatus.FORBIDDEN
        assert "Invalid payload" in str(exc_info.value.detail)
        assert concrete_service.payload is None
        assert concrete_service.has_errors() is False

    @pytest.mark.asyncio
    async def test_authenticate_invalid_payload_no_raise(
        self,
        jwt_config: JWTBearerAuthenticationConfig,
        mock_verifier: MagicMock,
        mock_decoder: MagicMock,
    ) -> None:
        """Test authentication collects error when payload is invalid and raise_exception is False.

        Args:
            jwt_config (JWTBearerAuthenticationConfig): The JWT config.
            mock_verifier (MagicMock): The mock verifier.
            mock_decoder (MagicMock): The mock decoder.
        """

        class ConcreteService(JWTAuthenticationServiceAbstract[JWTPayload]):
            """Concrete implementation for testing."""

            pass

        service = ConcreteService(
            jwt_bearer_authentication_config=jwt_config,
            jwt_verifier=mock_verifier,
            jwt_decoder=mock_decoder,
            raise_exception=False,
        )

        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test.token.here"}

        mock_decoder.decode_payload = AsyncMock(  # type: ignore[assignment]
            side_effect=InvalidJWTPayploadError("Invalid payload")
        )

        await service.authenticate(request=request)

        assert service.payload is None
        assert service.has_errors() is True
        assert len(service._errors) == 1  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert isinstance(service._errors[0], HTTPException)  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert service._errors[0].status_code == HTTPStatus.FORBIDDEN  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert "Invalid payload" in str(service._errors[0].detail)  # type: ignore[attr-defined] # pylint: disable=protected-access

    @pytest.mark.asyncio
    async def test_authenticate_not_verified_raises(
        self,
        concrete_service: JWTAuthenticationServiceAbstract[JWTPayload],
        jwt_payload: JWTPayload,
    ) -> None:
        """Test authentication raises exception when JWT is not verified.

        Args:
            concrete_service (JWTAuthenticationServiceAbstract[JWTPayload]): The service instance.
            jwt_payload (JWTPayload): The JWT payload.
        """
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test.token.here"}

        concrete_service._jwt_decoder.decode_payload = AsyncMock(return_value=jwt_payload)  # type: ignore[assignment]
        concrete_service._jwt_verifier.verify = AsyncMock(  # type: ignore[assignment]
            side_effect=NotVerifiedJWTError("Not verified")
        )

        with pytest.raises(HTTPException) as exc_info:
            await concrete_service.authenticate(request=request)

        assert exc_info.value.status_code == HTTPStatus.FORBIDDEN
        assert "Not verified" in str(exc_info.value.detail)
        assert concrete_service.payload == jwt_payload
        assert concrete_service.has_errors() is False

    @pytest.mark.asyncio
    async def test_authenticate_not_verified_no_raise(
        self,
        jwt_config: JWTBearerAuthenticationConfig,
        mock_verifier: MagicMock,
        mock_decoder: MagicMock,
        jwt_payload: JWTPayload,
    ) -> None:
        """Test authentication collects error when JWT is not verified and raise_exception is False.

        Args:
            jwt_config (JWTBearerAuthenticationConfig): The JWT config.
            mock_verifier (MagicMock): The mock verifier.
            mock_decoder (MagicMock): The mock decoder.
            jwt_payload (JWTPayload): The JWT payload.
        """

        class ConcreteService(JWTAuthenticationServiceAbstract[JWTPayload]):
            """Concrete implementation for testing."""

            pass

        service = ConcreteService(
            jwt_bearer_authentication_config=jwt_config,
            jwt_verifier=mock_verifier,
            jwt_decoder=mock_decoder,
            raise_exception=False,
        )

        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test.token.here"}

        mock_decoder.decode_payload = AsyncMock(return_value=jwt_payload)  # type: ignore[assignment]
        mock_verifier.verify = AsyncMock(side_effect=NotVerifiedJWTError("Not verified"))  # type: ignore[assignment]

        await service.authenticate(request=request)

        assert service.payload == jwt_payload
        assert service.has_errors() is True
        assert len(service._errors) == 1  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert isinstance(service._errors[0], HTTPException)  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert service._errors[0].status_code == HTTPStatus.FORBIDDEN  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert "Not verified" in str(service._errors[0].detail)  # type: ignore[attr-defined] # pylint: disable=protected-access

    @pytest.mark.asyncio
    async def test_authenticate_invalid_jwt_from_decoder_raises(
        self,
        concrete_service: JWTAuthenticationServiceAbstract[JWTPayload],
    ) -> None:
        """Test authentication raises exception when decoder raises InvalidJWTError.

        Args:
            concrete_service (JWTAuthenticationServiceAbstract[JWTPayload]): The service instance.
        """
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test.token.here"}

        concrete_service._jwt_decoder.decode_payload = AsyncMock(  # type: ignore[assignment]
            side_effect=InvalidJWTError("Invalid JWT")
        )

        with pytest.raises(HTTPException) as exc_info:
            await concrete_service.authenticate(request=request)

        assert exc_info.value.status_code == HTTPStatus.FORBIDDEN
        assert "Invalid JWT" in str(exc_info.value.detail)
        assert concrete_service.payload is None
        assert concrete_service.has_errors() is False

    @pytest.mark.asyncio
    async def test_authenticate_invalid_jwt_from_decoder_no_raise(
        self,
        jwt_config: JWTBearerAuthenticationConfig,
        mock_verifier: MagicMock,
        mock_decoder: MagicMock,
    ) -> None:
        """Test authentication collects error when decoder raises InvalidJWTError and raise_exception is False.

        Args:
            jwt_config (JWTBearerAuthenticationConfig): The JWT config.
            mock_verifier (MagicMock): The mock verifier.
            mock_decoder (MagicMock): The mock decoder.
        """

        class ConcreteService(JWTAuthenticationServiceAbstract[JWTPayload]):
            """Concrete implementation for testing."""

            pass

        service = ConcreteService(
            jwt_bearer_authentication_config=jwt_config,
            jwt_verifier=mock_verifier,
            jwt_decoder=mock_decoder,
            raise_exception=False,
        )

        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test.token.here"}

        mock_decoder.decode_payload = AsyncMock(side_effect=InvalidJWTError("Invalid JWT"))  # type: ignore[assignment]

        await service.authenticate(request=request)

        assert service.payload is None
        assert service.has_errors() is True
        assert len(service._errors) == 1  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert isinstance(service._errors[0], HTTPException)  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert service._errors[0].status_code == HTTPStatus.FORBIDDEN  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert "Invalid JWT" in str(service._errors[0].detail)  # type: ignore[attr-defined] # pylint: disable=protected-access

    @pytest.mark.asyncio
    async def test_authenticate_calls_decoder_with_correct_token(
        self,
        concrete_service: JWTAuthenticationServiceAbstract[JWTPayload],
        jwt_payload: JWTPayload,
    ) -> None:
        """Test that authenticate calls decoder with the correct token.

        Args:
            concrete_service (JWTAuthenticationServiceAbstract[JWTPayload]): The service instance.
            jwt_payload (JWTPayload): The JWT payload.
        """
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test.token.here"}

        concrete_service._jwt_decoder.decode_payload = AsyncMock(return_value=jwt_payload)  # type: ignore[assignment]

        await concrete_service.authenticate(request=request)

        concrete_service._jwt_decoder.decode_payload.assert_called_once()  # type: ignore[attr-defined]
        call_args = concrete_service._jwt_decoder.decode_payload.call_args  # type: ignore[attr-defined]
        assert call_args.kwargs["jwt_token"] == JWTToken("test.token.here")

    @pytest.mark.asyncio
    async def test_authenticate_calls_verifier_with_correct_parameters(
        self,
        concrete_service: JWTAuthenticationServiceAbstract[JWTPayload],
        jwt_payload: JWTPayload,
    ) -> None:
        """Test that authenticate calls verifier with correct token and payload.

        Args:
            concrete_service (JWTAuthenticationServiceAbstract[JWTPayload]): The service instance.
            jwt_payload (JWTPayload): The JWT payload.
        """
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test.token.here"}

        concrete_service._jwt_decoder.decode_payload = AsyncMock(return_value=jwt_payload)  # type: ignore[assignment]

        await concrete_service.authenticate(request=request)

        concrete_service._jwt_verifier.verify.assert_called_once()  # type: ignore[attr-defined]
        call_args = concrete_service._jwt_verifier.verify.call_args  # type: ignore[attr-defined]
        assert call_args.kwargs["jwt_token"] == JWTToken("test.token.here")
        assert call_args.kwargs["jwt_payload"] == jwt_payload


class TestJWTAuthenticationService:  # pylint: disable=protected-access
    """Various tests for the JWTAuthenticationService class."""

    @pytest.fixture
    def jwt_config(self) -> JWTBearerAuthenticationConfig:
        """Create a JWT bearer authentication config.

        Returns:
            JWTBearerAuthenticationConfig: A JWT bearer authentication config.
        """
        return JWTBearerAuthenticationConfig(
            audience="test_audience",
            authorized_algorithms=["RS256"],
        )

    @pytest.fixture
    def mock_jwks_store(self) -> MagicMock:
        """Create a mock JWKS store.

        Returns:
            MagicMock: A mock JWKStoreAbstract object.
        """
        store = MagicMock(spec=JWKStoreAbstract)
        return store

    @pytest.fixture
    def service(
        self,
        jwt_config: JWTBearerAuthenticationConfig,
        mock_jwks_store: MagicMock,
    ) -> JWTAuthenticationService:
        """Create a JWT authentication service.

        Args:
            jwt_config (JWTBearerAuthenticationConfig): The JWT config.
            mock_jwks_store (MagicMock): The mock JWKS store.

        Returns:
            JWTAuthenticationService: A JWT authentication service.
        """
        return JWTAuthenticationService(
            jwt_bearer_authentication_config=jwt_config,
            jwks_store=mock_jwks_store,
        )

    def test_can_be_instantiated(
        self,
        jwt_config: JWTBearerAuthenticationConfig,
        mock_jwks_store: MagicMock,
    ) -> None:
        """Test that JWTAuthenticationService can be instantiated.

        Args:
            jwt_config (JWTBearerAuthenticationConfig): The JWT config.
            mock_jwks_store (MagicMock): The mock JWKS store.
        """
        service = JWTAuthenticationService(
            jwt_bearer_authentication_config=jwt_config,
            jwks_store=mock_jwks_store,
        )
        assert isinstance(service, JWTAuthenticationService)
        assert isinstance(service, JWTAuthenticationServiceAbstract)

    def test_inherits_from_abstract_class(self, service: JWTAuthenticationService) -> None:
        """Test that JWTAuthenticationService inherits from JWTAuthenticationServiceAbstract.

        Args:
            service (JWTAuthenticationService): The service instance.
        """
        assert isinstance(service, JWTAuthenticationServiceAbstract)

    def test_initializes_with_none_verifier(self, service: JWTAuthenticationService) -> None:
        """Test that service initializes with JWTNoneVerifier.

        Args:
            service (JWTAuthenticationService): The service instance.
        """
        assert isinstance(service._jwt_verifier, JWTNoneVerifier)  # type: ignore[attr-defined] # pylint: disable=protected-access

    def test_initializes_with_decoder(
        self,
        service: JWTAuthenticationService,
        mock_jwks_store: MagicMock,
    ) -> None:
        """Test that service initializes with JWTBearerTokenDecoder.

        Args:
            service (JWTAuthenticationService): The service instance.
            mock_jwks_store (MagicMock): The mock JWKS store.
        """
        assert isinstance(service._jwt_decoder, JWTBearerTokenDecoder)  # type: ignore[attr-defined] # pylint: disable=protected-access
        assert service._jwt_decoder._jwks_store == mock_jwks_store  # type: ignore[attr-defined] # pylint: disable=protected-access

    def test_initializes_with_raise_exception_true_by_default(
        self,
        jwt_config: JWTBearerAuthenticationConfig,
        mock_jwks_store: MagicMock,
    ) -> None:
        """Test that service initializes with raise_exception=True by default.

        Args:
            jwt_config (JWTBearerAuthenticationConfig): The JWT config.
            mock_jwks_store (MagicMock): The mock JWKS store.
        """
        service = JWTAuthenticationService(
            jwt_bearer_authentication_config=jwt_config,
            jwks_store=mock_jwks_store,
        )
        assert service._raise_exception is True  # type: ignore[attr-defined] # pylint: disable=protected-access

    def test_initializes_with_raise_exception_false(
        self,
        jwt_config: JWTBearerAuthenticationConfig,
        mock_jwks_store: MagicMock,
    ) -> None:
        """Test that service can be initialized with raise_exception=False.

        Args:
            jwt_config (JWTBearerAuthenticationConfig): The JWT config.
            mock_jwks_store (MagicMock): The mock JWKS store.
        """
        service = JWTAuthenticationService(
            jwt_bearer_authentication_config=jwt_config,
            jwks_store=mock_jwks_store,
            raise_exception=False,
        )
        assert service._raise_exception is False  # type: ignore[attr-defined] # pylint: disable=protected-access

    @pytest.mark.asyncio
    async def test_authenticate_works_with_service(
        self,
        service: JWTAuthenticationService,
    ) -> None:
        """Test that authenticate method works with the service.

        Args:
            service (JWTAuthenticationService): The service instance.
        """
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test.token.here"}

        now = datetime.datetime.now(tz=datetime.UTC)
        exp = now + datetime.timedelta(hours=1)
        nbf = now - datetime.timedelta(minutes=5)

        jwt_payload = JWTPayload(  # type: ignore[arg-type]
            scope="read write",
            aud="api1 api2",
            iss="https://example.com",
            exp=int(exp.timestamp()),
            iat=int(now.timestamp()),
            nbf=int(nbf.timestamp()),
            sub="user123",
        )

        service._jwt_decoder.decode_payload = AsyncMock(return_value=jwt_payload)  # type: ignore[assignment]

        await service.authenticate(request=request)

        assert service.payload == jwt_payload
        assert service.has_errors() is False
