"""Unit tests for the JWT verifiers."""

import datetime

import pytest

from fastapi_factory_utilities.core.security.jwt.objects import JWTPayload
from fastapi_factory_utilities.core.security.jwt.types import JWTToken
from fastapi_factory_utilities.core.security.jwt.verifiers import (
    JWTNoneVerifier,
    JWTVerifierAbstract,
)


class TestJWTVerifierAbstract:
    """Various tests for the JWTVerifierAbstract class."""

    def test_abstract_class_cannot_be_instantiated(self) -> None:
        """Test that the abstract class cannot be instantiated directly."""
        with pytest.raises(TypeError):
            JWTVerifierAbstract()  # type: ignore[abstract] # pylint: disable=abstract-class-instantiated

    def test_subclass_must_implement_verify(self) -> None:
        """Test that subclasses must implement the verify method."""

        # Create a subclass without implementing verify
        class IncompleteVerifier(JWTVerifierAbstract[JWTPayload]):
            """Incomplete verifier that doesn't implement verify."""

            pass

        # Attempting to instantiate should raise TypeError
        with pytest.raises(TypeError):
            IncompleteVerifier()  # type: ignore[abstract] # pylint: disable=abstract-class-instantiated

    def test_subclass_with_verify_can_be_instantiated(self) -> None:
        """Test that subclasses implementing verify can be instantiated."""

        # Create a subclass with verify implemented
        class CompleteVerifier(JWTVerifierAbstract[JWTPayload]):
            """Complete verifier that implements verify."""

            async def verify(
                self,
                jwt_token: JWTToken,
                jwt_payload: JWTPayload,
            ) -> None:
                """Verify the JWT bearer token."""
                return

        # Should be able to instantiate
        verifier = CompleteVerifier()
        assert isinstance(verifier, JWTVerifierAbstract)
        assert isinstance(verifier, CompleteVerifier)

    def test_abstract_verify_signature(self) -> None:
        """Test that the abstract verify method has the correct signature."""
        # Check that verify is an abstract method
        assert hasattr(JWTVerifierAbstract, "verify")
        # The method should be abstract - check __isabstractmethod__ attribute
        assert getattr(JWTVerifierAbstract.verify, "__isabstractmethod__", False) is True  # type: ignore[arg-type]


