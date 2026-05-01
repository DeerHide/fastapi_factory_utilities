"""Unit tests for the unified :class:`ApiField` annotation marker."""

from __future__ import annotations

from typing import Annotated

import pytest

from fastapi_factory_utilities.core.utils.api import (
    ApiField,
    ApiResponseField,
    ApiResponseModelAbstract,
    SearchableEntity,
    SearchableField,
    UpdateableField,
    has_response_flag,
    has_searchable_flag,
    has_updateable_flag,
)


class TestApiFieldDefaults:
    """Default flag values on :class:`ApiField`."""

    def test_default_is_response_only(self) -> None:
        """``ApiField()`` enables only ``response``."""
        marker = ApiField()
        assert marker.response is True
        assert marker.updateable is False
        assert marker.searchable is False

    def test_explicit_flags_independent(self) -> None:
        """All three flags can be set independently."""
        marker = ApiField(response=False, updateable=True, searchable=True)
        assert marker.response is False
        assert marker.updateable is True
        assert marker.searchable is True


class TestApiFieldEqualityAndHash:
    """Equality / hashing reflect the three flags."""

    def test_equal_when_flags_match(self) -> None:
        """Markers with identical flags compare equal."""
        assert ApiField(updateable=True) == ApiField(updateable=True)

    def test_unequal_when_flags_differ(self) -> None:
        """Different flag combinations are not equal."""
        assert ApiField() != ApiField(updateable=True)
        assert ApiResponseField != UpdateableField

    def test_hashable_in_set(self) -> None:
        """Markers can live in sets."""
        bag = {ApiField(), ApiField(updateable=True), ApiField()}
        assert len(bag) == 2  # noqa: PLR2004

    def test_compares_unequal_with_non_marker(self) -> None:
        """Equality with an unrelated object returns ``False`` (via ``NotImplemented``)."""
        assert (ApiField() == "not a marker") is False


class TestPrebuiltSingletons:
    """Pre-built singletons preserve the legacy semantics."""

    def test_api_response_field_singleton(self) -> None:
        """:data:`ApiResponseField` is response-only."""
        assert ApiResponseField.response is True
        assert ApiResponseField.updateable is False
        assert ApiResponseField.searchable is False

    def test_updateable_field_singleton(self) -> None:
        """:data:`UpdateableField` keeps response and adds updateable."""
        assert UpdateableField.response is True
        assert UpdateableField.updateable is True
        assert UpdateableField.searchable is False

    def test_searchable_field_singleton_is_search_only(self) -> None:
        """:data:`SearchableField` is search-only (not exposed in responses)."""
        assert SearchableField.response is False
        assert SearchableField.updateable is False
        assert SearchableField.searchable is True


class TestFlagHelpers:
    """Helpers ``has_*`` introspect ``Annotated`` metadata tuples."""

    @pytest.mark.parametrize(
        "metadata,response,updateable,searchable",
        [
            ((ApiResponseField,), True, False, False),
            ((UpdateableField,), True, True, False),
            ((SearchableField,), False, False, True),
            ((ApiResponseField, SearchableField), True, False, True),
            ((UpdateableField, SearchableField), True, True, True),
            ((ApiField(searchable=True),), True, False, True),
            (("not-a-marker", 42), False, False, False),
        ],
    )
    def test_helpers_or_combine_flags(
        self,
        metadata: tuple[object, ...],
        response: bool,
        updateable: bool,
        searchable: bool,
    ) -> None:
        """Multiple :class:`ApiField` markers OR-combine via the ``has_*`` helpers."""
        assert has_response_flag(metadata) is response
        assert has_updateable_flag(metadata) is updateable
        assert has_searchable_flag(metadata) is searchable


class TestUnifiedAnnotationDrivesBothBuilders:
    """A single field carrying response + searchable behaves like the legacy two-marker pattern."""

    class ProductEntity(ApiResponseModelAbstract, SearchableEntity):
        """Product carrying paired response + searchable annotations."""

        id: Annotated[str, ApiField(searchable=True)]
        label: Annotated[str, ApiField(updateable=True, searchable=True)]
        internal: str = "secret"

    def test_response_model_includes_marked_fields(self) -> None:
        """``id`` and ``label`` appear on the dynamic response model."""
        response_model = self.ProductEntity.build_response_model()
        assert set(response_model.model_fields) == {"id", "label"}

    def test_updateable_paths_only_for_updateable_marker(self) -> None:
        """Only fields carrying ``ApiField(updateable=True)`` show up in updateable paths."""
        assert self.ProductEntity.get_updateable_fields() == ["label"]

    def test_query_filter_includes_searchable_fields(self) -> None:
        """Searchable fields are exposed via the dynamic query filter model."""
        filter_model = self.ProductEntity.build_query_filter_model()
        assert {"id", "label"}.issubset(set(filter_model.model_fields))

    def test_single_apifield_marker_combining_response_and_searchable(self) -> None:
        """One :class:`ApiField` instance with multiple flags is enough."""

        class Combined(ApiResponseModelAbstract, SearchableEntity):
            """Combined marker on a single field."""

            id: Annotated[str, ApiField(response=True, searchable=True)]

        response_model = Combined.build_response_model()
        filter_model = Combined.build_query_filter_model()
        assert "id" in response_model.model_fields
        assert "id" in filter_model.model_fields
