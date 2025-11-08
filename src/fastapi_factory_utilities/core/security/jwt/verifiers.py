"""Provides the JWT bearer token validator."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from .objects import JWTPayload
from .types import JWTToken

JWTBearerPayloadGeneric = TypeVar("JWTBearerPayloadGeneric", bound=JWTPayload)


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
