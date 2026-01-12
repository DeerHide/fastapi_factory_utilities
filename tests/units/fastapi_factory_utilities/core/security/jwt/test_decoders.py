"""Unit tests for the JWT decoders."""

import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jwt import InvalidTokenError
from jwt.api_jwk import PyJWK
from pydantic import ValidationError

from fastapi_factory_utilities.core.security.jwt.configs import JWTBearerAuthenticationConfig
from fastapi_factory_utilities.core.security.jwt.decoders import (
    JWTBearerTokenDecoder,
    JWTBearerTokenDecoderAbstract,
    decode_jwt_token_payload,
)
from fastapi_factory_utilities.core.security.jwt.exceptions import InvalidJWTError, InvalidJWTPayploadError
from fastapi_factory_utilities.core.security.jwt.objects import JWTPayload
from fastapi_factory_utilities.core.security.jwt.stores import JWKStoreAbstract
from fastapi_factory_utilities.core.security.jwt.types import JWTToken, OAuth2Subject


class TestDecodeJWTTokenPayload:
    """Various tests for the decode_jwt_token_payload function."""

    @pytest.fixture
    def mock_public_key(self) -> MagicMock:
        """Create a mock public key.

        Returns:
            MagicMock: A mock PyJWK object.
        """
        return MagicMock(spec=PyJWK)

    @pytest.fixture
    def jwt_token(self) -> JWTToken:
        """Create a JWT token.

        Returns:
            JWTToken: A JWT token.
        """
        return JWTToken("test.jwt.token")

    @pytest.fixture
    def minimal_config(self) -> JWTBearerAuthenticationConfig:
        """Create a minimal JWT bearer authentication config.

        Returns:
            JWTBearerAuthenticationConfig: A minimal config.
        """
        return JWTBearerAuthenticationConfig(
            authorized_algorithms=["RS256"],
        )

    @pytest.fixture
    def config_with_issuer(self) -> JWTBearerAuthenticationConfig:
        """Create a JWT bearer authentication config with issuer.

        Returns:
            JWTBearerAuthenticationConfig: A config with issuer.
        """
        return JWTBearerAuthenticationConfig(
            authorized_algorithms=["RS256"],
            authorized_issuers=["https://example.com"],
        )

    @pytest.fixture
    def config_with_audience(self) -> JWTBearerAuthenticationConfig:
        """Create a JWT bearer authentication config with authorized audiences.

        Returns:
            JWTBearerAuthenticationConfig: A config with authorized audiences.
        """
        return JWTBearerAuthenticationConfig(
            authorized_algorithms=["RS256"],
            authorized_audiences=["audience1", "audience2"],
        )

    @pytest.fixture
    def config_with_all_options(self) -> JWTBearerAuthenticationConfig:
        """Create a JWT bearer authentication config with all options.

        Returns:
            JWTBearerAuthenticationConfig: A config with all options.
        """
        return JWTBearerAuthenticationConfig(
            authorized_algorithms=["RS256"],
            authorized_issuers=["https://example.com"],
            authorized_audiences=["audience1", "audience2"],
        )

    @pytest.fixture
    def decoded_payload(self) -> dict[str, Any]:
        """Create a decoded JWT payload.

        Returns:
            dict[str, Any]: A decoded JWT payload.
        """
        now = datetime.datetime.now(tz=datetime.UTC)
        return {
            "scope": "read write",
            "aud": "test_audience",
            "iss": "https://example.com",
            "exp": int(now.timestamp()) + 3600,
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "sub": "test_subject",
        }

    @pytest.mark.asyncio
    async def test_decode_with_minimal_config(
        self,
        jwt_token: JWTToken,
        mock_public_key: MagicMock,
        minimal_config: JWTBearerAuthenticationConfig,
        decoded_payload: dict[str, Any],
    ) -> None:
        """Test decoding with minimal configuration.

        Args:
            jwt_token (JWTToken): The JWT token.
            mock_public_key (MagicMock): The mock public key.
            minimal_config (JWTBearerAuthenticationConfig): The minimal config.
            decoded_payload (dict[str, Any]): The decoded payload.
        """
        with patch("fastapi_factory_utilities.core.security.jwt.decoders.decode") as mock_decode:
            mock_decode.return_value = decoded_payload

            result = await decode_jwt_token_payload(
                jwt_token=jwt_token,
                public_key=mock_public_key,
                jwt_bearer_authentication_config=minimal_config,
            )

            assert result == decoded_payload
            mock_decode.assert_called_once_with(
                jwt=jwt_token,
                key=mock_public_key,
                algorithms=minimal_config.authorized_algorithms,
                options={"verify_signature": True},
            )

    @pytest.mark.asyncio
    async def test_decode_with_issuer(
        self,
        jwt_token: JWTToken,
        mock_public_key: MagicMock,
        config_with_issuer: JWTBearerAuthenticationConfig,
        decoded_payload: dict[str, Any],
    ) -> None:
        """Test decoding with issuer configuration.

        Args:
            jwt_token (JWTToken): The JWT token.
            mock_public_key (MagicMock): The mock public key.
            config_with_issuer (JWTBearerAuthenticationConfig): The config with issuer.
            decoded_payload (dict[str, Any]): The decoded payload.
        """
        with patch("fastapi_factory_utilities.core.security.jwt.decoders.decode") as mock_decode:
            mock_decode.return_value = decoded_payload

            result = await decode_jwt_token_payload(
                jwt_token=jwt_token,
                public_key=mock_public_key,
                jwt_bearer_authentication_config=config_with_issuer,
            )

            assert result == decoded_payload
            mock_decode.assert_called_once_with(
                jwt=jwt_token,
                key=mock_public_key,
                algorithms=config_with_issuer.authorized_algorithms,
                options={"verify_signature": True},
                issuer=config_with_issuer.authorized_issuers,
            )

    @pytest.mark.asyncio
    async def test_decode_with_audience(
        self,
        jwt_token: JWTToken,
        mock_public_key: MagicMock,
        config_with_audience: JWTBearerAuthenticationConfig,
        decoded_payload: dict[str, Any],
    ) -> None:
        """Test decoding with authorized audiences configuration.

        Args:
            jwt_token (JWTToken): The JWT token.
            mock_public_key (MagicMock): The mock public key.
            config_with_audience (JWTBearerAuthenticationConfig): The config with authorized audiences.
            decoded_payload (dict[str, Any]): The decoded payload.
        """
        with patch("fastapi_factory_utilities.core.security.jwt.decoders.decode") as mock_decode:
            mock_decode.return_value = decoded_payload

            result = await decode_jwt_token_payload(
                jwt_token=jwt_token,
                public_key=mock_public_key,
                jwt_bearer_authentication_config=config_with_audience,
            )

            assert result == decoded_payload
            mock_decode.assert_called_once_with(
                jwt=jwt_token,
                key=mock_public_key,
                algorithms=config_with_audience.authorized_algorithms,
                options={"verify_signature": True},
                audience=config_with_audience.authorized_audiences,
            )

    @pytest.mark.asyncio
    async def test_decode_with_subject(
        self,
        jwt_token: JWTToken,
        mock_public_key: MagicMock,
        minimal_config: JWTBearerAuthenticationConfig,
        decoded_payload: dict[str, Any],
    ) -> None:
        """Test decoding with subject.

        Args:
            jwt_token (JWTToken): The JWT token.
            mock_public_key (MagicMock): The mock public key.
            minimal_config (JWTBearerAuthenticationConfig): The minimal config.
            decoded_payload (dict[str, Any]): The decoded payload.
        """
        subject: OAuth2Subject = OAuth2Subject("test_subject")
        with patch("fastapi_factory_utilities.core.security.jwt.decoders.decode") as mock_decode:
            mock_decode.return_value = decoded_payload

            result = await decode_jwt_token_payload(
                jwt_token=jwt_token,
                public_key=mock_public_key,
                jwt_bearer_authentication_config=minimal_config,
                subject=subject,
            )

            assert result == decoded_payload
            mock_decode.assert_called_once_with(
                jwt=jwt_token,
                key=mock_public_key,
                algorithms=minimal_config.authorized_algorithms,
                options={"verify_signature": True},
                subject=subject,
            )

    @pytest.mark.asyncio
    async def test_decode_with_all_options(
        self,
        jwt_token: JWTToken,
        mock_public_key: MagicMock,
        config_with_all_options: JWTBearerAuthenticationConfig,
        decoded_payload: dict[str, Any],
    ) -> None:
        """Test decoding with all options configured.

        Args:
            jwt_token (JWTToken): The JWT token.
            mock_public_key (MagicMock): The mock public key.
            config_with_all_options (JWTBearerAuthenticationConfig): The config with all options.
            decoded_payload (dict[str, Any]): The decoded payload.
        """
        subject: OAuth2Subject = OAuth2Subject("test_subject")
        with patch("fastapi_factory_utilities.core.security.jwt.decoders.decode") as mock_decode:
            mock_decode.return_value = decoded_payload

            result = await decode_jwt_token_payload(
                jwt_token=jwt_token,
                public_key=mock_public_key,
                jwt_bearer_authentication_config=config_with_all_options,
                subject=subject,
            )

            assert result == decoded_payload
            mock_decode.assert_called_once_with(
                jwt=jwt_token,
                key=mock_public_key,
                algorithms=config_with_all_options.authorized_algorithms,
                options={"verify_signature": True},
                issuer=config_with_all_options.authorized_issuers,
                audience=config_with_all_options.authorized_audiences,
                subject=subject,
            )

    @pytest.mark.asyncio
    async def test_decode_raises_invalid_jwt_error_on_invalid_token(
        self,
        jwt_token: JWTToken,
        mock_public_key: MagicMock,
        minimal_config: JWTBearerAuthenticationConfig,
    ) -> None:
        """Test that InvalidJWTError is raised when decode raises InvalidTokenError.

        Args:
            jwt_token (JWTToken): The JWT token.
            mock_public_key (MagicMock): The mock public key.
            minimal_config (JWTBearerAuthenticationConfig): The minimal config.
        """
        with patch("fastapi_factory_utilities.core.security.jwt.decoders.decode") as mock_decode:
            mock_decode.side_effect = InvalidTokenError("Invalid token")

            with pytest.raises(InvalidJWTError) as exc_info:
                await decode_jwt_token_payload(
                    jwt_token=jwt_token,
                    public_key=mock_public_key,
                    jwt_bearer_authentication_config=minimal_config,
                )

            assert "Failed to decode the JWT bearer token payload" in str(exc_info.value)
            assert exc_info.value.__cause__ is not None
            assert isinstance(exc_info.value.__cause__, InvalidTokenError)