class TestJWTNoneVerifier:
    """Various tests for the JWTNoneVerifier class."""

    @pytest.fixture
    def verifier(self) -> JWTNoneVerifier:
        """Create a JWTNoneVerifier instance.

        Returns:
            JWTNoneVerifier: A JWTNoneVerifier instance.
        """
        return JWTNoneVerifier()

    @pytest.fixture
    def jwt_token(self) -> JWTToken:
        """Create a JWT token.

        Returns:
            JWTToken: A JWT token.
        """
        return JWTToken("test.jwt.token")

    @pytest.fixture
    def jwt_payload(self) -> JWTPayload:
        """Create a JWT bearer payload.

        Returns:
            JWTBearerPayload: A JWT bearer payload.
        """
        now = datetime.datetime.now(tz=datetime.UTC)
        exp = now + datetime.timedelta(hours=1)
        nbf = now - datetime.timedelta(minutes=5)

        return JWTPayload(
            scp="read write",
            aud="api1 api2",
            iss="https://example.com",
            exp=int(exp.timestamp()),
            iat=int(now.timestamp()),
            nbf=int(nbf.timestamp()),
            sub="user123",
        )

    def test_can_be_instantiated(self) -> None:
        """Test that JWTNoneVerifier can be instantiated."""
        verifier = JWTNoneVerifier()
        assert isinstance(verifier, JWTNoneVerifier)
        assert isinstance(verifier, JWTVerifierAbstract)

    def test_inherits_from_abstract_class(self, verifier: JWTNoneVerifier) -> None:
        """Test that JWTNoneVerifier inherits from JWTVerifierAbstract.

        Args:
            verifier (JWTNoneVerifier): The verifier instance.
        """
        assert isinstance(verifier, JWTVerifierAbstract)

    @pytest.mark.asyncio
    async def test_verify_returns_none(
        self,
        verifier: JWTNoneVerifier,
        jwt_token: JWTToken,
        jwt_payload: JWTPayload,
    ) -> None:
        """Test that verify method returns None.

        Args:
            verifier (JWTNoneVerifier): The verifier instance.
            jwt_token (JWTToken): The JWT token.
            jwt_payload (JWTBearerPayload): The JWT bearer payload.
        """
        result = await verifier.verify(jwt_token=jwt_token, jwt_payload=jwt_payload)
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_does_not_raise_exception(
        self,
        verifier: JWTNoneVerifier,
        jwt_token: JWTToken,
        jwt_payload: JWTPayload,
    ) -> None:
        """Test that verify method does not raise any exceptions.

        Args:
            verifier (JWTNoneVerifier): The verifier instance.
            jwt_token (JWTToken): The JWT token.
            jwt_payload (JWTBearerPayload): The JWT bearer payload.
        """
        # Should not raise any exception
        await verifier.verify(jwt_token=jwt_token, jwt_payload=jwt_payload)

    @pytest.mark.asyncio
    async def test_verify_with_different_tokens(
        self,
        verifier: JWTNoneVerifier,
        jwt_payload: JWTPayload,
    ) -> None:
        """Test that verify works with different JWT tokens.

        Args:
            verifier (JWTNoneVerifier): The verifier instance.
            jwt_payload (JWTBearerPayload): The JWT bearer payload.
        """
        token1 = JWTToken("token1")
        token2 = JWTToken("token2")
        token3 = JWTToken("another.token.here")

        # All should work without raising exceptions
        await verifier.verify(jwt_token=token1, jwt_payload=jwt_payload)
        await verifier.verify(jwt_token=token2, jwt_payload=jwt_payload)
        await verifier.verify(jwt_token=token3, jwt_payload=jwt_payload)

    @pytest.mark.asyncio
    async def test_verify_with_different_payloads(
        self,
        verifier: JWTNoneVerifier,
        jwt_token: JWTToken,
    ) -> None:
        """Test that verify works with different JWT payloads.

        Args:
            verifier (JWTNoneVerifier): The verifier instance.
            jwt_token (JWTToken): The JWT token.
        """
        now = datetime.datetime.now(tz=datetime.UTC)

        payload1 = JWTPayload(
            scp="read",
            aud="api1",
            iss="https://example.com",
            exp=int((now + datetime.timedelta(hours=1)).timestamp()),
            iat=int(now.timestamp()),
            nbf=int(now.timestamp()),
            sub="user1",
        )

        payload2 = JWTPayload(
            scp="read write admin",
            aud="api1 api2 api3",
            iss="https://another-issuer.com",
            exp=int((now + datetime.timedelta(hours=2)).timestamp()),
            iat=int(now.timestamp()),
            nbf=int(now.timestamp()),
            sub="user2",
        )

        # All should work without raising exceptions
        await verifier.verify(jwt_token=jwt_token, jwt_payload=payload1)
        await verifier.verify(jwt_token=jwt_token, jwt_payload=payload2)

    @pytest.mark.asyncio
    async def test_verify_accepts_correct_parameters(
        self,
        verifier: JWTNoneVerifier,
        jwt_token: JWTToken,
        jwt_payload: JWTPayload,
    ) -> None:
        """Test that verify accepts the correct parameter types.

        Args:
            verifier (JWTNoneVerifier): The verifier instance.
            jwt_token (JWTToken): The JWT token.
            jwt_payload (JWTBearerPayload): The JWT bearer payload.
        """
        # Should accept JWTToken and JWTBearerPayload
        await verifier.verify(jwt_token=jwt_token, jwt_payload=jwt_payload)

    @pytest.mark.asyncio
    async def test_verify_can_be_called_multiple_times(
        self,
        verifier: JWTNoneVerifier,
        jwt_token: JWTToken,
        jwt_payload: JWTPayload,
    ) -> None:
        """Test that verify can be called multiple times without side effects.

        Args:
            verifier (JWTNoneVerifier): The verifier instance.
            jwt_token (JWTToken): The JWT token.
            jwt_payload (JWTBearerPayload): The JWT bearer payload.
        """
        # Call multiple times
        for _ in range(10):
            await verifier.verify(jwt_token=jwt_token, jwt_payload=jwt_payload)

        # Should still work
        result = await verifier.verify(jwt_token=jwt_token, jwt_payload=jwt_payload)
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_with_empty_token_string(
        self,
        verifier: JWTNoneVerifier,
        jwt_payload: JWTPayload,
    ) -> None:
        """Test that verify works with an empty token string.

        Args:
            verifier (JWTNoneVerifier): The verifier instance.
            jwt_payload (JWTBearerPayload): The JWT bearer payload.
        """
        empty_token = JWTToken("")
        # Should not raise any exception
        await verifier.verify(jwt_token=empty_token, jwt_payload=jwt_payload)

    @pytest.mark.asyncio
    async def test_verify_with_expired_payload(
        self,
        verifier: JWTNoneVerifier,
        jwt_token: JWTToken,
    ) -> None:
        """Test that verify works even with expired payload (since it's a none verifier).

        Args:
            verifier (JWTNoneVerifier): The verifier instance.
            jwt_token (JWTToken): The JWT token.
        """
        now = datetime.datetime.now(tz=datetime.UTC)
        expired_time = now - datetime.timedelta(hours=1)

        expired_payload = JWTPayload(
            scp="read",
            aud="api1",
            iss="https://example.com",
            exp=int(expired_time.timestamp()),  # Expired
            iat=int((expired_time - datetime.timedelta(hours=2)).timestamp()),
            nbf=int((expired_time - datetime.timedelta(hours=2)).timestamp()),
            sub="user123",
        )

        # Should not raise any exception (none verifier doesn't check expiration)
        await verifier.verify(jwt_token=jwt_token, jwt_payload=expired_payload)
