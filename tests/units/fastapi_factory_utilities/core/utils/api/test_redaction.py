"""Unit tests for declarative :func:`redact` / :class:`Redacted`."""

from __future__ import annotations

from typing import Annotated

import pytest
from pydantic import BaseModel, Field

from fastapi_factory_utilities.core.utils.api import Redacted, get_redacted_marker, redact


class FlatSecret(BaseModel):
    """Model with a nullable redacted field."""

    name: str
    secret: Annotated[str | None, Redacted()] = None


class NestedChild(BaseModel):
    """Nested model with a redacted body."""

    label: str
    body: Annotated[str, Redacted("[redacted]")]


class NestedParent(BaseModel):
    """Parent holding nested models and a list of children."""

    title: str
    child: NestedChild
    children: list[NestedChild] = Field(default_factory=list)


class MutableReplacement(BaseModel):
    """Model whose redacted replacement is a mutable list."""

    items: Annotated[list[str], Redacted([])] = Field(default_factory=list)


class NonNullableBad(BaseModel):
    """Non-nullable field marked ``Redacted()`` without an explicit replacement."""

    token: Annotated[str, Redacted()]


class TestGetRedactedMarker:
    """``get_redacted_marker`` introspection helper."""

    def test_returns_marker_when_present(self) -> None:
        """First ``Redacted`` in metadata is returned."""
        marker = Redacted("x")
        assert get_redacted_marker((marker,)) is marker

    def test_returns_none_when_absent(self) -> None:
        """No marker yields ``None``."""
        assert get_redacted_marker(()) is None


class TestRedactFlat:
    """Flat field redaction."""

    def test_nullable_field_replaced_with_none(self) -> None:
        """``Redacted()`` clears a nullable secret."""
        original = FlatSecret(name="alice", secret="s3cret")
        result = redact(original)
        assert result.secret is None
        assert result.name == "alice"
        assert original.secret == "s3cret"

    def test_original_unchanged(self) -> None:
        """``redact`` never mutates the input model."""
        original = FlatSecret(name="bob", secret="keep")
        _ = redact(original)
        assert original.secret == "keep"

    def test_identity_when_nothing_to_redact(self) -> None:
        """Unmarked models are returned as-is (no copy)."""

        class Plain(BaseModel):
            name: str

        plain = Plain(name="x")
        assert redact(plain) is plain


class TestRedactNested:
    """Nested models and lists."""

    def test_nested_model_and_list(self) -> None:
        """Redacts nested fields and each list item."""
        original = NestedParent(
            title="t",
            child=NestedChild(label="c", body="secret-body"),
            children=[
                NestedChild(label="a", body="a-body"),
                NestedChild(label="b", body="b-body"),
            ],
        )
        result = redact(original)
        assert result.child.body == "[redacted]"
        assert result.child.label == "c"
        assert [c.body for c in result.children] == ["[redacted]", "[redacted]"]
        assert original.child.body == "secret-body"
        assert original.children[0].body == "a-body"


class TestRedactMutableReplacement:
    """Deep-copied mutable replacements."""

    def test_replacements_not_shared(self) -> None:
        """Two redacted copies do not share the same list instance."""
        a = redact(MutableReplacement(items=["x"]))
        b = redact(MutableReplacement(items=["y"]))
        assert a.items == []
        assert b.items == []
        a.items.append("mutated")
        assert b.items == []


class TestRedactNonNullable:
    """Invalid ``Redacted()`` on non-nullable fields."""

    def test_raises_type_error(self) -> None:
        """First ``redact`` call raises when replacement=None is illegal."""
        model = NonNullableBad(token="abc")
        with pytest.raises(TypeError, match="nullable"):
            redact(model)