class TestJWTBearerTokenDecoderAbstract:
    """Various tests for the JWTBearerTokenDecoderAbstract class."""

    def test_abstract_class_cannot_be_instantiated(self) -> None:
        """Test that the abstract class cannot be instantiated directly."""
        with pytest.raises(TypeError):
            JWTBearerTokenDecoderAbstract()  # type: ignore[abstract] # pylint: disable=abstract-class-instantiated

    def test_get_kid_from_jwt_unsafe_header_success(self) -> None:
        """Test that get_kid_from_jwt_unsafe_header returns the kid from the JWT header."""

        # Create a concrete implementation for testing
        class ConcreteDecoder(JWTBearerTokenDecoderAbstract[JWTPayload]):
            """Concrete implementation for testing."""

            async def decode_payload(self, jwt_token: JWTToken) -> JWTPayload:
                """Decode the JWT bearer token payload."""
                raise NotImplementedError()

        decoder = ConcreteDecoder()
        jwt_token = JWTToken("test.jwt.token")

        with patch("fastapi_factory_utilities.core.security.jwt.decoders.get_unverified_header") as mock_get_header:
            mock_get_header.return_value = {"kid": "test_kid_123"}

            result = decoder.get_kid_from_jwt_unsafe_header(jwt_token=jwt_token)

            assert result == "test_kid_123"
            mock_get_header.assert_called_once_with(jwt_token)

    def test_get_kid_from_jwt_unsafe_header_raises_invalid_jwt_error_on_missing_kid(self) -> None:
        """Test that get_kid_from_jwt_unsafe_header raises InvalidJWTError when kid is missing."""

        # Create a concrete implementation for testing
        class ConcreteDecoder(JWTBearerTokenDecoderAbstract[JWTPayload]):
            """Concrete implementation for testing."""

            async def decode_payload(self, jwt_token: JWTToken) -> JWTPayload:
                """Decode the JWT bearer token payload."""
                raise NotImplementedError()

        decoder = ConcreteDecoder()
        jwt_token = JWTToken("test.jwt.token")

        with patch("fastapi_factory_utilities.core.security.jwt.decoders.get_unverified_header") as mock_get_header:
            mock_get_header.return_value = {}  # No kid in header

            with pytest.raises(InvalidJWTError) as exc_info:
                decoder.get_kid_from_jwt_unsafe_header(jwt_token=jwt_token)

            assert "Failed to get the kid from the JWT header" in str(exc_info.value)
            assert exc_info.value.__cause__ is not None
            assert isinstance(exc_info.value.__cause__, KeyError)

    def test_get_kid_from_jwt_unsafe_header_raises_invalid_jwt_error_on_invalid_token(self) -> None:
        """Test that get_kid_from_jwt_unsafe_header raises InvalidJWTError on invalid token."""

        # Create a concrete implementation for testing
        class ConcreteDecoder(JWTBearerTokenDecoderAbstract[JWTPayload]):
            """Concrete implementation for testing."""

            async def decode_payload(self, jwt_token: JWTToken) -> JWTPayload:
                """Decode the JWT bearer token payload."""
                raise NotImplementedError()

        decoder = ConcreteDecoder()
        jwt_token = JWTToken("test.jwt.token")

        with patch("fastapi_factory_utilities.core.security.jwt.decoders.get_unverified_header") as mock_get_header:
            mock_get_header.side_effect = InvalidTokenError("Invalid token")

            with pytest.raises(InvalidJWTError) as exc_info:
                decoder.get_kid_from_jwt_unsafe_header(jwt_token=jwt_token)

            assert "Failed to get the kid from the JWT header" in str(exc_info.value)
            assert exc_info.value.__cause__ is not None
            assert isinstance(exc_info.value.__cause__, InvalidTokenError)


