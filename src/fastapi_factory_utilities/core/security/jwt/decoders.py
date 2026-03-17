"""Provides the JWT bearer token decoders.

Can be implemented to support different JWT bearer token formats or additional claims.
https://www.iana.org/assignments/jwt/jwt.xhtml#claims
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar, get_args

from jwt import ExpiredSignatureError, InvalidTokenError, decode, get_unverified_header
from jwt.api_jwk import PyJWK
from pydantic import ValidationError

from fastapi_factory_utilities.core.security.types import JWTToken, OAuth2Issuer, OAuth2Subject

from .configs import JWTBearerAuthenticationConfig
from .exceptions import ExpiredJWTError, InvalidJWTError, InvalidJWTPayploadError
from .objects import JWTPayload
from .stores import JWKStoreAbstract

JWTBearerPayloadGeneric = TypeVar("JWTBearerPayloadGeneric", bound=JWTPayload)


async def decode_jwt_token_payload(
    jwt_token: JWTToken,
    public_key: PyJWK,
    jwt_bearer_authentication_config: JWTBearerAuthenticationConfig,
    subject: OAuth2Subject | None = None,
    issuer: OAuth2Issuer | None = None,
) -> dict[str, Any]:
    """Decode the JWT bearer token payload.

    Args:
        jwt_token (JWTToken): The JWT bearer token.
        public_key (PyJWK): The public key.
        jwt_bearer_authentication_config (JWTBearerAuthenticationConfig): The JWT bearer authentication configuration.
        subject (OAuth2Subject | None): The subject.
        issuer (OAuth2Issuer | None): The issuer.

    Returns:
        dict[str, Any]: The decoded JWT bearer token payload.

    Raises:
        ExpiredJWTError: If the JWT bearer token is expired.
        InvalidJWTError: If the JWT bearer token is invalid.
    """
    # Additional kwargs for the decode function
    kwargs: dict[str, Any] = {}
    kwargs["issuer"] = issuer or jwt_bearer_authentication_config.issuer
    if jwt_bearer_authentication_config.authorized_audiences:
        kwargs["audience"] = jwt_bearer_authentication_config.authorized_audiences
    if subject:
        kwargs["subject"] = subject
    # Decode the JWT bearer token payload
    try:
        return decode(
            jwt=jwt_token,
            key=public_key,
            algorithms=jwt_bearer_authentication_config.authorized_algorithms,
            options={"verify_signature": True},
            **kwargs,
        )
    except ExpiredSignatureError as e:
        raise ExpiredJWTError("The JWT bearer token is expired") from e
    except InvalidTokenError as e:
        raise InvalidJWTError("Failed to decode the JWT bearer token payload") from e


class JWTBearerTokenDecoderAbstract(ABC, Generic[JWTBearerPayloadGeneric]):
    """JWT bearer token decoder."""

    def get_kid_from_jwt_unsafe_header(self, jwt_token: JWTToken) -> str:
        """Get the kid from the JWT header.

        Args:
            jwt_token (JWTToken): The JWT bearer token.

        Returns:
            str: The kid.
        """
        try:
            jwt_unsafe_headers: dict[str, Any] = get_unverified_header(jwt_token)
            return jwt_unsafe_headers["kid"]
        except (KeyError, InvalidTokenError) as e:
            raise InvalidJWTError("Failed to get the kid from the JWT header") from e

    @abstractmethod
    async def decode_payload(self, jwt_token: JWTToken) -> JWTBearerPayloadGeneric:
        """Decode the JWT bearer token payload.

        Args:
            jwt_token (JWTToken): The JWT bearer token.

        Returns:
            JWTBearerPayloadGeneric: The decoded JWT bearer token payload.

        Raises:
            InvalidJWTError: If the JWT bearer token is invalid.
            InvalidJWTPayploadError: If the JWT bearer token payload is invalid.
        """
        raise NotImplementedError()


GenericJWTPayload = TypeVar("GenericJWTPayload", bound=JWTPayload)


class GenericJWTBearerTokenDecoder(JWTBearerTokenDecoderAbstract[GenericJWTPayload], Generic[GenericJWTPayload]):
    """JWT bearer token classic decoder."""

    def __init__(
        self, jwt_bearer_authentication_config: JWTBearerAuthenticationConfig, jwks_store: JWKStoreAbstract
    ) -> None:
        """Initialize the JWT bearer token classic decoder.

        Args:
            jwt_bearer_authentication_config (JWTBearerAuthenticationConfig): The JWT bearer authentication
            configuration.
            jwks_store (JWKStoreAbstract): The JWKS store.
        """
        self._jwt_bearer_authentication_config: JWTBearerAuthenticationConfig = jwt_bearer_authentication_config
        self._jwks_store: JWKStoreAbstract = jwks_store
        self._payload_model: type[GenericJWTPayload] = get_args(self.__orig_bases__[0])[0]  # type: ignore[attr-defined]

    async def decode_payload(self, jwt_token: JWTToken) -> GenericJWTPayload:
        """Decode the JWT bearer token."""
        # Get the kid from the JWT header
        kid: str = self.get_kid_from_jwt_unsafe_header(jwt_token=jwt_token)
        # Get the JWK from the JWKS store
        jwk: PyJWK = await self._jwks_store.get_jwk(kid=kid)
        issuer: OAuth2Issuer = await self._jwks_store.get_issuer_by_kid(kid=kid)
        # Decode the JWT bearer token payload
        jwt_decoded: dict[str, Any] = await decode_jwt_token_payload(
            jwt_token=jwt_token,
            public_key=jwk,
            jwt_bearer_authentication_config=self._jwt_bearer_authentication_config,
            issuer=issuer,
        )
        try:
            return self._payload_model.model_validate(jwt_decoded)
        except ValidationError as e:
            raise InvalidJWTPayploadError("Failed to validate the JWT bearer token payload") from e
