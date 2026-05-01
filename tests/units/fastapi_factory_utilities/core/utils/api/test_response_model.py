"""Unit tests for API response model utilities (dynamic response DTOs)."""

from __future__ import annotations

from types import NoneType
from typing import Annotated, Any, cast

import pytest
from pydantic import BaseModel, Field, ValidationError

from fastapi_factory_utilities.core.utils.api import (
    ApiField,
    ApiResponseField,
    ApiResponseModelAbstract,
    ApiResponseSchemaBase,
    UpdateableField,
)


class TestBuildResponseModelEmpty:
    """Models with no ``Annotated[..., ApiResponseField]`` fields yield an empty schema."""

    class EmptyEntity(ApiResponseModelAbstract):
        """Entity exposing no fields in API responses."""

    def test_empty_allowed_fields(self) -> None:
        """No marked fields yields a response type with no fields."""
        response_model = self.EmptyEntity.build_response_model()
        assert response_model.__name__ == "EmptyEntityApiResponse"
        assert response_model.__doc__ == "API response model for EmptyEntity"
        assert issubclass(response_model, ApiResponseSchemaBase)
        assert response_model.model_fields == {}
        instance = response_model()
        assert instance.model_fields_set == set()


class TestBuildResponseModelHappyPath:
    """``build_response_model`` copies types, defaults, and default_factory."""

    class ProductEntity(ApiResponseModelAbstract):
        """Sample entity with mixed field kinds."""

        id: Annotated[int, ApiResponseField]
        label: Annotated[str, ApiResponseField] = "default-label"
        tags: Annotated[list[str], ApiResponseField] = Field(default_factory=list)
        count_or_none: Annotated[int | None, ApiResponseField] = None
        internal_note: str = "secret"

    def test_subclass_name_doc_and_base(self) -> None:
        """Generated model metadata and inheritance."""
        response_model = self.ProductEntity.build_response_model()
        assert response_model.__name__ == "ProductEntityApiResponse"
        assert response_model.__doc__ == "API response model for ProductEntity"
        assert issubclass(response_model, ApiResponseSchemaBase)
        assert response_model.__module__ == self.ProductEntity.__module__

    def test_only_allowed_fields_on_response_model(self) -> None:
        """Unmarked fields are omitted from the response schema."""
        response_model = self.ProductEntity.build_response_model()
        assert set(response_model.model_fields) == {"id", "label", "tags", "count_or_none"}
        assert "internal_note" not in response_model.model_fields

    def test_required_optional_and_default_factory_preserved(self) -> None:
        """Field requirement, defaults, and factories match the source model."""
        response_model = self.ProductEntity.build_response_model()
        assert response_model.model_fields["id"].is_required() is True
        assert response_model.model_fields["label"].is_required() is False
        assert response_model.model_fields["label"].default == "default-label"
        assert response_model.model_fields["tags"].default_factory is list
        assert response_model.model_fields["count_or_none"].default is None

    def test_instances_validate_like_source_subset(self) -> None:
        """Valid data constructs; missing required field fails."""
        response_model = cast(Any, self.ProductEntity.build_response_model())
        obj = response_model(id=1)
        assert obj.id == 1
        assert obj.label == "default-label"
        assert obj.tags == []
        assert obj.count_or_none is None
        with pytest.raises(ValidationError):
            response_model()

    def test_default_factory_is_not_shared_across_instances(self) -> None:
        """Each instance gets a fresh factory result (list)."""
        response_model = cast(Any, self.ProductEntity.build_response_model())
        a = response_model(id=1)
        b = response_model(id=2)
        a.tags.append("a")
        assert b.tags == []


class _PlainNestedBaseModel(BaseModel):
    id: int


class TestBuildResponseModelNestedMustSubclassAbstract:
    """Nested ``BaseModel`` types that are not ``ApiResponseModelAbstract`` are rejected."""

    class BadEntity(ApiResponseModelAbstract):
        """Entity whose nested field is a plain ``BaseModel``."""

        subfield: Annotated[_PlainNestedBaseModel, ApiResponseField]

    def test_plain_nested_raises_value_error(self) -> None:
        """Nested API fields must subclass ``ApiResponseModelAbstract``."""
        with pytest.raises(ValueError, match="must use a type that subclasses ApiResponseModelAbstract"):
            self.BadEntity.build_response_model()


class TestBuildResponseModelExtension:
    """Consumers may subclass the dynamic response model."""

    class ItemEntity(ApiResponseModelAbstract):
        """Minimal entity."""

        sku: Annotated[str, ApiResponseField]

    def test_subclass_adds_fields(self) -> None:
        """Extending the generated class keeps base fields and adds new ones."""
        base_response = self.ItemEntity.build_response_model()

        class ItemWithMeta(base_response):  # type: ignore[misc,valid-type]
            """Extended API response."""

            request_id: str = ""

        item_cls = cast(Any, ItemWithMeta)
        instance = item_cls(sku="ABC", request_id="req-1")
        assert instance.sku == "ABC"
        assert instance.request_id == "req-1"