class TestJWTBearerTokenDecoder:
    """Various tests for the JWTBearerTokenDecoder class."""

    @pytest.fixture
    def mock_public_key(self) -> MagicMock:
        """Create a mock public key.

        Returns:
            MagicMock: A mock PyJWK object.
        """
        return MagicMock(spec=PyJWK)

    @pytest.fixture
    def jwt_token(self) -> JWTToken:
        """Create a JWT token.

        Returns:
            JWTToken: A JWT token.
        """
        return JWTToken("test.jwt.token")

    @pytest.fixture
    def jwt_config(self) -> JWTBearerAuthenticationConfig:
        """Create a JWT bearer authentication config.

        Returns:
            JWTBearerAuthenticationConfig: A JWT bearer authentication config.
        """
        return JWTBearerAuthenticationConfig(
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
    def decoder(self, jwt_config: JWTBearerAuthenticationConfig, mock_jwks_store: MagicMock) -> JWTBearerTokenDecoder:
        """Create a JWT bearer token decoder.

        Args:
            jwt_config (JWTBearerAuthenticationConfig): The JWT config.
            mock_jwks_store (MagicMock): The mock JWKS store.

        Returns:
            JWTBearerTokenDecoder: A JWT bearer token decoder.
        """
        return JWTBearerTokenDecoder(
            jwt_bearer_authentication_config=jwt_config,
            jwks_store=mock_jwks_store,
        )

    @pytest.fixture
    def valid_decoded_payload(self) -> dict[str, Any]:
        """Create a valid decoded JWT payload.

        Returns:
            dict[str, Any]: A valid decoded JWT payload.
        """
        now = datetime.datetime.now(tz=datetime.UTC)
        return {
            "scp": "read write",
            "aud": "test_audience",
            "iss": "https://example.com",
            "exp": int(now.timestamp()) + 3600,
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "sub": "test_subject",
        }

    @pytest.mark.asyncio
    async def test_decode_payload_success(
        self,
        decoder: JWTBearerTokenDecoder,
        jwt_token: JWTToken,
        valid_decoded_payload: dict[str, Any],
        mock_jwks_store: MagicMock,
    ) -> None:
        """Test successful payload decoding.

        Args:
            decoder (JWTBearerTokenDecoder): The decoder instance.
            jwt_token (JWTToken): The JWT token.
            valid_decoded_payload (dict[str, Any]): The valid decoded payload.
            mock_jwks_store (MagicMock): The mock JWKS store.
        """
        mock_jwk = MagicMock(spec=PyJWK)
        mock_jwks_store.get_jwk = AsyncMock(return_value=mock_jwk)

        with patch("fastapi_factory_utilities.core.security.jwt.decoders.get_unverified_header") as mock_get_header:
            mock_get_header.return_value = {"kid": "test_kid"}
            with patch("fastapi_factory_utilities.core.security.jwt.decoders.decode_jwt_token_payload") as mock_decode:
                mock_decode.return_value = valid_decoded_payload

                result = await decoder.decode_payload(jwt_token=jwt_token)

                assert isinstance(result, JWTPayload)
                assert result.scp == ["read", "write"]
                assert result.aud == ["test_audience"]
                assert result.iss == "https://example.com"
                assert result.sub == "test_subject"
                mock_get_header.assert_called_once_with(jwt_token)
                mock_jwks_store.get_jwk.assert_called_once_with(kid="test_kid")
                mock_decode.assert_called_once_with(
                    jwt_token=jwt_token,
                    public_key=mock_jwk,
                    jwt_bearer_authentication_config=decoder._jwt_bearer_authentication_config,  # pylint: disable=protected-access
                )

    @pytest.mark.asyncio
    async def test_decode_payload_raises_invalid_jwt_error(
        self,
        decoder: JWTBearerTokenDecoder,
        jwt_token: JWTToken,
        mock_jwks_store: MagicMock,
    ) -> None:
        """Test that InvalidJWTError is raised when decode fails.

        Args:
            decoder (JWTBearerTokenDecoder): The decoder instance.
            jwt_token (JWTToken): The JWT token.
            mock_jwks_store (MagicMock): The mock JWKS store.
        """
        mock_jwk = MagicMock(spec=PyJWK)
        mock_jwks_store.get_jwk = AsyncMock(return_value=mock_jwk)

        with patch("fastapi_factory_utilities.core.security.jwt.decoders.get_unverified_header") as mock_get_header:
            mock_get_header.return_value = {"kid": "test_kid"}
            with patch("fastapi_factory_utilities.core.security.jwt.decoders.decode_jwt_token_payload") as mock_decode:
                mock_decode.side_effect = InvalidJWTError("Failed to decode")

                with pytest.raises(InvalidJWTError) as exc_info:
                    await decoder.decode_payload(jwt_token=jwt_token)

                assert "Failed to decode" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_decode_payload_raises_invalid_jwt_payload_error_on_validation_failure(
        self,
        decoder: JWTBearerTokenDecoder,
        jwt_token: JWTToken,
        mock_jwks_store: MagicMock,
    ) -> None:
        """Test that InvalidJWTPayploadError is raised when payload validation fails.

        Args:
            decoder (JWTBearerTokenDecoder): The decoder instance.
            jwt_token (JWTToken): The JWT token.
            mock_jwks_store (MagicMock): The mock JWKS store.
        """
        mock_jwk = MagicMock(spec=PyJWK)
        mock_jwks_store.get_jwk = AsyncMock(return_value=mock_jwk)

        invalid_payload = {"invalid": "payload"}
        with patch("fastapi_factory_utilities.core.security.jwt.decoders.get_unverified_header") as mock_get_header:
            mock_get_header.return_value = {"kid": "test_kid"}
            with patch("fastapi_factory_utilities.core.security.jwt.decoders.decode_jwt_token_payload") as mock_decode:
                mock_decode.return_value = invalid_payload

                with pytest.raises(InvalidJWTPayploadError) as exc_info:
                    await decoder.decode_payload(jwt_token=jwt_token)

                assert "Failed to validate the JWT bearer token payload" in str(exc_info.value)
                assert exc_info.value.__cause__ is not None
                assert isinstance(exc_info.value.__cause__, ValidationError)

    @pytest.mark.asyncio
    async def test_decode_payload_with_missing_required_fields(
        self,
        decoder: JWTBearerTokenDecoder,
        jwt_token: JWTToken,
        mock_jwks_store: MagicMock,
    ) -> None:
        """Test that InvalidJWTPayploadError is raised when required fields are missing.

        Args:
            decoder (JWTBearerTokenDecoder): The decoder instance.
            jwt_token (JWTToken): The JWT token.
            mock_jwks_store (MagicMock): The mock JWKS store.
        """
        mock_jwk = MagicMock(spec=PyJWK)
        mock_jwks_store.get_jwk = AsyncMock(return_value=mock_jwk)

        incomplete_payload = {
            "scp": "read",
            # Missing other required fields
        }
        with patch("fastapi_factory_utilities.core.security.jwt.decoders.get_unverified_header") as mock_get_header:
            mock_get_header.return_value = {"kid": "test_kid"}
            with patch("fastapi_factory_utilities.core.security.jwt.decoders.decode_jwt_token_payload") as mock_decode:
                mock_decode.return_value = incomplete_payload

                with pytest.raises(InvalidJWTPayploadError) as exc_info:
                    await decoder.decode_payload(jwt_token=jwt_token)

                assert "Failed to validate the JWT bearer token payload" in str(exc_info.value)
                assert exc_info.value.__cause__ is not None
                assert isinstance(exc_info.value.__cause__, ValidationError)

    @pytest.mark.asyncio
    async def test_decode_payload_with_invalid_timestamp_format(
        self,
        decoder: JWTBearerTokenDecoder,
        jwt_token: JWTToken,
        mock_jwks_store: MagicMock,
    ) -> None:
        """Test that InvalidJWTPayploadError is raised when timestamp format is invalid.

        Args:
            decoder (JWTBearerTokenDecoder): The decoder instance.
            jwt_token (JWTToken): The JWT token.
            mock_jwks_store (MagicMock): The mock JWKS store.
        """
        mock_jwk = MagicMock(spec=PyJWK)
        mock_jwks_store.get_jwk = AsyncMock(return_value=mock_jwk)

        invalid_timestamp_payload = {
            "scp": "read write",
            "aud": "test_audience",
            "iss": "https://example.com",
            "exp": "invalid_timestamp",
            "iat": "invalid_timestamp",
            "nbf": "invalid_timestamp",
            "sub": "test_subject",
        }
        with patch("fastapi_factory_utilities.core.security.jwt.decoders.get_unverified_header") as mock_get_header:
            mock_get_header.return_value = {"kid": "test_kid"}
            with patch("fastapi_factory_utilities.core.security.jwt.decoders.decode_jwt_token_payload") as mock_decode:
                mock_decode.return_value = invalid_timestamp_payload

                with pytest.raises(InvalidJWTPayploadError) as exc_info:
                    await decoder.decode_payload(jwt_token=jwt_token)

                assert "Failed to validate the JWT bearer token payload" in str(exc_info.value)
                assert exc_info.value.__cause__ is not None
                assert isinstance(exc_info.value.__cause__, ValidationError)
