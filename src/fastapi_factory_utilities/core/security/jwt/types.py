"""Provides the JWT bearer token types."""

from typing import NewType

JWTToken = NewType("JWTToken", str)
OAuth2Scope = NewType("OAuth2Scope", str)
OAuth2Audience = NewType("OAuth2Audience", str)
OAuth2Issuer = NewType("OAuth2Issuer", str)
OAuth2Subject = NewType("OAuth2Subject", str)
