"""Unit tests for query entity utilities (dynamic filter models)."""

from __future__ import annotations

from typing import Any, ClassVar, cast

import pytest
from pydantic import BaseModel, ValidationError

from fastapi_factory_utilities.core.utils.queries.entities import QueryFilterAbstract, SearchableEntity
from fastapi_factory_utilities.core.utils.queries.enums import QueryFieldOperatorEnum
from fastapi_factory_utilities.core.utils.queries.types import QueryField, QueryFieldName, QueryFieldOperation


class _FilterNestedSubFull(BaseModel):
    id: str
    name: int


class _FilterNestedSubIdOnly(BaseModel):
    id: str


class TestQueryFilterAbstract:
    """Tests for QueryFilterAbstract."""

    def test_empty_instance_validates(self) -> None:
        """Base filter model with no fields constructs successfully."""
        instance = QueryFilterAbstract()
        assert instance.model_fields_set == set()


class TestSearcheableEntityBuildQueryFilterModel:
    """Tests for SearcheableEntity.build_query_filter_model."""

    class EmptyEntity(SearchableEntity):
        """Entity with no searchable fields."""

        SEARCHABLE_FIELDS: ClassVar[list[str]] = []

    class ProductEntity(SearchableEntity):
        """Entity with id and count."""

        SEARCHABLE_FIELDS: ClassVar[list[str]] = ["id", "count"]
        id: str
        count: int

    def test_empty_searchable_fields_model_name_doc_and_instance(self) -> None:
        """Empty SEARCHABLE_FIELDS yields a filter type with no extra fields."""
        filter_model = self.EmptyEntity.build_query_filter_model()
        assert filter_model.__name__ == "EmptyEntityQueryFilter"
        assert filter_model.__doc__ == "Query filter for EmptyEntity"
        assert filter_model.model_fields == {}
        instance = filter_model()
        assert instance.model_fields_set == set()

    def test_happy_path_subclass_and_defaults(self) -> None:
        """Generated model subclasses QueryFilterAbstract and defaults filter fields to None."""
        filter_model = self.ProductEntity.build_query_filter_model()
        assert issubclass(filter_model, QueryFilterAbstract)
        assert set(filter_model.model_fields) == {"id", "count"}
        instance = cast(Any, filter_model())
        assert instance.id is None
        assert instance.count is None

    def test_filter_fields_have_default_none(self) -> None:
        """Each dynamic field is optional with default None."""
        filter_model = self.ProductEntity.build_query_filter_model()
        for name in ("id", "count"):
            assert filter_model.model_fields[name].default is None

    def test_query_field_value_accepted(self) -> None:
        """Non-None values must be QueryField instances."""
        filter_model = cast(Any, self.ProductEntity.build_query_filter_model())
        qf = QueryField(
            name=QueryFieldName("id"),
            operations=[QueryFieldOperation(operator=QueryFieldOperatorEnum.EQ, value="x")],
        )
        instance = filter_model(id=qf, count=None)
        assert instance.id == qf
        assert instance.count is None

    def test_non_query_field_value_rejected(self) -> None:
        """Plain scalars for a filter field fail Pydantic model validation."""
        filter_model = cast(Any, self.ProductEntity.build_query_filter_model())
        with pytest.raises(ValidationError, match="QueryField"):
            filter_model(id="not-a-query-field")

    def test_invalid_searchable_field_name_raises_value_error(self) -> None:
        """Names in SEARCHABLE_FIELDS must exist on the entity with type hints."""

        class BadEntity(SearchableEntity):
            SEARCHABLE_FIELDS: ClassVar[list[str]] = ["missing"]
            name: str

        with pytest.raises(ValueError, match="not a valid searchable field") as exc_info:
            BadEntity.build_query_filter_model()
        assert isinstance(exc_info.value.__cause__, KeyError)

    def test_dynamic_model_ignores_extra_fields(self) -> None:
        """create_model uses extra='ignore' on the filter model."""
        filter_model = self.ProductEntity.build_query_filter_model()
        assert filter_model.model_config.get("extra") == "ignore"

    def test_inherited_fields_in_searchable_list(self) -> None:
        """Derived entity can include parent annotations in SEARCHABLE_FIELDS via get_type_hints."""

        class BaseResource(SearchableEntity):
            SEARCHABLE_FIELDS: ClassVar[list[str]] = ["id"]
            id: str

        class DerivedResource(BaseResource):
            SEARCHABLE_FIELDS: ClassVar[list[str]] = ["label", *BaseResource.SEARCHABLE_FIELDS]
            label: str

        base_filter = BaseResource.build_query_filter_model()
        assert set(base_filter.model_fields) == {"id"}
        base_inst = cast(Any, base_filter())
        assert base_inst.id is None

        derived_filter = DerivedResource.build_query_filter_model()
        assert derived_filter.__name__ == "DerivedResourceQueryFilter"
        assert set(derived_filter.model_fields) == {"id", "label"}
        derived_inst = cast(Any, derived_filter())
        assert derived_inst.id is None
        assert derived_inst.label is None

    def test_child_only_lists_new_searchable_field(self) -> None:
        """Child may search only on new fields; inherited model attributes still resolve for hints."""

        class BaseResource(SearchableEntity):
            SEARCHABLE_FIELDS: ClassVar[list[str]] = ["id"]
            id: str

        class SkuVariant(BaseResource):
            SEARCHABLE_FIELDS: ClassVar[list[str]] = ["sku"]
            sku: str

        filter_model = cast(Any, SkuVariant.build_query_filter_model())
        assert set(filter_model.model_fields) == {"sku"}
        assert filter_model().sku is None

    def test_dotted_searchable_field_resolves_leaf_type(self) -> None:
        """``SEARCHABLE_FIELDS`` may list nested paths like ``subfield.id``."""

        class WithNested(SearchableEntity):
            SEARCHABLE_FIELDS: ClassVar[list[str]] = ["subfield.id", "subfield.name", "sku"]
            subfield: _FilterNestedSubFull
            sku: str

        filter_model = cast(Any, WithNested.build_query_filter_model())
        assert set(filter_model.model_fields) == {"subfield.id", "subfield.name", "sku"}
        assert filter_model().model_fields_set == set()
        qid = QueryField(
            name=QueryFieldName("subfield.id"),
            operations=[QueryFieldOperation(operator=QueryFieldOperatorEnum.EQ, value="x")],
        )
        inst = filter_model(**{"subfield.id": qid})
        assert getattr(inst, "subfield.id") == qid

    def test_dotted_searchable_invalid_path_raises(self) -> None:
        """Leaf segment must exist on the nested model."""

        class BadNested(SearchableEntity):
            SEARCHABLE_FIELDS: ClassVar[list[str]] = ["subfield.missing"]
            subfield: _FilterNestedSubIdOnly

        with pytest.raises(ValueError, match="not defined on _FilterNestedSubIdOnly"):
            BadNested.build_query_filter_model()

    def test_searchable_prefix_conflict_raises(self) -> None:
        """``subfield`` and ``subfield.id`` cannot both appear in ``SEARCHABLE_FIELDS``."""

        class Conflict(SearchableEntity):
            SEARCHABLE_FIELDS: ClassVar[list[str]] = ["subfield", "subfield.id"]
            subfield: _FilterNestedSubIdOnly

        with pytest.raises(ValueError, match="Conflicting field paths"):
            Conflict.build_query_filter_model()
