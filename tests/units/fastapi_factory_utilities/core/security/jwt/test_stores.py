"""Unit tests for the JWK stores."""

import asyncio
from typing import cast

import pytest
from jwt import PyJWK, PyJWKSet

from fastapi_factory_utilities.core.security.jwt.stores import JWKStoreAbstract, JWKStoreMemory
from fastapi_factory_utilities.core.security.jwt.types import OAuth2Issuer

# Minimal valid RSA JWK (RFC 7517-style) for real PyJWK instances
_RSA_N = (
    "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1"
    + "RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5GsGY6QeFMStq1DqVQ6p6nQ"
)
_RSA_E = "AQAB"

CONCURRENT_OPERATION_COUNT = 10
EXPECTED_TWO_KEYS = 2


class TestJWKStoreAbstract:
    """Various tests for the JWKStoreAbstract class."""

    def test_abstract_class_cannot_be_instantiated(self) -> None:
        """Test that the abstract class cannot be instantiated directly."""
        with pytest.raises(TypeError):
            # pylint: disable=abstract-class-instantiated,no-value-for-parameter
            JWKStoreAbstract()  # type: ignore[abstract]

    @pytest.mark.asyncio
    async def test_concrete_get_jwk_returns_added_jwk(self) -> None:
        """Test that a concrete store returns the correct JWK after add_jwk."""
        jwk1 = PyJWK.from_dict({"kid": "kid1", "kty": "RSA", "use": "sig", "n": _RSA_N, "e": _RSA_E})

        class ConcreteStore(JWKStoreAbstract):
            """Concrete implementation for testing."""

            async def get_jwk(self, kid: str) -> PyJWK:
                return self._jwk_by_kid[kid]

            async def get_issuer_by_kid(self, kid: str) -> OAuth2Issuer:
                return self._issuer_by_kid[kid]

            async def get_jwks(self, issuer: OAuth2Issuer) -> PyJWKSet:
                jwks = [jwk for kid, jwk in self._jwk_by_kid.items() if self._issuer_by_kid[kid] == issuer]
                return PyJWKSet.from_dict(
                    {"keys": [jwk._jwk_data for jwk in jwks]}  # pylint: disable=protected-access # pyright: ignore[reportPrivateUsage]
                )

            async def add_jwk(self, issuer: str, jwk: PyJWK) -> None:
                if jwk.key_id is None:
                    raise ValueError("JWK key ID is required")
                self._jwk_by_kid[jwk.key_id] = jwk
                self._issuer_by_kid[jwk.key_id] = issuer

        store = ConcreteStore()
        await store.add_jwk("https://issuer.example", jwk1)
        result = await store.get_jwk("kid1")
        assert result is jwk1
        assert result.key_id == "kid1"

    @pytest.mark.asyncio
    async def test_get_jwk_raises_key_error_for_missing_kid(self) -> None:
        """Test that get_jwk raises KeyError when kid is not found."""
        jwk1 = PyJWK.from_dict({"kid": "existing_kid", "kty": "RSA", "use": "sig", "n": _RSA_N, "e": _RSA_E})

        class ConcreteStoreKeyError(JWKStoreAbstract):
            """Concrete implementation for testing KeyError."""

            async def get_jwk(self, kid: str) -> PyJWK:
                return self._jwk_by_kid[kid]

            async def get_issuer_by_kid(self, kid: str) -> str:
                return self._issuer_by_kid[kid]

            async def get_jwks(self, issuer: str) -> PyJWKSet:
                jwks = [jwk for kid, jwk in self._jwk_by_kid.items() if self._issuer_by_kid[kid] == issuer]
                return PyJWKSet.from_dict(
                    {"keys": [jwk._jwk_data for jwk in jwks]}  # pylint: disable=protected-access # pyright: ignore[reportPrivateUsage]
                )

            async def add_jwk(self, issuer: str, jwk: PyJWK) -> None:
                if jwk.key_id is None:
                    raise ValueError("JWK key ID is required")
                self._jwk_by_kid[jwk.key_id] = jwk
                self._issuer_by_kid[jwk.key_id] = issuer

        store = ConcreteStoreKeyError()
        await store.add_jwk("https://issuer.example", jwk1)

        with pytest.raises(KeyError):
            await store.get_jwk("nonexistent_kid")


