"""Provides the JWT bearer token extraction strategies."""

from abc import ABC, abstractmethod

from fastapi import Request

from fastapi_factory_utilities.core.security.types import JWTToken

from .configs import JWTBearerAuthenticationConfig, JWTLocation
from .exceptions import InvalidJWTError, MissingJWTCredentialsError


class JWTBearerTokenExtractionStrategyAbstract(ABC):
    """JWT bearer token extraction strategy."""

    def __init__(self, jwt_bearer_authentication_config: JWTBearerAuthenticationConfig) -> None:
        """Initialize the JWT bearer token extraction strategy."""
        self._jwt_bearer_authentication_config: JWTBearerAuthenticationConfig = jwt_bearer_authentication_config

    @abstractmethod
    def extract_token(self, request: Request) -> JWTToken:
        """Extract the JWT bearer token from the request."""
        raise NotImplementedError()


class JWTBearerTokenExtractionStrategyHeaderAuthorizationBearer(JWTBearerTokenExtractionStrategyAbstract):
    """JWT bearer token extraction strategy for the header authorization bearer."""

    @classmethod
    def extract_authorization_header_from_request(cls, request: Request) -> str:
        """Extract the authorization header from the request.

        Args:
            request (Request): The request object.

        Returns:
            str: The authorization header.

        Raises:
            MissingJWTCredentialsError: If the authorization header is missing.
        """
        authorization_header: str | None = request.headers.get("Authorization", None)
        if not authorization_header:
            raise MissingJWTCredentialsError(message="Missing Credentials")
        return authorization_header

    @classmethod
    def extract_bearer_token_from_authorization_header(cls, authorization_header: str) -> JWTToken:
        """Extract the bearer token from the authorization header.

        Args:
            authorization_header (str): The authorization header.

        Returns:
            JWTToken: The bearer token.

        Raises:
            InvalidJWTError: If the authorization header is invalid.
        """
        if not authorization_header.startswith("Bearer "):
            raise InvalidJWTError(message="Invalid Credentials")
        return JWTToken(authorization_header.split(sep=" ")[1])

    def extract_token(self, request: Request) -> JWTToken:
        """Extract the JWT bearer token from the request."""
        authorization_header: str = self.extract_authorization_header_from_request(request=request)
        return self.extract_bearer_token_from_authorization_header(authorization_header=authorization_header)


class JWTBearerTokenExtractionStrategyCookie(JWTBearerTokenExtractionStrategyAbstract):
    """JWT bearer token extraction strategy for the cookie."""

    def __init__(self, jwt_bearer_authentication_config: JWTBearerAuthenticationConfig) -> None:
        """Initialize the JWT bearer token extraction strategy."""
        super().__init__(jwt_bearer_authentication_config=jwt_bearer_authentication_config)
        if not jwt_bearer_authentication_config.cookie_name:
            raise ValueError("Cookie name is required")
        self._cookie_name: str = jwt_bearer_authentication_config.cookie_name

    def extract_token(self, request: Request) -> JWTToken:
        """Extract the JWT bearer token from the request."""
        if not self._cookie_name:
            raise MissingJWTCredentialsError(message="Missing Credentials")
        cookie: str | None = request.cookies.get(self._cookie_name, None)
        if not cookie:
            raise MissingJWTCredentialsError(message="Missing Credentials")
        return JWTToken(cookie)


class JWTHeaderTokenExtractionStrategy(JWTBearerTokenExtractionStrategyAbstract):
    """JWT header token extraction strategy."""

    def __init__(self, jwt_bearer_authentication_config: JWTBearerAuthenticationConfig) -> None:
        """Initialize the JWT header token extraction strategy."""
        super().__init__(jwt_bearer_authentication_config=jwt_bearer_authentication_config)
        if not jwt_bearer_authentication_config.header_name:
            raise ValueError("Header name is required")
        self._header_name: str = jwt_bearer_authentication_config.header_name

    def extract_token(self, request: Request) -> JWTToken:
        """Extract the JWT bearer token from the request."""
        header_value: str | None = request.headers.get(self._header_name, None)
        if not header_value:
            raise MissingJWTCredentialsError(message="Missing Credentials")
        return JWTToken(header_value)


def get_strategy_from_location(
    jwt_bearer_authentication_config: JWTBearerAuthenticationConfig, location: object
) -> JWTBearerTokenExtractionStrategyAbstract:
    """Get the JWT bearer token extraction strategy from the location."""
    match location:
        case JWTLocation.HEADER:
            return JWTHeaderTokenExtractionStrategy(jwt_bearer_authentication_config=jwt_bearer_authentication_config)
        case JWTLocation.AUTHORIZATION_BEARER:
            return JWTBearerTokenExtractionStrategyHeaderAuthorizationBearer(
                jwt_bearer_authentication_config=jwt_bearer_authentication_config
            )
        case JWTLocation.COOKIE:
            return JWTBearerTokenExtractionStrategyCookie(
                jwt_bearer_authentication_config=jwt_bearer_authentication_config
            )
        case _:
            msg_location: str = str(location)
            raise ValueError(f"Invalid location: {msg_location}")


def extract_token_from_request(
    request: Request, jwt_bearer_authentication_config: JWTBearerAuthenticationConfig
) -> JWTToken:
    """Extract the JWT bearer token from the request."""
    try:
        strategies: list[JWTBearerTokenExtractionStrategyAbstract] = [
            get_strategy_from_location(
                jwt_bearer_authentication_config=jwt_bearer_authentication_config, location=location
            )
            for location in jwt_bearer_authentication_config.authorized_locations
        ]
    except ValueError as error:
        # A ValueError here indicates a misconfigured JWTBearerAuthenticationConfig (e.g., missing header or cookie
        # name for a configured location, or an invalid location value). Surface this as a MissingJWTCredentialsError
        # so that callers like the authentication service can consistently translate it into an HTTP 401 response
        # instead of propagating an unhandled exception.
        raise MissingJWTCredentialsError(message=str(error)) from error
    last_invalid_error: InvalidJWTError | None = None
    for strategy in strategies:
        try:
            return strategy.extract_token(request=request)
        except MissingJWTCredentialsError:
            # Ignore the error and try the next strategy
            continue
        except InvalidJWTError as error:
            # Remember that we saw invalid credentials and try the next strategy
            last_invalid_error = error
            continue
    if last_invalid_error is not None:
        raise last_invalid_error
    raise MissingJWTCredentialsError(message="Missing Credentials")
