"""Provides the exceptions for the JWT authentication."""

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError


class JWTAuthenticationError(FastAPIFactoryUtilitiesError):
    """JWT authentication error."""


class MissingJWTCredentialsError(JWTAuthenticationError):
    """Missing JWT authentication credentials error."""


class InvalidJWTError(JWTAuthenticationError):
    """Invalid JWT authentication credentials error."""


class InvalidJWTPayploadError(JWTAuthenticationError):
    """Invalid JWT payload error."""


class NotVerifiedJWTError(JWTAuthenticationError):
    """Not verified JWT error."""
