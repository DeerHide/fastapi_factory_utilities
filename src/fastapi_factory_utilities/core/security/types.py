"""Provides the security types."""

from typing import NewType

JWTToken = NewType("JWTToken", str)
OAuth2Scope = NewType("OAuth2Scope", str)
OAuth2Audience = NewType("OAuth2Audience", str)
OAuth2Issuer = NewType("OAuth2Issuer", str)
OAuth2Subject = NewType("OAuth2Subject", str)

__all__: list[str] = [
    "JWTToken",
    "OAuth2Audience",
    "OAuth2Issuer",
    "OAuth2Scope",
    "OAuth2Subject",
]
