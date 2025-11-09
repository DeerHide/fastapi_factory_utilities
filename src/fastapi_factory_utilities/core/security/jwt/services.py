"""Provides the JWT bearer authentication service."""

from http import HTTPStatus
from typing import Generic, TypeVar

from fastapi import HTTPException, Request

from fastapi_factory_utilities.core.security.abstracts import AuthenticationAbstract

from .configs import JWTBearerAuthenticationConfig
from .decoders import JWTBearerTokenDecoder, JWTBearerTokenDecoderAbstract
from .exceptions import InvalidJWTError, InvalidJWTPayploadError, MissingJWTCredentialsError, NotVerifiedJWTError
from .objects import JWTPayload
from .stores import JWKStoreAbstract
from .types import JWTToken
from .verifiers import JWTNoneVerifier, JWTVerifierAbstract

JWTBearerPayloadGeneric = TypeVar("JWTBearerPayloadGeneric", bound=JWTPayload)


class JWTAuthenticationServiceAbstract(AuthenticationAbstract, Generic[JWTBearerPayloadGeneric]):
    """JWT authentication service.

    This service is the orchestrator for the JWT bearer authentication.
    """

    def __init__(
        self,
        jwt_bearer_authentication_config: JWTBearerAuthenticationConfig,
        jwt_verifier: JWTVerifierAbstract[JWTBearerPayloadGeneric],
        jwt_decoder: JWTBearerTokenDecoderAbstract[JWTBearerPayloadGeneric],
        raise_exception: bool = True,
    ) -> None:
        """Initialize the JWT bearer authentication service.

        Args:
            jwt_bearer_authentication_config (JWTBearerAuthenticationConfig): The JWT bearer authentication
            configuration.
            jwt_verifier (JWTVerifierAbstract): The JWT bearer token verifier.
            jwt_decoder (JWTBearerTokenDecoderAbstract[JWTBearerPayloadGeneric]): The JWT bearer token decoder.
            raise_exception (bool, optional): Whether to raise an exception or return None. Defaults to True.
        """
        # Configuration and Behavior
        self._jwt_bearer_authentication_config: JWTBearerAuthenticationConfig = jwt_bearer_authentication_config
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

    @property
    def payload(self) -> JWTBearerPayloadGeneric | None:
        """Get the JWT bearer payload.

        Returns:
            JWTBearerPayloadGeneric | None: The JWT bearer payload, or None if not authenticated yet.
        """
        return self._jwt_payload

    async def authenticate(self, request: Request) -> None:
        """Authenticate the JWT bearer token.

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
        authorization_header: str
        try:
            authorization_header = self.extract_authorization_header_from_request(request=request)
            self._jwt = self.extract_bearer_token_from_authorization_header(authorization_header=authorization_header)
        except (MissingJWTCredentialsError, InvalidJWTError) as e:
            return self.raise_exception(HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=str(e)))

        try:
            self._jwt_payload = await self._jwt_decoder.decode_payload(jwt_token=self._jwt)
        except (InvalidJWTError, InvalidJWTPayploadError) as e:
            return self.raise_exception(HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=str(e)))

        try:
            await self._jwt_verifier.verify(jwt_token=self._jwt, jwt_payload=self._jwt_payload)
        except NotVerifiedJWTError as e:
            return self.raise_exception(HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=str(e)))

        return


class JWTAuthenticationService(JWTAuthenticationServiceAbstract[JWTPayload]):
    """JWT bearer authentication service."""

    def __init__(
        self,
        jwt_bearer_authentication_config: JWTBearerAuthenticationConfig,
        jwks_store: JWKStoreAbstract,
        raise_exception: bool = True,
    ) -> None:
        """Initialize the JWT bearer authentication service.

        Don't enforce the public_key from configuration, for the developper to
        provide it through the dependency injection freely from any source.

        Args:
            jwt_bearer_authentication_config (JWTBearerAuthenticationConfig): The JWT bearer authentication
            configuration.
            jwks_store (JWKStoreAbstract): The JWKS store.
            raise_exception (bool, optional): Whether to raise an exception or return None. Defaults to True.
        """
        super().__init__(
            jwt_bearer_authentication_config=jwt_bearer_authentication_config,
            jwt_verifier=JWTNoneVerifier(),
            jwt_decoder=JWTBearerTokenDecoder(
                jwt_bearer_authentication_config=jwt_bearer_authentication_config, jwks_store=jwks_store
            ),
            raise_exception=raise_exception,
        )
