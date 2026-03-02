"""Unit tests for the JWT bearer token extraction strategies."""

from unittest.mock import MagicMock

import pytest
from fastapi import Request

from fastapi_factory_utilities.core.security.jwt.configs import JWTBearerAuthenticationConfig, JWTLocation
from fastapi_factory_utilities.core.security.jwt.exceptions import InvalidJWTError, MissingJWTCredentialsError
from fastapi_factory_utilities.core.security.jwt.extraction_strategies import (
    JWTBearerTokenExtractionStrategyCookie,
    JWTBearerTokenExtractionStrategyHeaderAuthorizationBearer,
    JWTHeaderTokenExtractionStrategy,
    extract_token_from_request,
    get_strategy_from_location,
)
from fastapi_factory_utilities.core.security.types import JWTToken, OAuth2Issuer

_DEFAULT_ISSUER: str = "https://example.com"


class TestJWTBearerTokenExtractionStrategyHeaderAuthorizationBearer:
    """Tests for the header Authorization Bearer extraction strategy."""

    @pytest.fixture
    def jwt_config(self) -> JWTBearerAuthenticationConfig:
        """Create a basic JWT bearer authentication config."""
        return JWTBearerAuthenticationConfig(
            authorized_algorithms=["RS256"],
            issuer=OAuth2Issuer(_DEFAULT_ISSUER),
        )

    def test_extract_authorization_header_from_request_success(self) -> None:
        """Test extracting authorization header from request successfully."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer test.token.here"}

        result = JWTBearerTokenExtractionStrategyHeaderAuthorizationBearer.extract_authorization_header_from_request(
            request=request
        )

        assert result == "Bearer test.token.here"

    def test_extract_authorization_header_from_request_missing(self) -> None:
        """Test extracting authorization header when it's missing."""
        request = MagicMock(spec=Request)
        request.headers = {}

        with pytest.raises(MissingJWTCredentialsError) as exc_info:
            JWTBearerTokenExtractionStrategyHeaderAuthorizationBearer.extract_authorization_header_from_request(
                request=request
            )

        assert "Missing Credentials" in str(exc_info.value)

    def test_extract_authorization_header_from_request_none(self) -> None:
        """Test extracting authorization header when it's None."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": None}

        with pytest.raises(MissingJWTCredentialsError) as exc_info:
            JWTBearerTokenExtractionStrategyHeaderAuthorizationBearer.extract_authorization_header_from_request(
                request=request
            )

        assert "Missing Credentials" in str(exc_info.value)

    def test_extract_bearer_token_from_authorization_header_success(self) -> None:
        """Test extracting bearer token from authorization header successfully."""
        authorization_header = "Bearer test.token.here"

        result = (
            JWTBearerTokenExtractionStrategyHeaderAuthorizationBearer.extract_bearer_token_from_authorization_header(
                authorization_header=authorization_header
            )
        )

        assert result == JWTToken("test.token.here")
        assert str(result) == "test.token.here"

    def test_extract_bearer_token_from_authorization_header_invalid_prefix(self) -> None:
        """Test extracting bearer token when prefix is invalid."""
        authorization_header = "Basic test.token.here"

        with pytest.raises(InvalidJWTError) as exc_info:
            JWTBearerTokenExtractionStrategyHeaderAuthorizationBearer.extract_bearer_token_from_authorization_header(
                authorization_header=authorization_header
            )

        assert "Invalid Credentials" in str(exc_info.value)

    def test_extract_bearer_token_from_authorization_header_no_space(self) -> None:
        """Test extracting bearer token when there's no space after Bearer."""
        authorization_header = "Bearertest.token.here"

        with pytest.raises(InvalidJWTError) as exc_info:
            JWTBearerTokenExtractionStrategyHeaderAuthorizationBearer.extract_bearer_token_from_authorization_header(
                authorization_header=authorization_header
            )

        assert "Invalid Credentials" in str(exc_info.value)

    def test_extract_bearer_token_from_authorization_header_empty_token(self) -> None:
        """Test extracting bearer token when token is empty."""
        authorization_header = "Bearer "

        result = (
            JWTBearerTokenExtractionStrategyHeaderAuthorizationBearer.extract_bearer_token_from_authorization_header(
                authorization_header=authorization_header
            )
        )

        assert result == JWTToken("")
        assert str(result) == ""


