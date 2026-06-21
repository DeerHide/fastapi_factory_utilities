"""Provides the JWT bearer token validator."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from time import perf_counter
from typing import Generic, TypeVar, cast

from cacheout import Cache  # type: ignore[attr-defined]
from opentelemetry.trace import Span, SpanKind, Status, StatusCode

from fastapi_factory_utilities.core.security.types import JWTToken
from fastapi_factory_utilities.core.services.hydra import (
    HydraAccessToken,
    HydraIntrospectGenericService,
    HydraOperationError,
    HydraTokenIntrospectObject,
)

from .configs import JWTBearerAuthenticationConfig
from .exceptions import InvalidJWTError
from .objects import JWTPayload
from .telemetry import (
    ATTR_OUTCOME,
    JWT_VERIFY_DURATION,
    OUTCOME_INVALID_JWT,
    OUTCOME_NOT_VERIFIED,
    OUTCOME_SUCCESS,
    TRACER,
    get_identifier_attributes,
)

JWTBearerPayloadGeneric = TypeVar("JWTBearerPayloadGeneric", bound=JWTPayload)
HydraIntrospectObjectGeneric = TypeVar("HydraIntrospectObjectGeneric", bound=HydraTokenIntrospectObject)

# ponytail: single shared Cache, maxsize fixed at first enabled verify(); upgrade path is per-issuer caches.
_INTROSPECT_CACHE: Cache | None = None


def _get_introspect_cache(maxsize: int) -> Cache:
    """Return the module-level introspection cache, creating it on first use.

    Args:
        maxsize: Maximum number of entries the cache may hold.

    Returns:
        Cache: The shared introspection cache instance.
    """
    global _INTROSPECT_CACHE  # noqa: PLW0603
    if _INTROSPECT_CACHE is None:
        _INTROSPECT_CACHE = Cache(maxsize=maxsize)
    return _INTROSPECT_CACHE


def clear_introspect_cache() -> None:
    """Clear the module-level introspection cache (for tests)."""
    global _INTROSPECT_CACHE  # noqa: PLW0603
    if _INTROSPECT_CACHE is not None:
        _INTROSPECT_CACHE.clear()
    _INTROSPECT_CACHE = None


def _compute_introspect_cache_ttl_seconds(
    jwt_payload: JWTPayload,
    cache_ttl_seconds: int,
) -> int:
    """Compute the TTL for a cached introspection result.

    Args:
        jwt_payload: The verified JWT payload.
        cache_ttl_seconds: Configured cache TTL in seconds.

    Returns:
        int: Effective cache TTL in seconds, capped by token expiration.
    """
    remaining_seconds: float = (jwt_payload.exp - datetime.now(tz=UTC)).total_seconds()
    return max(1, min(cache_ttl_seconds, int(remaining_seconds)))


class JWTVerifierAbstract(ABC, Generic[JWTBearerPayloadGeneric]):
    """JWT verifier."""

    @abstractmethod
    async def verify(
        self,
        jwt_token: JWTToken,
        jwt_payload: JWTBearerPayloadGeneric,
    ) -> None:
        """Verify the JWT bearer token.

        Args:
            jwt_token (JWTToken): The JWT bearer token.
            jwt_payload (JWTBearerPayloadGeneric): The JWT bearer payload.

        Raises:
            NotVerifiedJWTError: If the JWT bearer token is not verified.
        """
        raise NotImplementedError()


class GenericHydraJWTVerifier(
    JWTVerifierAbstract[JWTBearerPayloadGeneric], Generic[JWTBearerPayloadGeneric, HydraIntrospectObjectGeneric]
):
    """Generic Hydra JWT verifier."""

    def __init__(
        self,
        hydra_introspect_service: HydraIntrospectGenericService[HydraIntrospectObjectGeneric],
        config: JWTBearerAuthenticationConfig | None = None,
    ) -> None:
        """Initialize the Generic Hydra JWT verifier."""
        self._hydra_introspect_service: HydraIntrospectGenericService[HydraIntrospectObjectGeneric] = (
            hydra_introspect_service
        )
        self._config: JWTBearerAuthenticationConfig | None = config
        self._introspect_object: HydraIntrospectObjectGeneric | None = None

    @property
    def introspect_object(self) -> HydraIntrospectObjectGeneric:
        """Get the introspect object.

        Returns:
            HydraTokenIntrospectObject: The introspect object.
        """
        assert self._introspect_object is not None
        return self._introspect_object

    def _record_verify_success(
        self,
        *,
        span: Span,
        start_ts: float,
        identifier_attributes: dict[str, str],
    ) -> None:
        """Record telemetry for a successful JWT verification."""
        span.set_attribute(ATTR_OUTCOME, OUTCOME_SUCCESS)
        span.set_status(Status(StatusCode.OK))
        JWT_VERIFY_DURATION.record(
            amount=perf_counter() - start_ts,
            attributes={ATTR_OUTCOME: OUTCOME_SUCCESS, **identifier_attributes},
        )

    async def verify(self, jwt_token: JWTToken, jwt_payload: JWTBearerPayloadGeneric) -> None:
        """Verify the JWT token.

        Emits the ``jwt.verify`` span and records ``jwt.verify.duration``.

        Args:
            jwt_token: The JWT token.
            jwt_payload: The JWT payload.
        """
        identifier_attributes: dict[str, str] = get_identifier_attributes()
        start_ts: float = perf_counter()
        with TRACER.start_as_current_span(
            name="jwt.verify", kind=SpanKind.INTERNAL, attributes=identifier_attributes
        ) as span:
            cache_key: str | None = None
            if self._config is not None and self._config.cache_enabled and jwt_payload.jti is not None:
                cache_key = jwt_payload.jti
                cached_introspect_object: HydraIntrospectObjectGeneric | None = _get_introspect_cache(
                    maxsize=self._config.cache_max_entries
                ).get(cache_key)
                if cached_introspect_object is not None:
                    self._introspect_object = cached_introspect_object
                    self._record_verify_success(
                        span=span,
                        start_ts=start_ts,
                        identifier_attributes=identifier_attributes,
                    )
                    return

            try:
                self._introspect_object = await self._hydra_introspect_service.introspect(
                    token=cast(HydraAccessToken, jwt_token)
                )
            except HydraOperationError as e:
                outcome: str = OUTCOME_INVALID_JWT
                span.set_attribute(ATTR_OUTCOME, outcome)
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                JWT_VERIFY_DURATION.record(
                    amount=perf_counter() - start_ts,
                    attributes={ATTR_OUTCOME: outcome, **identifier_attributes},
                )
                raise InvalidJWTError("Failed to introspect the JWT token") from e

            if self._introspect_object.active is False:
                outcome = OUTCOME_NOT_VERIFIED
                span.set_attribute(ATTR_OUTCOME, outcome)
                span.set_status(Status(StatusCode.ERROR, "JWT token is not active"))
                JWT_VERIFY_DURATION.record(
                    amount=perf_counter() - start_ts,
                    attributes={ATTR_OUTCOME: outcome, **identifier_attributes},
                )
                raise InvalidJWTError("JWT token is not active")

            if cache_key is not None and self._config is not None:
                _get_introspect_cache(maxsize=self._config.cache_max_entries).set(
                    cache_key,
                    self._introspect_object,
                    ttl=_compute_introspect_cache_ttl_seconds(
                        jwt_payload=jwt_payload,
                        cache_ttl_seconds=self._config.cache_ttl_seconds,
                    ),
                )

            self._record_verify_success(
                span=span,
                start_ts=start_ts,
                identifier_attributes=identifier_attributes,
            )


class JWTNoneVerifier(JWTVerifierAbstract[JWTPayload]):
    """JWT none verifier."""

    async def verify(self, jwt_token: JWTToken, jwt_payload: JWTPayload) -> None:
        """Verify the JWT bearer token.

        Args:
            jwt_token (JWTToken): The JWT bearer token.
            jwt_payload (JWTBearerPayload): The JWT bearer payload.

        Raises:
            NotVerifiedJWTError: If the JWT bearer token is not verified.
        """
        return