class TestJWKStoreMemory:
    """Various tests for the JWKStoreMemory class."""

    @pytest.fixture
    def store(self) -> JWKStoreMemory:
        """Create a JWK store in memory.

        Returns:
            JWKStoreMemory: A JWK store instance.
        """
        return JWKStoreMemory()

    @pytest.fixture
    def sample_jwk(self) -> PyJWK:
        """Create a sample PyJWK with kid test_kid_1.

        Returns:
            PyJWK: A sample JWK.
        """
        return PyJWK.from_dict(
            {
                "kid": "test_kid_1",
                "kty": "RSA",
                "use": "sig",
                "n": _RSA_N,
                "e": _RSA_E,
            }
        )

    @pytest.fixture
    def sample_jwk_2(self) -> PyJWK:
        """Create a second sample PyJWK with kid test_kid_2.

        Returns:
            PyJWK: A sample JWK.
        """
        return PyJWK.from_dict(
            {
                "kid": "test_kid_2",
                "kty": "RSA",
                "use": "sig",
                "n": _RSA_N,
                "e": _RSA_E,
            }
        )

    @pytest.fixture
    def sample_jwk_no_kid(self) -> PyJWK:
        """Create a PyJWK without kid for add_jwk validation tests.

        Returns:
            PyJWK: A JWK with key_id None.
        """
        return PyJWK.from_dict({"kty": "RSA", "use": "sig", "n": _RSA_N, "e": _RSA_E})

    def test_can_be_instantiated(self) -> None:
        """Test that JWKStoreMemory can be instantiated."""
        store = JWKStoreMemory()
        assert isinstance(store, JWKStoreMemory)
        assert isinstance(store, JWKStoreAbstract)

    def test_inherits_from_abstract_class(self, store: JWKStoreMemory) -> None:
        """Test that JWKStoreMemory inherits from JWKStoreAbstract.

        Args:
            store (JWKStoreMemory): The store instance.
        """
        assert isinstance(store, JWKStoreAbstract)

    def test_initializes_with_lock(self, store: JWKStoreMemory) -> None:
        """Test that store initializes with a lock.

        Args:
            store (JWKStoreMemory): The store instance.
        """
        assert isinstance(store._lock, asyncio.Lock)  # pyright: ignore[reportPrivateUsage] # pylint: disable=protected-access

    @pytest.mark.asyncio
    async def test_add_jwk_then_get_jwk_returns_same_jwk(self, store: JWKStoreMemory, sample_jwk: PyJWK) -> None:
        """Test that after add_jwk, get_jwk returns the same PyJWK.

        Args:
            store (JWKStoreMemory): The store instance.
            sample_jwk (PyJWK): Sample JWK to add.
        """
        await store.add_jwk("https://issuer.example", sample_jwk)
        result = await store.get_jwk("test_kid_1")
        assert result is sample_jwk
        assert result.key_id == "test_kid_1"

    @pytest.mark.asyncio
    async def test_get_jwk_raises_key_error_for_missing_kid(self, store: JWKStoreMemory, sample_jwk: PyJWK) -> None:
        """Test that get_jwk raises KeyError when kid is not found.

        Args:
            store (JWKStoreMemory): The store instance.
            sample_jwk (PyJWK): Sample JWK to add.
        """
        await store.add_jwk("https://issuer.example", sample_jwk)

        with pytest.raises(KeyError):
            await store.get_jwk("nonexistent_kid")

    @pytest.mark.asyncio
    async def test_get_issuer_by_kid_returns_issuer_after_add_jwk(
        self, store: JWKStoreMemory, sample_jwk: PyJWK
    ) -> None:
        """Test that get_issuer_by_kid returns the issuer for a stored kid.

        Args:
            store (JWKStoreMemory): The store instance.
            sample_jwk (PyJWK): Sample JWK to add.
        """
        issuer = "https://issuer.example"
        await store.add_jwk(issuer, sample_jwk)
        result = await store.get_issuer_by_kid("test_kid_1")
        assert result == issuer

    @pytest.mark.asyncio
    async def test_get_issuer_by_kid_raises_key_error_for_missing_kid(
        self, store: JWKStoreMemory, sample_jwk: PyJWK
    ) -> None:
        """Test that get_issuer_by_kid raises KeyError when kid is not found.

        Args:
            store (JWKStoreMemory): The store instance.
            sample_jwk (PyJWK): Sample JWK to add.
        """
        await store.add_jwk("https://issuer.example", sample_jwk)

        with pytest.raises(KeyError):
            await store.get_issuer_by_kid("nonexistent_kid")

    @pytest.mark.asyncio
    async def test_get_issuer_by_kid_returns_correct_issuer_per_kid(
        self,
        store: JWKStoreMemory,
        sample_jwk: PyJWK,
        sample_jwk_2: PyJWK,
    ) -> None:
        """Test that get_issuer_by_kid returns the right issuer for each kid.

        Args:
            store (JWKStoreMemory): The store instance.
            sample_jwk (PyJWK): First JWK.
            sample_jwk_2 (PyJWK): Second JWK.
        """
        issuer_a = "https://issuer-a.example"
        issuer_b = "https://issuer-b.example"
        await store.add_jwk(issuer_a, sample_jwk)
        await store.add_jwk(issuer_a, sample_jwk_2)
        jwk_b = PyJWK.from_dict({"kid": "kid_b", "kty": "RSA", "use": "sig", "n": _RSA_N, "e": _RSA_E})
        await store.add_jwk(issuer_b, jwk_b)

        assert await store.get_issuer_by_kid("test_kid_1") == issuer_a
        assert await store.get_issuer_by_kid("test_kid_2") == issuer_a
        assert await store.get_issuer_by_kid("kid_b") == issuer_b

    @pytest.mark.asyncio
    async def test_add_jwk_without_kid_raises_value_error(
        self, store: JWKStoreMemory, sample_jwk_no_kid: PyJWK
    ) -> None:
        """Test that add_jwk raises ValueError when JWK has no key_id.

        Args:
            store (JWKStoreMemory): The store instance.
            sample_jwk_no_kid (PyJWK): JWK with key_id None.
        """
        with pytest.raises(ValueError, match="JWK key ID is required"):
            await store.add_jwk("https://issuer.example", sample_jwk_no_kid)

    @pytest.mark.asyncio
    async def test_get_jwks_returns_only_keys_for_issuer(
        self,
        store: JWKStoreMemory,
        sample_jwk: PyJWK,
        sample_jwk_2: PyJWK,
    ) -> None:
        """Test that get_jwks(issuer) returns only keys stored for that issuer.

        Args:
            store (JWKStoreMemory): The store instance.
            sample_jwk (PyJWK): First JWK.
            sample_jwk_2 (PyJWK): Second JWK.
        """
        issuer_a = "https://issuer-a.example"
        issuer_b = "https://issuer-b.example"
        await store.add_jwk(issuer_a, sample_jwk)
        await store.add_jwk(issuer_a, sample_jwk_2)
        jwk_b = PyJWK.from_dict({"kid": "kid_b", "kty": "RSA", "use": "sig", "n": _RSA_N, "e": _RSA_E})
        await store.add_jwk(issuer_b, jwk_b)

        jwks_a = await store.get_jwks(issuer_a)
        jwks_b = await store.get_jwks(issuer_b)

        keys_a: list[PyJWK] = cast(list[PyJWK], jwks_a.keys)  # type: ignore[union-attr]
        keys_b: list[PyJWK] = cast(list[PyJWK], jwks_b.keys)  # type: ignore[union-attr]
        assert len(keys_a) == EXPECTED_TWO_KEYS
        assert len(keys_b) == 1
        kids_a = {k.key_id for k in keys_a}
        kids_b = {k.key_id for k in keys_b}
        assert kids_a == {"test_kid_1", "test_kid_2"}
        assert kids_b == {"kid_b"}

    @pytest.mark.asyncio
    async def test_get_jwks_returns_new_pyjwkset_each_time(self, store: JWKStoreMemory, sample_jwk: PyJWK) -> None:
        """Test that get_jwks returns a new PyJWKSet each time (not same reference).

        Args:
            store (JWKStoreMemory): The store instance.
            sample_jwk (PyJWK): Sample JWK to add.
        """
        await store.add_jwk("https://issuer.example", sample_jwk)
        jwks1 = await store.get_jwks("https://issuer.example")
        jwks2 = await store.get_jwks("https://issuer.example")
        assert jwks1 is not jwks2
        keys1: list[PyJWK] = cast(list[PyJWK], jwks1.keys)  # type: ignore[union-attr]
        keys2: list[PyJWK] = cast(list[PyJWK], jwks2.keys)  # type: ignore[union-attr]
        assert len(keys1) == 1
        assert len(keys2) == 1
        assert jwks1["test_kid_1"].key_id == jwks2["test_kid_1"].key_id

    @pytest.mark.asyncio
    async def test_add_jwk_overwrites_by_kid(self, store: JWKStoreMemory, sample_jwk: PyJWK) -> None:
        """Test that adding a second JWK with the same kid overwrites the first.

        Args:
            store (JWKStoreMemory): The store instance.
            sample_jwk (PyJWK): First JWK (kid test_kid_1).
        """
        issuer = "https://issuer.example"
        await store.add_jwk(issuer, sample_jwk)
        jwk_same_kid = PyJWK.from_dict(
            {
                "kid": "test_kid_1",
                "kty": "RSA",
                "use": "sig",
                "n": _RSA_N,
                "e": _RSA_E,
            }
        )
        await store.add_jwk(issuer, jwk_same_kid)
        result = await store.get_jwk("test_kid_1")
        assert result is jwk_same_kid
        assert result is not sample_jwk

    @pytest.mark.asyncio
    async def test_concurrent_add_and_get_jwk(self, store: JWKStoreMemory) -> None:
        """Test that concurrent add_jwk and get_jwk operations are safe.

        Args:
            store (JWKStoreMemory): The store instance.
        """
        issuer = "https://issuer.example"

        async def add_and_get(i: int) -> PyJWK:
            jwk = PyJWK.from_dict(
                {
                    "kid": f"test_kid_{i}",
                    "kty": "RSA",
                    "use": "sig",
                    "n": _RSA_N,
                    "e": _RSA_E,
                }
            )
            await store.add_jwk(issuer, jwk)
            return await store.get_jwk(f"test_kid_{i}")

        results = await asyncio.gather(*[add_and_get(i) for i in range(CONCURRENT_OPERATION_COUNT)])
        assert len(results) == CONCURRENT_OPERATION_COUNT
        for i, jwk in enumerate(results):
            assert jwk.key_id == f"test_kid_{i}"

        jwks = await store.get_jwks(issuer)
        keys: list[PyJWK] = cast(list[PyJWK], jwks.keys)  # type: ignore[union-attr]
        assert len(keys) == CONCURRENT_OPERATION_COUNT

    @pytest.mark.asyncio
    async def test_concurrent_get_jwks(self, store: JWKStoreMemory, sample_jwk: PyJWK, sample_jwk_2: PyJWK) -> None:
        """Test that concurrent get_jwks operations are safe.

        Args:
            store (JWKStoreMemory): The store instance.
            sample_jwk (PyJWK): First JWK.
            sample_jwk_2 (PyJWK): Second JWK.
        """
        issuer = "https://issuer.example"
        await store.add_jwk(issuer, sample_jwk)
        await store.add_jwk(issuer, sample_jwk_2)

        async def get_jwks() -> PyJWKSet:
            return await store.get_jwks(issuer)

        results = await asyncio.gather(*[get_jwks() for _ in range(CONCURRENT_OPERATION_COUNT)])
        assert len(results) == CONCURRENT_OPERATION_COUNT
        for jwks in results:
            keys: list[PyJWK] = cast(list[PyJWK], jwks.keys)  # type: ignore[union-attr]
            assert len(keys) == EXPECTED_TWO_KEYS
            assert jwks["test_kid_1"].key_id == "test_kid_1"
            assert jwks["test_kid_2"].key_id == "test_kid_2"