class TestJWTHeaderTokenExtractionStrategy:
    """Tests for the custom header extraction strategy."""

    @pytest.fixture
    def jwt_config(self) -> JWTBearerAuthenticationConfig:
        """Create a JWT bearer authentication config for header-based extraction."""
        return JWTBearerAuthenticationConfig(
            authorized_algorithms=["RS256"],
            issuer=OAuth2Issuer(_DEFAULT_ISSUER),
            authorized_locations=[JWTLocation.HEADER],
            header_name="X-My-JWT",
        )

    def test_initialization_requires_header_name(self) -> None:
        """Strategy initialization should fail when header_name is missing."""
        config = JWTBearerAuthenticationConfig(
            authorized_algorithms=["RS256"],
            issuer=OAuth2Issuer(_DEFAULT_ISSUER),
            authorized_locations=[JWTLocation.HEADER],
        )

        with pytest.raises(ValueError) as exc_info:
            JWTHeaderTokenExtractionStrategy(jwt_bearer_authentication_config=config)

        assert "Header name is required" in str(exc_info.value)

    def test_extract_token_success(self, jwt_config: JWTBearerAuthenticationConfig) -> None:
        """Extract token from the configured header."""
        strategy = JWTHeaderTokenExtractionStrategy(jwt_bearer_authentication_config=jwt_config)
        request = MagicMock(spec=Request)
        request.headers = {"X-My-JWT": "header.jwt.token"}

        token = strategy.extract_token(request=request)

        assert token == JWTToken("header.jwt.token")

    def test_extract_token_missing_header_raises_missing_credentials(
        self, jwt_config: JWTBearerAuthenticationConfig
    ) -> None:
        """Missing header value should raise MissingJWTCredentialsError."""
        strategy = JWTHeaderTokenExtractionStrategy(jwt_bearer_authentication_config=jwt_config)
        request = MagicMock(spec=Request)
        request.headers = {}

        with pytest.raises(MissingJWTCredentialsError):
            strategy.extract_token(request=request)


class TestJWTBearerTokenExtractionStrategyCookie:
    """Tests for the cookie-based extraction strategy."""

    @pytest.fixture
    def jwt_config(self) -> JWTBearerAuthenticationConfig:
        """Create a JWT bearer authentication config for cookie-based extraction."""
        return JWTBearerAuthenticationConfig(
            authorized_algorithms=["RS256"],
            issuer=OAuth2Issuer(_DEFAULT_ISSUER),
            authorized_locations=[JWTLocation.COOKIE],
            cookie_name="jwt_cookie",
        )

    def test_initialization_requires_cookie_name(self) -> None:
        """Strategy initialization should fail when cookie_name is missing."""
        config = JWTBearerAuthenticationConfig(
            authorized_algorithms=["RS256"],
            issuer=OAuth2Issuer(_DEFAULT_ISSUER),
            authorized_locations=[JWTLocation.COOKIE],
        )

        with pytest.raises(ValueError) as exc_info:
            JWTBearerTokenExtractionStrategyCookie(jwt_bearer_authentication_config=config)

        assert "Cookie name is required" in str(exc_info.value)

    def test_extract_token_success(self, jwt_config: JWTBearerAuthenticationConfig) -> None:
        """Extract token from the configured cookie."""
        strategy = JWTBearerTokenExtractionStrategyCookie(jwt_bearer_authentication_config=jwt_config)
        request = MagicMock(spec=Request)
        request.cookies = {"jwt_cookie": "cookie.jwt.token"}

        token = strategy.extract_token(request=request)

        assert token == JWTToken("cookie.jwt.token")

    def test_extract_token_missing_cookie_raises_missing_credentials(
        self, jwt_config: JWTBearerAuthenticationConfig
    ) -> None:
        """Missing cookie should raise MissingJWTCredentialsError."""
        strategy = JWTBearerTokenExtractionStrategyCookie(jwt_bearer_authentication_config=jwt_config)
        request = MagicMock(spec=Request)
        request.cookies = {}

        with pytest.raises(MissingJWTCredentialsError):
            strategy.extract_token(request=request)


