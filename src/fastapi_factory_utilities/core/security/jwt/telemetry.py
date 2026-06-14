"""OpenTelemetry instrumentation primitives for JWT operations.

Centralizes the tracer, meter, histogram instruments, attribute keys, outcome
constants, and the identifier ``ContextVar`` shared by all JWT layers
(extract, decode, verify, authenticate, JWKS access).

Keeping these primitives in a single module avoids touching the public
constructors of decoders/verifiers: the active authentication identifier
(``customer``, ``internal``, ...) is propagated to child operations through a
``ContextVar`` rather than through extra constructor parameters.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Final

from opentelemetry import metrics, trace

__all__: list[str] = [
    "ATTR_ISSUER",
    "ATTR_KID",
    "ATTR_LOCATION",
    "ATTR_OUTCOME",
    "ATTR_PAYLOAD_IDENTIFIER",
    "JWT_AUTHENTICATE_DURATION",
    "JWT_DECODE_DURATION",
    "JWT_EXTRACT_DURATION",
    "JWT_IDENTIFIER_CTX",
    "JWT_JWKS_BOOTSTRAP_DURATION",
    "JWT_JWKS_GET_DURATION",
    "JWT_VERIFY_DURATION",
    "METER",
    "OUTCOME_EXPIRED",
    "OUTCOME_INTERNAL_ERROR",
    "OUTCOME_INVALID_JWT",
    "OUTCOME_INVALID_PAYLOAD",
    "OUTCOME_MISSING_CREDENTIALS",
    "OUTCOME_NOT_VERIFIED",
    "OUTCOME_SUCCESS",
    "TRACER",
]

INSTRUMENTING_MODULE_NAME: Final[str] = "fastapi_factory_utilities.security.jwt"

TRACER: Final[trace.Tracer] = trace.get_tracer(INSTRUMENTING_MODULE_NAME)
METER: Final[metrics.Meter] = metrics.get_meter(INSTRUMENTING_MODULE_NAME)

# --------------------------------------------------------------------------- #
# Histograms (OTel best practice: histograms inherently track count + sum +   #
# distribution, so no companion counters are needed).                         #
# --------------------------------------------------------------------------- #

JWT_AUTHENTICATE_DURATION: Final[metrics.Histogram] = METER.create_histogram(
    name="jwt.authentication.duration",
    unit="s",
    description="Duration of the full JWT authentication flow (extract + decode + verify).",
)

JWT_EXTRACT_DURATION: Final[metrics.Histogram] = METER.create_histogram(
    name="jwt.extract.duration",
    unit="s",
    description="Duration of JWT bearer token extraction from the incoming request.",
)

JWT_DECODE_DURATION: Final[metrics.Histogram] = METER.create_histogram(
    name="jwt.decode.duration",
    unit="s",
    description="Duration of JWT bearer token signature verification and payload decoding.",
)

JWT_VERIFY_DURATION: Final[metrics.Histogram] = METER.create_histogram(
    name="jwt.verify.duration",
    unit="s",
    description="Duration of JWT bearer token verification (e.g. Hydra introspection).",
)

JWT_JWKS_GET_DURATION: Final[metrics.Histogram] = METER.create_histogram(
    name="jwt.jwks.get.duration",
    unit="s",
    description="Duration of JWK lookup by ``kid`` from the in-memory JWKS store.",
)

JWT_JWKS_BOOTSTRAP_DURATION: Final[metrics.Histogram] = METER.create_histogram(
    name="jwt.jwks.bootstrap.duration",
    unit="s",
    description="Duration of bootstrapping the in-memory JWKS store from Hydra introspect services.",
)

# --------------------------------------------------------------------------- #
# Attribute keys                                                              #
# --------------------------------------------------------------------------- #

ATTR_PAYLOAD_IDENTIFIER: Final[str] = "jwt.identifier"
"""Auth-service identifier (e.g. ``customer``, ``internal``)."""

ATTR_OUTCOME: Final[str] = "jwt.outcome"
"""Outcome of the JWT operation. See ``OUTCOME_*`` constants."""

ATTR_LOCATION: Final[str] = "jwt.location"
"""Strategy that produced the token (``header``, ``authorization_bearer``, ``cookie``)."""

ATTR_KID: Final[str] = "jwt.kid"
"""Key id read from the unverified JWT header."""

ATTR_ISSUER: Final[str] = "jwt.iss"
"""Issuer associated with the JWK that decoded the token."""

# --------------------------------------------------------------------------- #
# Outcome constants                                                           #
# --------------------------------------------------------------------------- #

OUTCOME_SUCCESS: Final[str] = "success"
OUTCOME_MISSING_CREDENTIALS: Final[str] = "missing_credentials"
OUTCOME_INVALID_JWT: Final[str] = "invalid_jwt"
OUTCOME_EXPIRED: Final[str] = "expired"
OUTCOME_INVALID_PAYLOAD: Final[str] = "invalid_payload"
OUTCOME_NOT_VERIFIED: Final[str] = "not_verified"
OUTCOME_INTERNAL_ERROR: Final[str] = "internal_error"

# --------------------------------------------------------------------------- #
# Identifier propagation                                                      #
# --------------------------------------------------------------------------- #

JWT_IDENTIFIER_CTX: Final[ContextVar[str | None]] = ContextVar("jwt_identifier", default=None)
"""Holds the active auth-service identifier so child JWT operations can tag spans/metrics."""


def get_identifier_attributes() -> dict[str, str]:
    """Return the identifier attribute as a dict, or an empty dict when unset.

    Returns:
        dict[str, str]: Attribute mapping suitable for span/metric attributes.
    """
    identifier: str | None = JWT_IDENTIFIER_CTX.get()
    if identifier is None:
        return {}
    return {ATTR_PAYLOAD_IDENTIFIER: identifier}
