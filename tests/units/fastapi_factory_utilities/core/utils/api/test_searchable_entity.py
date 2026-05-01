"""Unit tests for :class:`SearchableEntity` (dynamic filter model builder)."""

from __future__ import annotations

from typing import Annotated, Any, cast

import pytest
from pydantic import BaseModel, ValidationError
from starlette.requests import Request

from fastapi_factory_utilities.core.utils.api import (
    QueryAbstract,
    QueryField,
    QueryFieldName,
    QueryFieldOperation,
    QueryFieldOperatorEnum,
    QueryFilterNestedAbstract,
    QueryResolver,
    SearchableEntity,
    SearchableField,
)


class _PlainNestedForSearchableTests(BaseModel):
    """Plain nested model (not a SearchableEntity), used for rejection tests."""

    x: int


class _CycleEntityB(SearchableEntity):
    leaf: Annotated[str, SearchableField]
    parent: Annotated[_CycleEntityA, SearchableField]


class _CycleEntityA(SearchableEntity):
    child: Annotated[_CycleEntityB, SearchableField]


_CycleEntityA.model_rebuild()
_CycleEntityB.model_rebuild()


def _request(query_string: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": query_string.encode("utf-8"),
        }
    )


class TestQueryAbstractEmpty:
    """Sanity check on the abstract base used by dynamic filters."""

    def test_empty_instance_validates(self) -> None:
        """Base filter model with no fields constructs successfully."""
        instance = QueryAbstract()
        assert instance.model_fields_set == set()


class TestSearcheableEntityBuildQueryFilterModel:
    """Tests for SearchableEntity.build_query_filter_model."""

    class EmptyEntity(SearchableEntity):
        """Entity with no searchable fields."""

    class ProductEntity(SearchableEntity):
        """Entity with id and count."""

        id: Annotated[str, SearchableField]
        count: Annotated[int, SearchableField]

    def test_empty_searchable_fields_model_name_doc_and_instance(self) -> None:
        """No Annotated searchable markers yields a filter type with no extra fields."""
        filter_model = self.EmptyEntity.build_query_filter_model()
        assert filter_model.__name__ == "EmptyEntityQueryFilter"
        assert filter_model.__doc__ == "Query filter for EmptyEntity"
        assert set(filter_model.model_fields) == {"page", "page_size", "sorts"}
        instance = filter_model()
        assert instance.model_fields_set == set()

    def test_happy_path_subclass_and_defaults(self) -> None:
        """Generated model subclasses QueryAbstract and defaults filter fields to None."""
        filter_model = self.ProductEntity.build_query_filter_model()
        assert issubclass(filter_model, QueryAbstract)
        assert set(filter_model.model_fields) == {"id", "count", "page", "page_size", "sorts"}
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

    def test_dynamic_model_ignores_extra_fields(self) -> None:
        """create_model uses extra='ignore' on the filter model."""
        filter_model = self.ProductEntity.build_query_filter_model()
        assert filter_model.model_config.get("extra") == "ignore"

    def test_inherited_fields_in_searchable_list(self) -> None:
        """Derived entity accumulates Annotated searchable fields from the MRO via get_type_hints."""

        class BaseResource(SearchableEntity):
            id: Annotated[str, SearchableField]

        class DerivedResource(BaseResource):
            label: Annotated[str, SearchableField]

        base_filter = BaseResource.build_query_filter_model()
        assert set(base_filter.model_fields) == {"id", "page", "page_size", "sorts"}
        base_inst = cast(Any, base_filter())
        assert base_inst.id is None

        derived_filter = DerivedResource.build_query_filter_model()
        assert derived_filter.__name__ == "DerivedResourceQueryFilter"
        assert set(derived_filter.model_fields) == {"id", "label", "page", "page_size", "sorts"}
        derived_inst = cast(Any, derived_filter())
        assert derived_inst.id is None
        assert derived_inst.label is None

    def test_child_union_includes_parent_searchable_fields(self) -> None:
        """Child adds searchable fields; parent Annotated searchables remain in the filter model."""

        class BaseResource(SearchableEntity):
            id: Annotated[str, SearchableField]

        class SkuVariant(BaseResource):
            sku: Annotated[str, SearchableField]

        filter_model = cast(Any, SkuVariant.build_query_filter_model())
        assert set(filter_model.model_fields) == {"id", "sku", "page", "page_size", "sorts"}
        assert filter_model().id is None
        assert filter_model().sku is None

    def test_child_shadowing_id_removes_parent_searchable(self) -> None:
        """Child may shadow a parent field with a plain annotation to drop SearchableField on that name."""

        class BaseResource(SearchableEntity):
            id: Annotated[str, SearchableField]

        class SkuOnly(BaseResource):
            id: str
            sku: Annotated[str, SearchableField]

        filter_model = cast(Any, SkuOnly.build_query_filter_model())
        assert set(filter_model.model_fields) == {"sku", "page", "page_size", "sorts"}
        assert filter_model().sku is None


