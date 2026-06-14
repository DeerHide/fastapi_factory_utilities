"""Provides the JWT bearer authentication service."""

from http import HTTPStatus
from time import perf_counter
from typing import Generic, TypeVar

from fastapi import HTTPException, Request
from opentelemetry.trace import SpanKind, Status, StatusCode

from fastapi_factory_utilities.core.security.abstracts import AuthenticationAbstract
from fastapi_factory_utilities.core.security.types import JWTToken, OAuth2Issuer

from .configs import JWTBearerAuthenticationConfig
from .decoders import JWTBearerTokenDecoderAbstract
from .exceptions import (
    ExpiredJWTError,
    InvalidJWTError,
    InvalidJWTPayploadError,
    MissingJWTCredentialsError,
    NotVerifiedJWTError,
)
from .extraction_strategies import extract_token_from_request
from .objects import JWTPayload
from .telemetry import (
    ATTR_OUTCOME,
    ATTR_PAYLOAD_IDENTIFIER,
    JWT_AUTHENTICATE_DURATION,
    JWT_IDENTIFIER_CTX,
    OUTCOME_EXPIRED,
    OUTCOME_INTERNAL_ERROR,
    OUTCOME_INVALID_JWT,
    OUTCOME_INVALID_PAYLOAD,
    OUTCOME_MISSING_CREDENTIALS,
    OUTCOME_NOT_VERIFIED,
    OUTCOME_SUCCESS,
    TRACER,
)
from .verifiers import JWTVerifierAbstract

JWTBearerPayloadGeneric = TypeVar("JWTBearerPayloadGeneric", bound=JWTPayload)


