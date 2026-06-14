"""Provides the JWT bearer token validator."""

from abc import ABC, abstractmethod
from time import perf_counter
from typing import Generic, TypeVar, cast

from opentelemetry.trace import SpanKind, Status, StatusCode

from fastapi_factory_utilities.core.security.types import JWTToken
from fastapi_factory_utilities.core.services.hydra import (
    HydraAccessToken,
    HydraIntrospectGenericService,
    HydraOperationError,
    HydraTokenIntrospectObject,
)

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

    def __init__(self, hydra_introspect_service: HydraIntrospectGenericService[HydraIntrospectObjectGeneric]) -> None:
        """Initialize the Generic Hydra JWT verifier."""
        self._hydra_introspect_service: HydraIntrospectGenericService[HydraIntrospectObjectGeneric] = (
            hydra_introspect_service
        )
        self._introspect_object: HydraIntrospectObjectGeneric | None = None

    @property
    def introspect_object(self) -> HydraIntrospectObjectGeneric:
        """Get the introspect object.

        Returns:
            HydraTokenIntrospectObject: The introspect object.
        """
        assert self._introspect_object is not None
        return self._introspect_object

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

            span.set_attribute(ATTR_OUTCOME, OUTCOME_SUCCESS)
            span.set_status(Status(StatusCode.OK))
            JWT_VERIFY_DURATION.record(
                amount=perf_counter() - start_ts,
                attributes={ATTR_OUTCOME: OUTCOME_SUCCESS, **identifier_attributes},
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
