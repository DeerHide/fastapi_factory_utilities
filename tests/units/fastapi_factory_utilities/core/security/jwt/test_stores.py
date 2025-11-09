"""Unit tests for the JWK stores."""

import asyncio
from unittest.mock import MagicMock

import pytest
from jwt.api_jwk import PyJWKSet

from fastapi_factory_utilities.core.security.jwt.stores import JWKStoreAbstract, JWKStoreMemory

# Test constants
SAMPLE_JWKS_KEY_COUNT = 2
CONCURRENT_OPERATION_COUNT = 10
LARGE_JWKS_KEY_COUNT = 10


class TestJWKStoreAbstract:
    """Various tests for the JWKStoreAbstract class."""

    def test_abstract_class_cannot_be_instantiated(self) -> None:
        """Test that the abstract class cannot be instantiated directly."""
        with pytest.raises(TypeError):
            # pylint: disable=abstract-class-instantiated,no-value-for-parameter
            JWKStoreAbstract()  # type: ignore[abstract]

    @pytest.mark.asyncio
    async def test_get_jwk_calls_get_jwks(self) -> None:
        """Test that get_jwk calls get_jwks and retrieves the correct JWK.

        This test verifies that the abstract method get_jwk correctly
        delegates to get_jwks and indexes the result.
        """

        # Create a concrete implementation for testing
        class ConcreteStore(JWKStoreAbstract):
            """Concrete implementation for testing."""

            async def get_jwks(self) -> PyJWKSet:
                """Get the JWKS from the store."""
                jwks_dict = {
                    "keys": [
                        {
                            "kid": "kid1",
                            "kty": "RSA",
                            "use": "sig",
                            "n": "test_n_value_1",
                            "e": "AQAB",
                        },
                        {
                            "kid": "kid2",
                            "kty": "RSA",
                            "use": "sig",
                            "n": "test_n_value_2",
                            "e": "AQAB",
                        },
                    ]
                }
                jwks = PyJWKSet.from_dict(jwks_dict)
                return jwks

            async def store_jwks(self, jwks: PyJWKSet) -> None:
                """Store the JWKS in the store."""
                pass

        store = ConcreteStore()
        jwk = await store.get_jwk("kid1")

        assert jwk is not None
        assert jwk.key_id == "kid1"

    @pytest.mark.asyncio
    async def test_get_jwk_raises_key_error_for_missing_kid(self) -> None:
        """Test that get_jwk raises KeyError when kid is not found."""

        # Create a concrete implementation for testing
        class ConcreteStore(JWKStoreAbstract):
            """Concrete implementation for testing."""

            async def get_jwks(self) -> PyJWKSet:
                """Get the JWKS from the store."""
                # Create a JWKS with one key, but we'll look for a different kid
                jwks_dict = {
                    "keys": [
                        {
                            "kid": "existing_kid",
                            "kty": "RSA",
                            "use": "sig",
                            "n": "test_n_value",
                            "e": "AQAB",
                        }
                    ]
                }
                return PyJWKSet.from_dict(jwks_dict)

            async def store_jwks(self, jwks: PyJWKSet) -> None:
                """Store the JWKS in the store."""
                pass

        store = ConcreteStore()

        with pytest.raises(KeyError):
            await store.get_jwk("nonexistent_kid")