class JWTAuthenticationServiceAbstract(AuthenticationAbstract, Generic[JWTBearerPayloadGeneric]):
    """JWT authentication service.

    This service is the orchestrator for the JWT bearer authentication.
    """

    def __init__(
        self,
        identifier: str,
        jwt_bearer_authentication_config: JWTBearerAuthenticationConfig,
        jwt_verifier: JWTVerifierAbstract[JWTBearerPayloadGeneric],
        jwt_decoder: JWTBearerTokenDecoderAbstract[JWTBearerPayloadGeneric],
        raise_exception: bool = True,
    ) -> None:
        """Initialize the JWT bearer authentication service.

        Args:
            identifier (str): The identifier of the JWT bearer authentication service.
            jwt_bearer_authentication_config (JWTBearerAuthenticationConfig): The JWT bearer authentication
            configuration.
            jwt_verifier (JWTVerifierAbstract): The JWT bearer token verifier.
            jwt_decoder (JWTBearerTokenDecoderAbstract[JWTBearerPayloadGeneric]): The JWT bearer token decoder.
            raise_exception (bool, optional): Whether to raise an exception or return None. Defaults to True.
        """
        # Configuration and Behavior
        self._identifier: str = identifier
        self._jwt_bearer_authentication_config: JWTBearerAuthenticationConfig = jwt_bearer_authentication_config
        self._issuer: OAuth2Issuer = jwt_bearer_authentication_config.issuer
        self._jwt_verifier: JWTVerifierAbstract[JWTBearerPayloadGeneric] = jwt_verifier
        self._jwt_decoder: JWTBearerTokenDecoderAbstract[JWTBearerPayloadGeneric] = jwt_decoder
        # Runtime variables
        self._jwt: JWTToken | None = None
        self._jwt_payload: JWTBearerPayloadGeneric | None = None
        super().__init__(raise_exception=raise_exception)

    @property
    def verifier(self) -> JWTVerifierAbstract[JWTBearerPayloadGeneric]:
        """Get the JWT bearer token verifier.

        Returns:
            JWTVerifierAbstract[JWTBearerPayloadGeneric]: The JWT bearer token verifier.
        """
        return self._jwt_verifier

    @property
    def decoder(self) -> JWTBearerTokenDecoderAbstract[JWTBearerPayloadGeneric]:
        """Get the JWT bearer token decoder.

        Returns:
            JWTBearerTokenDecoderAbstract[JWTBearerPayloadGeneric]: The JWT bearer token decoder.
        """
        return self._jwt_decoder

    @property
    def payload(self) -> JWTBearerPayloadGeneric | None:
        """Get the JWT bearer payload.

        Returns:
            JWTBearerPayloadGeneric | None: The JWT bearer payload, or None if not authenticated yet.
        """
        return self._jwt_payload

    async def authenticate(self, request: Request) -> None:
        """Authenticate the JWT bearer token.

        Emits the parent ``jwt.authenticate`` span (with child ``jwt.extract``,
        ``jwt.decode``, ``jwt.verify`` spans), records
        ``jwt.authentication.duration``, and propagates the auth-service
        identifier to child layers via :data:`JWT_IDENTIFIER_CTX`.

        Args:
            request (Request): The request object.

        Returns:
            None: If the authentication is successful or not raise_exception is False.

        Raises:
            MissingJWTCredentialsError: If the authorization header is missing.
            InvalidJWTError: If the authorization header is invalid.
            InvalidJWTPayploadError: If the JWT bearer token payload is invalid.
            NotVerifiedJWTError: If the JWT bearer token is not verified.
        """
        identifier_attributes: dict[str, str] = {ATTR_PAYLOAD_IDENTIFIER: self._identifier}
        identifier_token = JWT_IDENTIFIER_CTX.set(self._identifier)
        start_ts: float = perf_counter()
        outcome: str = OUTCOME_INTERNAL_ERROR
        try:
            with TRACER.start_as_current_span(
                name="jwt.authenticate", kind=SpanKind.INTERNAL, attributes=identifier_attributes
            ) as span:
                try:
                    try:
                        self._jwt = extract_token_from_request(
                            request=request,
                            jwt_bearer_authentication_config=self._jwt_bearer_authentication_config,
                        )
                    except MissingJWTCredentialsError as error:
                        outcome = OUTCOME_MISSING_CREDENTIALS
                        self.raise_exception(
                            HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=str(error))
                        )
                        return
                    except InvalidJWTError as error:
                        outcome = OUTCOME_INVALID_JWT
                        self.raise_exception(
                            HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=str(error))
                        )
                        return

                    try:
                        self._jwt_payload = await self._jwt_decoder.decode_payload(jwt_token=self._jwt)
                    except ExpiredJWTError as error:
                        outcome = OUTCOME_EXPIRED
                        self.raise_exception(
                            HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=str(error))
                        )
                        return
                    except InvalidJWTPayploadError as error:
                        outcome = OUTCOME_INVALID_PAYLOAD
                        self.raise_exception(
                            HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=str(error))
                        )
                        return
                    except InvalidJWTError as error:
                        outcome = OUTCOME_INVALID_JWT
                        self.raise_exception(
                            HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=str(error))
                        )
                        return

                    try:
                        await self._jwt_verifier.verify(jwt_token=self._jwt, jwt_payload=self._jwt_payload)
                    except NotVerifiedJWTError as error:
                        outcome = OUTCOME_NOT_VERIFIED
                        self.raise_exception(
                            HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=str(error))
                        )
                        return
                    except InvalidJWTError as error:
                        outcome = OUTCOME_INVALID_JWT
                        self.raise_exception(
                            HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=str(error))
                        )
                        return

                    outcome = OUTCOME_SUCCESS
                    return
                finally:
                    span.set_attribute(ATTR_OUTCOME, outcome)
                    if outcome == OUTCOME_SUCCESS:
                        span.set_status(Status(StatusCode.OK))
                    else:
                        span.set_status(Status(StatusCode.ERROR, outcome))
        finally:
            JWT_IDENTIFIER_CTX.reset(identifier_token)
            JWT_AUTHENTICATE_DURATION.record(
                amount=perf_counter() - start_ts,
                attributes={ATTR_OUTCOME: outcome, **identifier_attributes},
            )
