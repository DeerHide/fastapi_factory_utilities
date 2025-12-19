"""Provides enums for Kratos."""

from enum import StrEnum


class AuthenticatorAssuranceLevelEnum(StrEnum):
    """Enum for Authenticator Assurance Level (AAL)."""

    AAL0 = "aal0"
    AAL1 = "aal1"
    AAL2 = "aal2"
    AAL3 = "aal3"


class AuthenticationMethodEnum(StrEnum):
    """Enum for Authentication Method."""

    PASSWORD = "password"
    OIDC = "oidc"
    TOTP = "totp"
    LOOKUP_SECRET = "lookup_secret"
    WEBAUTHN = "webauthn"
    CODE = "code"
    PASSKEY = "passkey"
    PROFILE = "profile"
    SAML = "saml"
    LINK_RECOVERY = "link_recovery"
    CODE_RECOVERY = "code_recovery"


class KratosIdentityStateEnum(StrEnum):
    """Enum for Identity State."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class KratosFlowTypeEnum(StrEnum):
    """Enum for Flow Type."""

    API = "api"
    BROWSER = "browser"


class KratosIdentityPatchOpEnum(StrEnum):
    """Enum for Kratos identity patch operation."""

    ADD = "add"
    REMOVE = "remove"
    REPLACE = "replace"
    MOVE = "move"
    COPY = "copy"
    TEST = "test"