class ApiNestedSubEntity(ApiResponseModelAbstract):
    """Module-level nested model: id and name exposed; hidden is internal."""

    id: Annotated[int, ApiResponseField]
    name: Annotated[str, ApiResponseField] = "anon"
    hidden: str = "x"


class ApiNestedSubEntityIdOnly(ApiResponseModelAbstract):
    """Nested model exposing only ``id`` (for optional-container test)."""

    id: Annotated[int, ApiResponseField]
    name: str = "anon"
    hidden: str = "x"


class TestBuildResponseModelNestedMarkedTypes:
    """Nested ``ApiResponseModelAbstract`` types become nested response models."""

    class ParentEntity(ApiResponseModelAbstract):
        """Entity with nested subfield and top-level attribute."""

        subfield: Annotated[ApiNestedSubEntity, ApiResponseField]
        top: Annotated[str, ApiResponseField]
        internal: int = 0

    class ParentEntityOptionalSub(ApiResponseModelAbstract):
        """Optional nested subfield preserves optionality on the API model."""

        subfield: Annotated[ApiNestedSubEntityIdOnly | None, ApiResponseField] = None
        top: Annotated[str, ApiResponseField]

    def test_nested_fields_grouped_under_subfield(self) -> None:
        """Marked nested type becomes one nested model with only its marked leaves."""
        response_model = cast(Any, self.ParentEntity.build_response_model())
        assert set(response_model.model_fields) == {"subfield", "top"}
        sub_ann = response_model.model_fields["subfield"].annotation
        assert sub_ann is not None
        assert isinstance(sub_ann, type) and issubclass(sub_ann, BaseModel)
        sub_fields = set(sub_ann.model_fields)
        assert sub_fields == {"id", "name"}
        assert "hidden" not in sub_fields
        obj = response_model(subfield={"id": 1, "name": "n"}, top="ok")
        assert obj.subfield.id == 1
        assert obj.subfield.name == "n"
        assert obj.top == "ok"

    def test_optional_nested_container(self) -> None:
        """Optional parent field allows ``subfield=None`` on the response model."""
        response_model = cast(Any, self.ParentEntityOptionalSub.build_response_model())
        obj = response_model(subfield=None, top="t")
        assert obj.subfield is None
        assert obj.top == "t"
        inner = response_model.model_fields["subfield"].annotation
        args = getattr(inner, "__args__", ())
        non_none = [a for a in args if a is not NoneType]
        assert len(non_none) == 1
        inner_model = non_none[0]
        assert set(inner_model.model_fields) == {"id"}


class _UpdateablePlainNestedModel(BaseModel):
    """Plain nested model with one marked updateable field."""

    code: Annotated[str, UpdateableField]
    hidden: str


class _UpdateableApiNestedModel(ApiResponseModelAbstract):
    """API nested model with one marked updateable field."""

    name: Annotated[str, UpdateableField]
    status: str


class TestGetUpdateableFields:
    """`get_updateable_fields` supports flat and nested updateable markers."""

    class FlatEntity(ApiResponseModelAbstract):
        """Flat entity with mixed updateable and non-updateable fields."""

        id: int
        label: Annotated[str, UpdateableField]
        count: Annotated[int, UpdateableField]
        internal: str

    class NestedEntity(ApiResponseModelAbstract):
        """Entity with nested API and plain BaseModel updateable fields."""

        title: Annotated[str, UpdateableField]
        api_nested: Annotated[_UpdateableApiNestedModel, UpdateableField]
        plain_nested: Annotated[_UpdateablePlainNestedModel, UpdateableField]
        optional_nested: Annotated[_UpdateableApiNestedModel | None, UpdateableField] = None
        metadata: Annotated[dict[str, Any], UpdateableField] = Field(default_factory=dict)
        hidden: str = ""

    def test_returns_only_flat_marked_fields(self) -> None:
        """Flat model returns only fields marked with `UpdateableField`."""
        assert set(self.FlatEntity.get_updateable_fields()) == {"label", "count"}

    def test_returns_nested_dotted_paths_for_supported_nested_models(self) -> None:
        """Nested BaseModel-like containers return dotted updateable paths."""
        assert set(self.NestedEntity.get_updateable_fields()) == {
            "title",
            "api_nested.name",
            "plain_nested.code",
            "optional_nested.name",
            "metadata",
        }


class _UpdatePolicyChildEntity(ApiResponseModelAbstract):
    """Nested entity: one updateable leaf, one API-only leaf (module-level for type hints)."""

    slug: Annotated[str, UpdateableField]
    title: Annotated[str, ApiResponseField] = "t"


class _UpdatePolicyParentApiOnlyChildEntity(ApiResponseModelAbstract):
    """Parent marks ``child`` with ``ApiResponseField`` only (not ``UpdateableField``)."""

    child: Annotated[_UpdatePolicyChildEntity, ApiResponseField]
    owner: Annotated[str, UpdateableField]


