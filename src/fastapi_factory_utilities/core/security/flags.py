"""Provides flags for security."""

from enum import Flag, auto


class AuthenticationMethodsFlag(Flag):
    """Authentication Flags."""

    JWT = auto()
    KRATOS = auto()
