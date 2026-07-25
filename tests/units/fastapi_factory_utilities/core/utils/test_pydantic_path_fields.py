"""Unit tests for :mod:`fastapi_factory_utilities.core.utils.pydantic_path_fields`."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated

from pydantic import BaseModel

from fastapi_factory_utilities.core.utils.pydantic_path_fields import nested_basemodel_for_annotation


class _ModelA(BaseModel):
    """Sample nested model A."""

    x: int


class _ModelB(BaseModel):
    """Sample nested model B (ambiguous union peer)."""

    y: str


class TestNestedBasemodelForAnnotationDefault:
    """Default (``descend_sequences=False``) keeps sequence containers as leaves."""

    def test_direct_model(self) -> None:
        """A bare ``BaseModel`` subclass is returned."""
        assert nested_basemodel_for_annotation(_ModelA) is _ModelA

    def test_optional_model(self) -> None:
        """``Model | None`` unwraps to the model."""
        assert nested_basemodel_for_annotation(_ModelA | None) is _ModelA

    def test_list_of_model_stays_leaf(self) -> None:
        """``list[Model]`` does not descend by default (response/update shape builders)."""
        assert nested_basemodel_for_annotation(list[_ModelA]) is None

    def test_list_of_str_stays_leaf(self) -> None:
        """Scalar sequences stay leaves."""
        assert nested_basemodel_for_annotation(list[str]) is None

    def test_dict_of_model_stays_leaf(self) -> None:
        """``dict[str, Model]`` is not a sequence; stays a leaf."""
        assert nested_basemodel_for_annotation(dict[str, _ModelA]) is None

    def test_ambiguous_union_returns_none(self) -> None:
        """Two distinct model candidates are ambiguous."""
        assert nested_basemodel_for_annotation(_ModelA | _ModelB) is None

    def test_exclude_skips_matched_subclass(self) -> None:
        """``exclude=`` treats matching subclasses as non-nestable."""
        assert nested_basemodel_for_annotation(_ModelA, exclude=(_ModelA,)) is None


class TestNestedBasemodelForAnnotationDescendSequences:
    """``descend_sequences=True`` walks homogeneous sequence item types."""

    def test_list_of_model(self) -> None:
        """``list[Model]`` descends into the item type."""
        assert nested_basemodel_for_annotation(list[_ModelA], descend_sequences=True) is _ModelA

    def test_set_of_model(self) -> None:
        """``set[Model]`` descends into the item type."""
        assert nested_basemodel_for_annotation(set[_ModelA], descend_sequences=True) is _ModelA

    def test_tuple_of_model(self) -> None:
        """``tuple[Model, ...]`` descends into the item type."""
        assert nested_basemodel_for_annotation(tuple[_ModelA, ...], descend_sequences=True) is _ModelA

    def test_sequence_of_model(self) -> None:
        """``Sequence[Model]`` descends into the item type."""
        assert nested_basemodel_for_annotation(Sequence[_ModelA], descend_sequences=True) is _ModelA

    def test_optional_list_of_model(self) -> None:
        """``list[Model] | None`` unwraps then descends."""
        assert nested_basemodel_for_annotation(list[_ModelA] | None, descend_sequences=True) is _ModelA

    def test_annotated_list_of_model(self) -> None:
        """``Annotated[list[Model], ...]`` strips metadata then descends."""
        assert nested_basemodel_for_annotation(Annotated[list[_ModelA], "meta"], descend_sequences=True) is _ModelA

    def test_list_of_str_still_leaf(self) -> None:
        """Scalar sequences stay leaves even with descent enabled."""
        assert nested_basemodel_for_annotation(list[str], descend_sequences=True) is None

    def test_dict_of_model_still_leaf(self) -> None:
        """``dict`` is not a sequence origin; stays a leaf."""
        assert nested_basemodel_for_annotation(dict[str, _ModelA], descend_sequences=True) is None
