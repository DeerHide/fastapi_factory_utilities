"""Provides the JWK stores."""

from abc import ABC, abstractmethod
from asyncio import Lock

from fastapi import Request
from fastapi.datastructures import State
from jwt import PyJWK, PyJWKSet

from fastapi_factory_utilities.core.security.types import OAuth2Issuer
from fastapi_factory_utilities.core.services.hydra import (
    HydraIntrospectGenericService,
    HydraOperationError,
    HydraTokenIntrospectObject,
)

from .exceptions import HydraJWKSStoreError


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


async def configure_jwks_in_memory_store_from_hydra_introspect_services(
    introspect_service_list: list[HydraIntrospectGenericService[HydraTokenIntrospectObject]],
) -> JWKStoreMemory:
    """Configure the JWKS in memory store from the Hydra introspect services."""
    jwk_store = JWKStoreMemory()
    try:
        for introspect_service in introspect_service_list:
            jwks: list[PyJWK] = await introspect_service.get_wellknown_jwks()
            for key in jwks:
                assert key.key_id is not None
                await jwk_store.add_jwk(introspect_service.get_issuer(), key)
    except (HydraOperationError, RuntimeError) as e:
        raise HydraJWKSStoreError("Failed to get the JWKS from the introspect services") from e
    return jwk_store


class DependsHydraJWKStoreMemory:
    """Dependency for the Hydra JWKS store in memory."""

    DEPENDENCY_KEY: str = "hydra_jwks_store_memory"

    @classmethod
    def export_from_state(cls, state: State) -> JWKStoreMemory:
        """Export the Hydra JWKS store in memory from the state."""
        jwk_store: JWKStoreMemory | None = getattr(state, cls.DEPENDENCY_KEY, None)
        if jwk_store is None:
            raise HydraJWKSStoreError("Hydra JWKS store in memory not found in the state")
        return jwk_store

    @classmethod
    def import_to_state(cls, state: State, jwk_store: JWKStoreMemory) -> None:
        """Import the Hydra JWKS store in memory to the state."""
        setattr(state, cls.DEPENDENCY_KEY, jwk_store)

    def __call__(self, request: Request) -> JWKStoreMemory:
        """Dependency for the Hydra JWKS store in memory."""
        return self.export_from_state(state=request.app.state)
