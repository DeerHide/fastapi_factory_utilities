"""Provides the JWK stores."""

from abc import ABC, abstractmethod
from asyncio import Lock

from jwt import PyJWK, PyJWKSet

from .types import OAuth2Issuer


class JWKStoreAbstract(ABC):
    """JWK store abstract class."""

    def __init__(self) -> None:
        """Initialize the JWK store."""
        self._issuer_by_kid: dict[str, OAuth2Issuer] = {}
        self._jwk_by_kid: dict[str, PyJWK] = {}

    @abstractmethod
    async def get_jwk(self, kid: str) -> PyJWK:
        """Get the JWK from the store."""
        raise NotImplementedError()

    @abstractmethod
    async def get_issuer_by_kid(self, kid: str) -> OAuth2Issuer:
        """Get the issuer by kid from the store."""
        raise NotImplementedError()

    @abstractmethod
    async def get_jwks(self, issuer: OAuth2Issuer) -> PyJWKSet:
        """Get the JWKS from the store."""
        raise NotImplementedError()

    @abstractmethod
    async def add_jwk(self, issuer: OAuth2Issuer, jwk: PyJWK) -> None:
        """Add a JWK to the store."""
        raise NotImplementedError()


class JWKStoreMemory(JWKStoreAbstract):
    """JWK store in memory. Concurrent safe."""

    def __init__(self) -> None:
        """Initialize the JWK store in memory."""
        super().__init__()
        self._lock: Lock = Lock()

    async def get_jwk(self, kid: str) -> PyJWK:
        """Get the JWK from the store."""
        async with self._lock:
            return self._jwk_by_kid[kid]

    async def get_issuer_by_kid(self, kid: str) -> OAuth2Issuer:
        """Get the issuer by kid from the store."""
        async with self._lock:
            return self._issuer_by_kid[kid]

    async def get_jwks(self, issuer: OAuth2Issuer) -> PyJWKSet:
        """Get the JWKS from the store."""
        async with self._lock:
            jwks: list[PyJWK] = []
            for kid, jwk in self._jwk_by_kid.items():
                if self._issuer_by_kid[kid] == issuer:
                    jwks.append(jwk)
            return PyJWKSet.from_dict(
                {
                    "keys": [jwk._jwk_data for jwk in jwks]  # pylint: disable=protected-access # pyright: ignore[reportPrivateUsage]
                }
            )

    async def add_jwk(self, issuer: OAuth2Issuer, jwk: PyJWK) -> None:
        """Add a JWK to the store."""
        async with self._lock:
            if jwk.key_id is None:
                raise ValueError("JWK key ID is required")
            self._jwk_by_kid[jwk.key_id] = jwk
            self._issuer_by_kid[jwk.key_id] = issuer