class TestGetStrategyFromLocation:
    """Tests for get_strategy_from_location."""

    @pytest.fixture
    def jwt_config(self) -> JWTBearerAuthenticationConfig:
        """Create a base JWT bearer authentication config."""
        return JWTBearerAuthenticationConfig(
            authorized_algorithms=["RS256"],
            issuer=OAuth2Issuer(_DEFAULT_ISSUER),
        )

    def test_returns_header_strategy(self, jwt_config: JWTBearerAuthenticationConfig) -> None:
        """HEADER location returns JWTHeaderTokenExtractionStrategy."""
        config = jwt_config.model_copy(update={"authorized_locations": [JWTLocation.HEADER], "header_name": "X-My-JWT"})

        strategy = get_strategy_from_location(jwt_bearer_authentication_config=config, location=JWTLocation.HEADER)

        assert isinstance(strategy, JWTHeaderTokenExtractionStrategy)

    def test_returns_authorization_bearer_strategy(self, jwt_config: JWTBearerAuthenticationConfig) -> None:
        """HEADER_AUTHORIZATION_BEARER location returns JWTBearerTokenExtractionStrategyHeaderAuthorizationBearer."""
        config = jwt_config.model_copy(update={"authorized_locations": [JWTLocation.AUTHORIZATION_BEARER]})

        strategy = get_strategy_from_location(
            jwt_bearer_authentication_config=config, location=JWTLocation.AUTHORIZATION_BEARER
        )

        assert isinstance(strategy, JWTBearerTokenExtractionStrategyHeaderAuthorizationBearer)

    def test_returns_cookie_strategy(self, jwt_config: JWTBearerAuthenticationConfig) -> None:
        """COOKIE location returns JWTBearerTokenExtractionStrategyCookie."""
        config = jwt_config.model_copy(
            update={"authorized_locations": [JWTLocation.COOKIE], "cookie_name": "jwt_cookie"}
        )

        strategy = get_strategy_from_location(jwt_bearer_authentication_config=config, location=JWTLocation.COOKIE)

        assert isinstance(strategy, JWTBearerTokenExtractionStrategyCookie)

    def test_invalid_location_raises_value_error(self, jwt_config: JWTBearerAuthenticationConfig) -> None:
        """Invalid location value should raise ValueError."""
        with pytest.raises(ValueError):
            get_strategy_from_location(
                jwt_bearer_authentication_config=jwt_config,
                location="invalid",  # pyright: ignore[reportArgumentType]
            )


