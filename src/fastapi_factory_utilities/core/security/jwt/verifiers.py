"""Provides the JWT bearer token validator."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, cast

from fastapi_factory_utilities.core.security.types import JWTToken
from fastapi_factory_utilities.core.services.hydra import (
    HydraAccessToken,
    HydraIntrospectGenericService,
    HydraOperationError,
    HydraTokenIntrospectObject,
)

from .exceptions import InvalidJWTError
from .objects import JWTPayload

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

        Args:
            jwt_token: The JWT token.
            jwt_payload: The JWT payload.
        """
        try:
            self._introspect_object = await self._hydra_introspect_service.introspect(
                token=cast(HydraAccessToken, jwt_token)
            )
        except HydraOperationError as e:
            raise InvalidJWTError("Failed to introspect the JWT token") from e

        if self._introspect_object.active is False:
            raise InvalidJWTError("JWT token is not active")


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
