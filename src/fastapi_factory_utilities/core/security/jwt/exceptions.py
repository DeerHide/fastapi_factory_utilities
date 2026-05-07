"""Provides the exceptions for the JWT authentication."""

import logging

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError


class JWTAuthenticationError(FastAPIFactoryUtilitiesError):
    """JWT authentication error."""

    DEFAULT_LOGGING_LEVEL: int = logging.DEBUG


class MissingJWTCredentialsError(JWTAuthenticationError):
    """Missing JWT authentication credentials error."""


class InvalidJWTError(JWTAuthenticationError):
    """Invalid JWT authentication credentials error."""


class InvalidJWTPayploadError(JWTAuthenticationError):
    """Invalid JWT payload error."""


class NotVerifiedJWTError(JWTAuthenticationError):
    """Not verified JWT error."""


class JWTBearerAuthenticationConfigBuilderError(FastAPIFactoryUtilitiesError):
    """JWT bearer authentication configuration builder error."""


class HydraJWKSStoreError(FastAPIFactoryUtilitiesError):
    """Hydra JWKS store error."""


class ExpiredJWTError(InvalidJWTError):
    """Expired JWT error."""
