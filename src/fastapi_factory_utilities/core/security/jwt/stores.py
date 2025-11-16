"""Provides the JWK stores."""

from abc import ABC, abstractmethod
from asyncio import Lock

from jwt.api_jwk import PyJWK, PyJWKSet


class JWKStoreAbstract(ABC):
    """JWK store abstract class."""

    async def get_jwk(self, kid: str) -> PyJWK:
        """Get the JWK from the store."""
        return (await self.get_jwks())[kid]

    @abstractmethod
    async def get_jwks(self) -> PyJWKSet:
        """Get the JWKS from the store."""
        raise NotImplementedError()

    @abstractmethod
    async def store_jwks(self, jwks: PyJWKSet) -> None:
        """Store the JWKS in the store."""
        raise NotImplementedError()


class JWKStoreMemory(JWKStoreAbstract):
    """JWK store in memory. Concurrent safe."""

    def __init__(self) -> None:
        """Initialize the JWK store in memory."""
        self._jwks: PyJWKSet
        self._lock: Lock = Lock()

    async def get_jwks(self) -> PyJWKSet:
        """Get the JWKS from the store."""
        async with self._lock:
            return self._jwks

    async def store_jwks(self, jwks: PyJWKSet) -> None:
        """Store the JWKS in the store."""
        async with self._lock:
            self._jwks = jwks