class _UpdatePolicyParentOptionalChildEntity(ApiResponseModelAbstract):
    """Optional API-exposed nested container."""

    child: Annotated[_UpdatePolicyChildEntity | None, ApiResponseField] = None


class _UpdatePolicyMiddleEntity(ApiResponseModelAbstract):
    """Intermediate API-only nest."""

    child: Annotated[_UpdatePolicyChildEntity, ApiResponseField]


class _UpdatePolicyRootEntity(ApiResponseModelAbstract):
    """Two-level API-only chain down to updateable leaf."""

    middle: Annotated[_UpdatePolicyMiddleEntity, ApiResponseField]


class _NullableNoteForReconcileEntity(ApiResponseModelAbstract):
    """Nullable note exposed and updateable (required on PUT schema)."""

    note: Annotated[str | None, ApiResponseField, UpdateableField] = None


class TestGetUpdateableFieldsApiExposedNested:
    """Nested updateable leaves must appear even when the parent field is only API-exposed."""

    def test_nested_updateable_paths_under_api_only_parent(self) -> None:
        """``get_updateable_fields`` walks ``ApiResponseField`` nests to find ``UpdateableField`` leaves."""
        assert set(_UpdatePolicyParentApiOnlyChildEntity.get_updateable_fields()) == {"owner", "child.slug"}

    def test_optional_api_nested_still_exposes_nested_updateable_paths(self) -> None:
        """Optional ``Child | None`` preserves nested updateable path collection."""
        assert set(_UpdatePolicyParentOptionalChildEntity.get_updateable_fields()) == {"child.slug"}

    def test_deep_api_only_chain_collects_leaf_updateable(self) -> None:
        """Multiple API-only levels before an ``UpdateableField`` leaf yield a dotted path."""
        assert set(_UpdatePolicyRootEntity.get_updateable_fields()) == {"middle.child.slug"}

    def test_scalar_may_combine_api_response_and_updateable_annotations(self) -> None:
        """A field can be both exposed and updateable via multiple metadata entries."""

        class Both(ApiResponseModelAbstract):
            code: Annotated[str, ApiResponseField, UpdateableField]

        assert Both.get_updateable_fields() == ["code"]

    def test_custom_apifield_with_updateable_true(self) -> None:
        """``ApiField(updateable=True)`` is treated like :data:`UpdateableField`."""

        class Custom(ApiResponseModelAbstract):
            ref: Annotated[str, ApiField(updateable=True)]

        assert Custom.get_updateable_fields() == ["ref"]

    def test_searchable_only_field_not_exposed(self) -> None:
        """A field carrying only an :class:`ApiField` with ``response=False`` is not exposed."""

        class SearchOnlyEntity(ApiResponseModelAbstract):
            id: Annotated[str, ApiResponseField]
            internal_searchable: Annotated[str, ApiField(response=False, searchable=True)] = ""

        response_model = SearchOnlyEntity.build_response_model()
        assert set(response_model.model_fields) == {"id"}


class TestReconcileUpdateRequest:
    """``reconcile_update_request`` respects ``get_updateable_fields`` path policy."""

    def test_reconcile_updates_nested_leaf_when_parent_is_api_only(self) -> None:
        """PUT flattens nested keys; nested updateable leaves merge even without container marker."""
        original = _UpdatePolicyParentApiOnlyChildEntity(
            child=_UpdatePolicyChildEntity(slug="a", title="orig-title"),
            owner="me",
        )
        put_cls = cast(Any, _UpdatePolicyParentApiOnlyChildEntity.build_update_request_model())
        put_request = put_cls.model_validate(
            {
                "child": {"slug": "b", "title": "new-title"},
                "owner": "me",
            }
        )
        result = _UpdatePolicyParentApiOnlyChildEntity.reconcile_update_request(
            entity_original=original,
            put_request=put_request,
        )

        assert result.entity_updated.child.slug == "b"
        assert result.entity_updated.child.title == "orig-title"
        assert result.entity_updated.owner == "me"
        assert {c.path for c in result.changed} == {"child.slug"}
        assert set(result.ignored_paths) == {"child.title"}
        assert set(result.unchanged_paths) == {"owner"}

    def test_reconcile_classifies_added_and_removed_scalar(self) -> None:
        """Scalar transitions to/from ``None`` yield ``added`` / ``removed`` change kinds."""
        original = _NullableNoteForReconcileEntity(note=None)
        put_cls = cast(Any, _NullableNoteForReconcileEntity.build_update_request_model())
        put_set = put_cls.model_validate({"note": "hello"})
        set_result = _NullableNoteForReconcileEntity.reconcile_update_request(
            entity_original=original,
            put_request=put_set,
        )
        assert set_result.changed[0].kind == "added"

        put_clear = put_cls.model_validate({"note": None})
        clear_result = _NullableNoteForReconcileEntity.reconcile_update_request(
            entity_original=_NullableNoteForReconcileEntity(note="hello"),
            put_request=put_clear,
        )
        assert clear_result.changed[0].kind == "removed"
