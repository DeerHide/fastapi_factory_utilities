"""Provides security-related functions for the API."""

from .configs import JWTBearerAuthenticationConfig
from .decoders import GenericJWTBearerTokenDecoder, JWTBearerTokenDecoderAbstract, decode_jwt_token_payload
from .exceptions import (
    InvalidJWTError,
    InvalidJWTPayploadError,
    JWTAuthenticationError,
    MissingJWTCredentialsError,
    NotVerifiedJWTError,
)
from .objects import JWTPayload
from .services import JWTAuthenticationServiceAbstract
from .stores import JWKStoreAbstract, JWKStoreMemory
from .types import JWTToken, OAuth2Audience, OAuth2Issuer, OAuth2Scope, OAuth2Subject
from .verifiers import GenericHydraJWTVerifier, JWTNoneVerifier, JWTVerifierAbstract

__all__: list[str] = [
    "GenericHydraJWTVerifier",
    "GenericJWTBearerTokenDecoder",
    "InvalidJWTError",
    "InvalidJWTPayploadError",
    "JWKStoreAbstract",
    "JWKStoreMemory",
    "JWTAuthenticationError",
    "JWTAuthenticationServiceAbstract",
    "JWTBearerAuthenticationConfig",
    "JWTBearerTokenDecoderAbstract",
    "JWTNoneVerifier",
    "JWTPayload",
    "JWTToken",
    "JWTVerifierAbstract",
    "MissingJWTCredentialsError",
    "NotVerifiedJWTError",
    "OAuth2Audience",
    "OAuth2Issuer",
    "OAuth2Scope",
    "OAuth2Subject",
    "decode_jwt_token_payload",
]
