"""Provides the JWT bearer token extraction strategies."""

from abc import ABC, abstractmethod
from time import perf_counter

from fastapi import Request
from opentelemetry.trace import SpanKind, Status, StatusCode

from fastapi_factory_utilities.core.security.types import JWTToken

from .configs import JWTBearerAuthenticationConfig, JWTLocation
from .exceptions import InvalidJWTError, MissingJWTCredentialsError
from .telemetry import (
    ATTR_LOCATION,
    ATTR_OUTCOME,
    JWT_EXTRACT_DURATION,
    OUTCOME_INVALID_JWT,
    OUTCOME_MISSING_CREDENTIALS,
    OUTCOME_SUCCESS,
    TRACER,
    get_identifier_attributes,
)


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


_LOCATION_TO_STRATEGY_LABEL: dict[JWTLocation, str] = {
    JWTLocation.HEADER: JWTLocation.HEADER.value,
    JWTLocation.AUTHORIZATION_BEARER: JWTLocation.AUTHORIZATION_BEARER.value,
    JWTLocation.COOKIE: JWTLocation.COOKIE.value,
}


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
    """Extract the JWT bearer token from the request.

    Emits the ``jwt.extract`` span and records the ``jwt.extract.duration``
    histogram. The ``jwt.location`` attribute reflects the strategy that
    produced the token on success, or the last attempted strategy on failure.

    Raises:
        MissingJWTCredentialsError: If no strategy yielded credentials.
        InvalidJWTError: If a strategy found credentials but they were invalid.
    """
    identifier_attributes: dict[str, str] = get_identifier_attributes()
    start_ts: float = perf_counter()
    with TRACER.start_as_current_span(
        name="jwt.extract", kind=SpanKind.INTERNAL, attributes=identifier_attributes
    ) as span:
        try:
            strategies: list[tuple[JWTLocation, JWTBearerTokenExtractionStrategyAbstract]] = [
                (
                    location,
                    get_strategy_from_location(
                        jwt_bearer_authentication_config=jwt_bearer_authentication_config, location=location
                    ),
                )
                for location in jwt_bearer_authentication_config.authorized_locations
            ]
        except ValueError as error:
            # A ValueError here indicates a misconfigured JWTBearerAuthenticationConfig (e.g., missing header or cookie
            # name for a configured location, or an invalid location value). Surface this as a MissingJWTCredentialsError
            # so that callers like the authentication service can consistently translate it into an HTTP 401 response
            # instead of propagating an unhandled exception.
            outcome: str = OUTCOME_MISSING_CREDENTIALS
            span.set_attribute(ATTR_OUTCOME, outcome)
            span.record_exception(error)
            span.set_status(Status(StatusCode.ERROR, str(error)))
            JWT_EXTRACT_DURATION.record(
                amount=perf_counter() - start_ts,
                attributes={ATTR_OUTCOME: outcome, **identifier_attributes},
            )
            raise MissingJWTCredentialsError(message=str(error)) from error

        last_invalid_error: InvalidJWTError | None = None
        last_attempted_location: JWTLocation | None = None
        for location, strategy in strategies:
            last_attempted_location = location
            try:
                token: JWTToken = strategy.extract_token(request=request)
            except MissingJWTCredentialsError:
                continue
            except InvalidJWTError as error:
                last_invalid_error = error
                continue
            location_label: str = _LOCATION_TO_STRATEGY_LABEL[location]
            span.set_attribute(ATTR_LOCATION, location_label)
            span.set_attribute(ATTR_OUTCOME, OUTCOME_SUCCESS)
            span.set_status(Status(StatusCode.OK))
            JWT_EXTRACT_DURATION.record(
                amount=perf_counter() - start_ts,
                attributes={
                    ATTR_OUTCOME: OUTCOME_SUCCESS,
                    ATTR_LOCATION: location_label,
                    **identifier_attributes,
                },
            )
            return token

        if last_attempted_location is not None:
            span.set_attribute(ATTR_LOCATION, _LOCATION_TO_STRATEGY_LABEL[last_attempted_location])

        if last_invalid_error is not None:
            outcome = OUTCOME_INVALID_JWT
            span.set_attribute(ATTR_OUTCOME, outcome)
            span.record_exception(last_invalid_error)
            span.set_status(Status(StatusCode.ERROR, str(last_invalid_error)))
            JWT_EXTRACT_DURATION.record(
                amount=perf_counter() - start_ts,
                attributes={ATTR_OUTCOME: outcome, **identifier_attributes},
            )
            raise last_invalid_error

        outcome = OUTCOME_MISSING_CREDENTIALS
        span.set_attribute(ATTR_OUTCOME, outcome)
        span.set_status(Status(StatusCode.ERROR, "Missing Credentials"))
        JWT_EXTRACT_DURATION.record(
            amount=perf_counter() - start_ts,
            attributes={ATTR_OUTCOME: outcome, **identifier_attributes},
        )
        raise MissingJWTCredentialsError(message="Missing Credentials")