class TestJWKStoreMemory:
    """Various tests for the JWKStoreMemory class."""

    @pytest.fixture
    def store(self, monkeypatch: pytest.MonkeyPatch) -> JWKStoreMemory:
        """Create a JWK store in memory.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.

        Returns:
            JWKStoreMemory: A JWK store instance.
        """
        # Mock PyJWKSet to allow empty initialization for testing
        mock_empty_jwks = MagicMock()
        type(mock_empty_jwks).__len__ = lambda self: 0
        type(mock_empty_jwks).__getitem__ = lambda self, key: (_ for _ in ()).throw(KeyError("Key not found"))

        def mock_pyjwkset_init(keys: list) -> MagicMock:  # pylint: disable=unused-argument
            """Mock PyJWKSet initialization."""
            return mock_empty_jwks

        monkeypatch.setattr(
            "fastapi_factory_utilities.core.security.jwt.stores.PyJWKSet",
            mock_pyjwkset_init,
        )
        store = JWKStoreMemory()
        return store

    @pytest.fixture
    def empty_jwks(self) -> MagicMock:
        """Create an empty JWKS mock.

        Returns:
            MagicMock: An empty JWKS mock.
        """
        mock_jwks = MagicMock()
        type(mock_jwks).__len__ = lambda self: 0
        return mock_jwks

    @pytest.fixture
    def sample_jwks(self) -> PyJWKSet:
        """Create a sample JWKS with test keys.

        Returns:
            PyJWKSet: A sample JWKS.
        """
        jwks_dict = {
            "keys": [
                {
                    "kid": "test_kid_1",
                    "kty": "RSA",
                    "use": "sig",
                    "n": "test_n_value_1",
                    "e": "AQAB",
                },
                {
                    "kid": "test_kid_2",
                    "kty": "RSA",
                    "use": "sig",
                    "n": "test_n_value_2",
                    "e": "AQAB",
                },
            ]
        }
        return PyJWKSet.from_dict(jwks_dict)

    def test_can_be_instantiated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that JWKStoreMemory can be instantiated.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.
        """
        # Mock PyJWKSet to allow empty initialization for testing
        mock_empty_jwks = MagicMock()
        type(mock_empty_jwks).__len__ = lambda self: 0

        def mock_pyjwkset_init(keys: list) -> MagicMock:  # pylint: disable=unused-argument
            """Mock PyJWKSet initialization."""
            return mock_empty_jwks

        monkeypatch.setattr(
            "fastapi_factory_utilities.core.security.jwt.stores.PyJWKSet",
            mock_pyjwkset_init,
        )
        store = JWKStoreMemory()
        assert isinstance(store, JWKStoreMemory)
        assert isinstance(store, JWKStoreAbstract)

    def test_inherits_from_abstract_class(self, store: JWKStoreMemory) -> None:
        """Test that JWKStoreMemory inherits from JWKStoreAbstract.

        Args:
            store (JWKStoreMemory): The store instance.
        """
        assert isinstance(store, JWKStoreAbstract)

    def test_initializes_with_empty_jwks(self, store: JWKStoreMemory) -> None:
        """Test that store initializes with empty JWKS.

        Args:
            store (JWKStoreMemory): The store instance.
        """
        assert store._jwks is not None  # pyright: ignore[reportPrivateUsage] # pylint: disable=protected-access
        # For mocks, we check the mock's __len__ return value
        if isinstance(store._jwks, MagicMock):  # pyright: ignore[reportPrivateUsage] # pylint: disable=protected-access
            assert len(store._jwks) == 0  # pyright: ignore[reportPrivateUsage] # pylint: disable=protected-access
        else:
            assert len(store._jwks.keys) == 0  # pyright: ignore[reportPrivateUsage] # pylint: disable=protected-access

    def test_initializes_with_lock(self, store: JWKStoreMemory) -> None:
        """Test that store initializes with a lock.

        Args:
            store (JWKStoreMemory): The store instance.
        """
        assert isinstance(store._lock, asyncio.Lock)  # pyright: ignore[reportPrivateUsage] # pylint: disable=protected-access

    @pytest.mark.asyncio
    async def test_get_jwks_returns_empty_jwks_initially(self, store: JWKStoreMemory) -> None:
        """Test that get_jwks returns empty JWKS initially.

        Args:
            store (JWKStoreMemory): The store instance.
        """
        jwks = await store.get_jwks()
        assert jwks is not None
        # For mocks, we check the mock's __len__ return value
        if isinstance(jwks, MagicMock):
            assert len(jwks) == 0
        else:
            assert len(jwks.keys) == 0

    @pytest.mark.asyncio
    async def test_store_jwks_stores_jwks(self, store: JWKStoreMemory, sample_jwks: PyJWKSet) -> None:
        """Test that store_jwks stores the JWKS.

        Args:
            store (JWKStoreMemory): The store instance.
            sample_jwks (PyJWKSet): Sample JWKS to store.
        """
        await store.store_jwks(sample_jwks)
        stored_jwks = await store.get_jwks()
        assert stored_jwks == sample_jwks
        assert len(stored_jwks.keys) == SAMPLE_JWKS_KEY_COUNT

    @pytest.mark.asyncio
    async def test_store_jwks_overwrites_existing_jwks(
        self, store: JWKStoreMemory, sample_jwks: PyJWKSet, empty_jwks: MagicMock
    ) -> None:
        """Test that store_jwks overwrites existing JWKS.

        Args:
            store (JWKStoreMemory): The store instance.
            sample_jwks (PyJWKSet): Sample JWKS to store first.
            empty_jwks (MagicMock): Empty JWKS mock to overwrite with.
        """
        await store.store_jwks(sample_jwks)
        assert len((await store.get_jwks()).keys) == SAMPLE_JWKS_KEY_COUNT

        await store.store_jwks(empty_jwks)  # type: ignore[arg-type]
        stored_jwks = await store.get_jwks()
        assert stored_jwks == empty_jwks
        assert len(stored_jwks.keys) == 0

    @pytest.mark.asyncio
    async def test_get_jwk_retrieves_correct_jwk(self, store: JWKStoreMemory, sample_jwks: PyJWKSet) -> None:
        """Test that get_jwk retrieves the correct JWK by kid.

        Args:
            store (JWKStoreMemory): The store instance.
            sample_jwks (PyJWKSet): Sample JWKS to store.
        """
        await store.store_jwks(sample_jwks)
        jwk = await store.get_jwk("test_kid_1")

        assert jwk is not None
        assert jwk.key_id == "test_kid_1"

    @pytest.mark.asyncio
    async def test_get_jwk_retrieves_different_jwk(self, store: JWKStoreMemory, sample_jwks: PyJWKSet) -> None:
        """Test that get_jwk retrieves a different JWK by kid.

        Args:
            store (JWKStoreMemory): The store instance.
            sample_jwks (PyJWKSet): Sample JWKS to store.
        """
        await store.store_jwks(sample_jwks)
        jwk = await store.get_jwk("test_kid_2")

        assert jwk is not None
        assert jwk.key_id == "test_kid_2"

    @pytest.mark.asyncio
    async def test_get_jwk_raises_key_error_for_missing_kid(self, store: JWKStoreMemory, sample_jwks: PyJWKSet) -> None:
        """Test that get_jwk raises KeyError when kid is not found.

        Args:
            store (JWKStoreMemory): The store instance.
            sample_jwks (PyJWKSet): Sample JWKS to store.
        """
        await store.store_jwks(sample_jwks)

        with pytest.raises(KeyError):
            await store.get_jwk("nonexistent_kid")

    @pytest.mark.asyncio
    async def test_get_jwk_raises_key_error_when_store_is_empty(self, store: JWKStoreMemory) -> None:
        """Test that get_jwk raises KeyError when store is empty.

        Args:
            store (JWKStoreMemory): The store instance.
        """
        with pytest.raises(KeyError):
            await store.get_jwk("any_kid")

    @pytest.mark.asyncio
    async def test_concurrent_get_jwks_operations(self, store: JWKStoreMemory, sample_jwks: PyJWKSet) -> None:
        """Test that concurrent get_jwks operations are thread-safe.

        Args:
            store (JWKStoreMemory): The store instance.
            sample_jwks (PyJWKSet): Sample JWKS to store.
        """
        await store.store_jwks(sample_jwks)

        async def get_jwks() -> PyJWKSet:
            """Get JWKS from store."""
            return await store.get_jwks()

        # Run multiple concurrent get operations
        results = await asyncio.gather(*[get_jwks() for _ in range(CONCURRENT_OPERATION_COUNT)])

        # All results should be the same
        assert all(result == sample_jwks for result in results)
        assert len(results) == CONCURRENT_OPERATION_COUNT

    @pytest.mark.asyncio
    async def test_concurrent_store_jwks_operations(self, store: JWKStoreMemory) -> None:
        """Test that concurrent store_jwks operations are thread-safe.

        Args:
            store (JWKStoreMemory): The store instance.
        """
        # Create different JWKS for each operation
        jwks_list = []
        for i in range(5):
            jwks_dict = {
                "keys": [
                    {
                        "kid": f"test_kid_{i}",
                        "kty": "RSA",
                        "use": "sig",
                        "n": f"test_n_value_{i}",
                        "e": "AQAB",
                    }
                ]
            }
            jwks_list.append(PyJWKSet.from_dict(jwks_dict))

        async def store_jwks(jwks: PyJWKSet) -> None:
            """Store JWKS in store."""
            await store.store_jwks(jwks)

        # Run multiple concurrent store operations
        await asyncio.gather(*[store_jwks(jwks) for jwks in jwks_list])

        # The final state should be one of the stored JWKS
        final_jwks = await store.get_jwks()
        assert len(final_jwks.keys) == 1
        # Verify the final JWKS is one of the stored ones
        assert any(final_jwks == jwks for jwks in jwks_list)

    @pytest.mark.asyncio
    async def test_concurrent_get_and_store_operations(
        self, store: JWKStoreMemory, sample_jwks: PyJWKSet, empty_jwks: MagicMock
    ) -> None:
        """Test that concurrent get and store operations are thread-safe.

        Args:
            store (JWKStoreMemory): The store instance.
            sample_jwks (PyJWKSet): Sample JWKS to store.
            empty_jwks (MagicMock): Empty JWKS mock to store.
        """
        await store.store_jwks(sample_jwks)

        async def get_jwks() -> PyJWKSet | MagicMock:
            """Get JWKS from store."""
            return await store.get_jwks()

        async def store_jwks(jwks: PyJWKSet | MagicMock) -> None:
            """Store JWKS in store."""
            await store.store_jwks(jwks)  # type: ignore[arg-type]

        # Run concurrent get and store operations
        await asyncio.gather(
            *[get_jwks() for _ in range(5)],
            *[store_jwks(empty_jwks) for _ in range(5)],
        )

        # Final state should be consistent
        final_jwks = await store.get_jwks()
        # Should be empty after all store operations complete
        if isinstance(final_jwks, MagicMock):
            assert len(final_jwks) == 0
        else:
            assert isinstance(final_jwks, PyJWKSet)
            assert len(final_jwks.keys) == 0

    @pytest.mark.asyncio
    async def test_get_jwks_returns_same_reference(self, store: JWKStoreMemory, sample_jwks: PyJWKSet) -> None:
        """Test that get_jwks returns the same reference (not a copy).

        Args:
            store (JWKStoreMemory): The store instance.
            sample_jwks (PyJWKSet): Sample JWKS to store.
        """
        await store.store_jwks(sample_jwks)
        jwks1 = await store.get_jwks()
        jwks2 = await store.get_jwks()

        # Should be the same object reference
        assert jwks1 is jwks2
        assert jwks1 == jwks2

    @pytest.mark.asyncio
    async def test_store_jwks_with_empty_set(self, store: JWKStoreMemory, empty_jwks: MagicMock) -> None:
        """Test storing an empty JWKS.

        Args:
            store (JWKStoreMemory): The store instance.
            empty_jwks (MagicMock): Empty JWKS mock to store.
        """
        await store.store_jwks(empty_jwks)  # type: ignore[arg-type]
        stored_jwks = await store.get_jwks()
        assert stored_jwks == empty_jwks
        # For mocks, we check the mock's __len__ return value
        if isinstance(stored_jwks, MagicMock):
            assert len(stored_jwks) == 0
        else:
            assert len(stored_jwks.keys) == 0

    @pytest.mark.asyncio
    async def test_store_jwks_with_large_jwks(self, store: JWKStoreMemory) -> None:
        """Test storing a JWKS with many keys.

        Args:
            store (JWKStoreMemory): The store instance.
        """
        # Create a JWKS with many keys
        keys = []
        for i in range(LARGE_JWKS_KEY_COUNT):
            keys.append(
                {
                    "kid": f"test_kid_{i}",
                    "kty": "RSA",
                    "use": "sig",
                    "n": f"test_n_value_{i}",
                    "e": "AQAB",
                }
            )

        jwks_dict = {"keys": keys}
        large_jwks = PyJWKSet.from_dict(jwks_dict)

        await store.store_jwks(large_jwks)
        stored_jwks = await store.get_jwks()

        assert len(stored_jwks.keys) == LARGE_JWKS_KEY_COUNT
        # Verify we can retrieve all keys
        for i in range(LARGE_JWKS_KEY_COUNT):
            jwk = await store.get_jwk(f"test_kid_{i}")
            assert jwk.key_id == f"test_kid_{i}"
