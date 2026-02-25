"""Provides security-related functions for the API."""

from .configs import (
    DependsJWTBearerAuthenticationConfig,
    JWTBearerAuthenticationConfig,
    JWTBearerAuthenticationConfigBuilder,
)
from .decoders import GenericJWTBearerTokenDecoder, JWTBearerTokenDecoderAbstract, decode_jwt_token_payload
from .exceptions import (
    InvalidJWTError,
    InvalidJWTPayploadError,
    JWTAuthenticationError,
    JWTBearerAuthenticationConfigBuilderError,
    MissingJWTCredentialsError,
    NotVerifiedJWTError,
)
from .objects import JWTPayload
from .services import JWTAuthenticationServiceAbstract
from .stores import (
    DependsHydraJWKStoreMemory,
    JWKStoreAbstract,
    JWKStoreMemory,
    configure_jwks_in_memory_store_from_hydra_introspect_services,
)
from .verifiers import GenericHydraJWTVerifier, JWTNoneVerifier, JWTVerifierAbstract

__all__: list[str] = [
    "DependsHydraJWKStoreMemory",
    "DependsJWTBearerAuthenticationConfig",
    "GenericHydraJWTVerifier",
    "GenericJWTBearerTokenDecoder",
    "InvalidJWTError",
    "InvalidJWTPayploadError",
    "JWKStoreAbstract",
    "JWKStoreMemory",
    "JWTAuthenticationError",
    "JWTAuthenticationServiceAbstract",
    "JWTBearerAuthenticationConfig",
    "JWTBearerAuthenticationConfigBuilder",
    "JWTBearerAuthenticationConfigBuilderError",
    "JWTBearerTokenDecoderAbstract",
    "JWTNoneVerifier",
    "JWTPayload",
    "JWTVerifierAbstract",
    "MissingJWTCredentialsError",
    "NotVerifiedJWTError",
    "configure_jwks_in_memory_store_from_hydra_introspect_services",
    "decode_jwt_token_payload",
]
