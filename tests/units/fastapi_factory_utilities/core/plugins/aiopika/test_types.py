"""Unit tests for Aiopika name types."""

import pytest

from fastapi_factory_utilities.core.plugins.aiopika.types import (
    ExchangeName,
    PartStr,
    QueueName,
    RoutingKey,
)


class TestPartStr:
    """Tests for PartStr."""

    def test_accepts_alphanumeric_token(self) -> None:
        """Valid part matches pattern and length bounds."""
        assert PartStr("abc") == "abc"
        assert PartStr("key_09-AB") == "key_09-AB"

    def test_wildcard_star_allowed(self) -> None:
        """Single-segment topic wildcard is allowed."""
        assert PartStr("*") == "*"

    def test_too_short_rejected(self) -> None:
        """Non-wildcard parts below min length are rejected."""
        with pytest.raises(ValueError, match="at least"):
            PartStr("ab")

    def test_bad_charset_rejected(self) -> None:
        """Characters outside the allowed set are rejected."""
        with pytest.raises(ValueError, match="pattern"):
            PartStr("bad.part")

    def test_too_long_rejected(self) -> None:
        """Parts longer than max length are rejected."""
        with pytest.raises(ValueError, match="32"):
            PartStr("x" * 33)


class TestRoutingKey:
    """Tests for RoutingKey / AbstractName."""

    def test_valid_dotted_name(self) -> None:
        """Dotted routing keys validate and expose parts."""
        rk = RoutingKey("foo.bar.baz")
        assert str(rk) == "foo.bar.baz"
        assert rk.get_parts() == [PartStr("foo"), PartStr("bar"), PartStr("baz")]

    def test_listener_pattern_with_wildcards(self) -> None:
        """Topic-style patterns with asterisks are valid."""
        rk = RoutingKey("*.*.*.*")
        assert str(rk) == "*.*.*.*"

    def test_invalid_character_rejected(self) -> None:
        """Disallowed characters in the full string are rejected."""
        with pytest.raises(ValueError, match="pattern"):
            RoutingKey("hello world")

    def test_too_short_rejected(self) -> None:
        """Full name below min length is rejected."""
        with pytest.raises(ValueError, match="at least"):
            RoutingKey("a.")

    def test_equality_same_type(self) -> None:
        """Two instances with the same value compare equal."""
        assert RoutingKey("one.two.three") == RoutingKey("one.two.three")

    def test_equality_queue_name_same_value(self) -> None:
        """AbstractName equality works across concrete subclasses."""
        value = "que.name.here"
        assert QueueName(value) == QueueName(value)

    def test_equality_with_non_name_object_is_false(self) -> None:
        """Equality with unrelated objects is false after failed name comparison."""
        assert (RoutingKey("foo.bar.baz") == object()) is False

    def test_hash_stable(self) -> None:
        """Equal names have equal hash."""
        a = ExchangeName("exc.name.here")
        b = ExchangeName("exc.name.here")
        assert hash(a) == hash(b)


class TestExchangeNameQueueName:
    """Tests for ExchangeName and QueueName."""

    def test_queue_name_parts(self) -> None:
        """QueueName splits segments like RoutingKey."""
        qn = QueueName("app.svc.queue")
        assert qn.get_parts()[1] == PartStr("svc")

    def test_exchange_name_str(self) -> None:
        """ExchangeName behaves as a string for display."""
        en = ExchangeName("dom.svc.exchange")
        assert f"{en}" == "dom.svc.exchange"