class TestExtractTokenFromRequest:
    """Tests for extract_token_from_request orchestrator."""

    @pytest.fixture
    def base_config(self) -> JWTBearerAuthenticationConfig:
        """Base JWT bearer authentication config."""
        return JWTBearerAuthenticationConfig(
            authorized_algorithms=["RS256"],
            issuer=OAuth2Issuer(_DEFAULT_ISSUER),
        )

    def test_success_on_first_location_header_authorization_bearer(
        self, base_config: JWTBearerAuthenticationConfig
    ) -> None:
        """When first location succeeds, token is returned from Authorization header."""
        config = base_config.model_copy(
            update={
                "authorized_locations": [JWTLocation.AUTHORIZATION_BEARER, JWTLocation.COOKIE],
                "cookie_name": "jwt_cookie",
            }
        )
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer header.jwt.token"}
        request.cookies = {}

        token = extract_token_from_request(request=request, jwt_bearer_authentication_config=config)

        assert token == JWTToken("header.jwt.token")

    def test_fallback_to_second_location_on_missing_first(self, base_config: JWTBearerAuthenticationConfig) -> None:
        """If first strategy reports missing credentials, orchestrator should fall back to the second."""
        config = base_config.model_copy(
            update={
                "authorized_locations": [JWTLocation.AUTHORIZATION_BEARER, JWTLocation.COOKIE],
                "cookie_name": "jwt_cookie",
            }
        )
        request = MagicMock(spec=Request)
        request.headers = {}
        request.cookies = {"jwt_cookie": "cookie.jwt.token"}

        token = extract_token_from_request(request=request, jwt_bearer_authentication_config=config)

        assert token == JWTToken("cookie.jwt.token")

    def test_fallback_to_second_location_on_invalid_first(self, base_config: JWTBearerAuthenticationConfig) -> None:
        """If first strategy sees invalid credentials but second succeeds, the token should be returned."""
        config = base_config.model_copy(
            update={
                "authorized_locations": [JWTLocation.AUTHORIZATION_BEARER, JWTLocation.COOKIE],
                "cookie_name": "jwt_cookie",
            }
        )
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Basic invalid.jwt.token"}
        request.cookies = {"jwt_cookie": "cookie.jwt.token"}

        token = extract_token_from_request(request=request, jwt_bearer_authentication_config=config)

        assert token == JWTToken("cookie.jwt.token")

    def test_final_missing_credentials_raises_missing_error(self, base_config: JWTBearerAuthenticationConfig) -> None:
        """If all strategies report missing credentials, MissingJWTCredentialsError is raised."""
        config = base_config.model_copy(
            update={
                "authorized_locations": [JWTLocation.COOKIE],
                "cookie_name": "jwt_cookie",
            }
        )
        request = MagicMock(spec=Request)
        request.headers = {}
        request.cookies = {}

        with pytest.raises(MissingJWTCredentialsError):
            extract_token_from_request(request=request, jwt_bearer_authentication_config=config)

    def test_final_invalid_credentials_raises_invalid_error(self, base_config: JWTBearerAuthenticationConfig) -> None:
        """If at least one strategy sees invalid credentials and none succeed, InvalidJWTError is raised."""
        config = base_config.model_copy(
            update={
                "authorized_locations": [JWTLocation.AUTHORIZATION_BEARER, JWTLocation.COOKIE],
                "cookie_name": "jwt_cookie",
            }
        )
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Basic invalid.jwt.token"}
        request.cookies = {}

        with pytest.raises(InvalidJWTError):
            extract_token_from_request(request=request, jwt_bearer_authentication_config=config)

    def test_misconfigured_header_location_raises_missing_credentials(
        self, base_config: JWTBearerAuthenticationConfig
    ) -> None:
        """Misconfigured HEADER location (missing header_name) should surface as MissingJWTCredentialsError."""
        config = base_config.model_copy(update={"authorized_locations": [JWTLocation.HEADER]})
        request = MagicMock(spec=Request)
        request.headers = {}
        request.cookies = {}

        with pytest.raises(MissingJWTCredentialsError):
            extract_token_from_request(request=request, jwt_bearer_authentication_config=config)

    def test_misconfigured_cookie_location_raises_missing_credentials(
        self, base_config: JWTBearerAuthenticationConfig
    ) -> None:
        """Misconfigured COOKIE location (missing cookie_name) should surface as MissingJWTCredentialsError."""
        config = base_config.model_copy(update={"authorized_locations": [JWTLocation.COOKIE]})
        request = MagicMock(spec=Request)
        request.headers = {}
        request.cookies = {}

        with pytest.raises(MissingJWTCredentialsError):
            extract_token_from_request(request=request, jwt_bearer_authentication_config=config)
