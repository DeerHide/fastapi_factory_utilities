"""Provides security-related functions for the API."""

from .configs import JWTBearerAuthenticationConfig
from .decoders import JWTBearerTokenDecoder, JWTBearerTokenDecoderAbstract, decode_jwt_token_payload
from .exceptions import (
    InvalidJWTError,
    InvalidJWTPayploadError,
    JWTAuthenticationError,
    MissingJWTCredentialsError,
    NotVerifiedJWTError,
)
from .objects import JWTPayload
from .services import (
    JWTAuthenticationService,
    JWTAuthenticationServiceAbstract,
)
from .stores import JWKStoreAbstract, JWKStoreMemory
from .types import JWTToken, OAuth2Audience, OAuth2Issuer, OAuth2Scope, OAuth2Subject
from .verifiers import JWTNoneVerifier, JWTVerifierAbstract

__all__: list[str] = [
    "InvalidJWTError",
    "InvalidJWTPayploadError",
    "JWKStoreAbstract",
    "JWKStoreMemory",
    "JWTAuthenticationError",
    "JWTAuthenticationService",
    "JWTAuthenticationServiceAbstract",
    "JWTBearerAuthenticationConfig",
    "JWTBearerTokenDecoder",
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
