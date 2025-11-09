"""Provides security-related functions for the API."""

from .configs import JWTBearerAuthenticationConfig
from .decoders import (
    JWTBearerTokenDecoder,
    JWTBearerTokenDecoderAbstract,
)
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
from .types import OAuth2Scope
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
    "JWTVerifierAbstract",
    "MissingJWTCredentialsError",
    "NotVerifiedJWTError",
    "OAuth2Scope",
]