class TestSearchableEntityNestedQueryFilterModel:
    """Nested SearchableEntity types become QueryFilterNestedAbstract segments on the root model."""

    class AddressEntity(SearchableEntity):
        """Nested searchable segment."""

        city: Annotated[str, SearchableField]
        street: Annotated[str, SearchableField] = ""

    class UserEntity(SearchableEntity):
        """Root entity with required nested address."""

        name: Annotated[str, SearchableField]
        address: Annotated[TestSearchableEntityNestedQueryFilterModel.AddressEntity, SearchableField]

    class UserEntityOptionalAddress(SearchableEntity):
        """Root entity with optional nested address."""

        name: Annotated[str, SearchableField]
        address: Annotated[TestSearchableEntityNestedQueryFilterModel.AddressEntity | None, SearchableField] = None

    def test_nested_field_uses_segment_base_and_inner_query_fields(self) -> None:
        """Marked nested SearchableEntity becomes an inner model with QueryField leaves."""
        filter_model = cast(Any, self.UserEntity.build_query_filter_model())
        assert issubclass(filter_model, QueryAbstract)
        assert set(filter_model.model_fields) == {"name", "address", "page", "page_size", "sorts"}
        sub_ann = filter_model.model_fields["address"].annotation
        assert sub_ann is not None
        assert isinstance(sub_ann, type) and issubclass(sub_ann, QueryFilterNestedAbstract)
        assert not issubclass(sub_ann, QueryAbstract)
        assert sub_ann.__name__ == "AddressEntityQueryFilterSegment"
        assert set(sub_ann.model_fields) == {"city", "street"}
        for leaf in ("city", "street"):
            assert "QueryField" in str(sub_ann.model_fields[leaf].annotation)

    def test_nested_instance_validate(self) -> None:
        """Root accepts a nested segment instance with QueryField leaves."""
        filter_model = cast(Any, self.UserEntity.build_query_filter_model())
        sub_cls = filter_model.model_fields["address"].annotation
        assert isinstance(sub_cls, type)
        city_qf = QueryField(
            name=QueryFieldName("address.city"),
            operations=[QueryFieldOperation(operator=QueryFieldOperatorEnum.EQ, value="Paris")],
        )
        segment = sub_cls(city=city_qf, street=None)
        root = filter_model(name=None, address=segment)
        assert root.address.city == city_qf

    def test_optional_nested_container_allows_none(self) -> None:
        """Optional nested address preserves ``None`` default on the root filter model."""
        filter_model = cast(Any, self.UserEntityOptionalAddress.build_query_filter_model())
        assert filter_model.model_fields["address"].is_required() is False
        assert filter_model.model_fields["address"].default is None
        obj = filter_model(name=None, address=None)
        assert obj.address is None

    def test_required_nested_container(self) -> None:
        """Required nested address matches source field requirement."""
        filter_model = cast(Any, self.UserEntity.build_query_filter_model())
        assert filter_model.model_fields["address"].is_required() is True

    def test_query_resolver_registers_dotted_keys(self) -> None:
        """Nested segment shape matches :class:`QueryResolver` nested BaseModel rules."""
        filter_model = cast(Any, self.UserEntity.build_query_filter_model())
        resolver = QueryResolver().from_model(filter_model)
        req = _request("address.city=Paris&address.street=Main&page=0&page_size=10")
        resolver.resolve(req)
        assert QueryFieldName("address.city") in resolver.fields
        assert QueryFieldName("address.street") in resolver.fields
        assert resolver.fields[QueryFieldName("address.city")].operations[0].value == "Paris"

    def test_plain_basemodel_nested_raises(self) -> None:
        """Nested searchable fields must use a type that subclasses SearchableEntity."""

        class BadEntity(SearchableEntity):
            """Entity nesting a plain BaseModel."""

            sub: Annotated[_PlainNestedForSearchableTests, SearchableField]
            label: Annotated[str, SearchableField]

        with pytest.raises(ValueError, match="must use a type that subclasses SearchableEntity"):
            BadEntity.build_query_filter_model()

    def test_cycle_in_nested_searchable_raises(self) -> None:
        """Mutually recursive SearchableEntity graphs raise a clear error."""
        with pytest.raises(ValueError, match="Circular SearchableEntity graph"):
            _CycleEntityA.build_query_filter_model()
