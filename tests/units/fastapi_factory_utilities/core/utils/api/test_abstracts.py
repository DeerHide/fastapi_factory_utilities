"""Unit tests for API response model utilities (dynamic response DTOs)."""

from __future__ import annotations

from types import NoneType
from typing import Any, ClassVar, cast

import pytest
from pydantic import BaseModel, Field, ValidationError

from fastapi_factory_utilities.core.utils.api import ApiResponseModelAbstract, ApiResponseSchemaBase


class _ApiNestedSubEntity(BaseModel):
    """Module-level nested model so :func:`get_type_hints` can resolve annotations."""

    id: int
    name: str = "anon"
    hidden: str = "x"


class TestBuildResponseModelEmpty:
    """``FIELDS_ALLOWED_FOR_RESPONSE`` may be empty."""

    class EmptyEntity(ApiResponseModelAbstract):
        """Entity exposing no fields in API responses."""

        FIELDS_ALLOWED_FOR_RESPONSE: ClassVar[list[str]] = []

    def test_empty_allowed_fields(self) -> None:
        """Empty list yields a response type with no fields."""
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

        FIELDS_ALLOWED_FOR_RESPONSE: ClassVar[list[str]] = ["id", "label", "tags", "count_or_none"]

        id: int
        label: str = "default-label"
        tags: list[str] = Field(default_factory=list)
        count_or_none: int | None = None
        internal_note: str = "secret"

    def test_subclass_name_doc_and_base(self) -> None:
        """Generated model metadata and inheritance."""
        response_model = self.ProductEntity.build_response_model()
        assert response_model.__name__ == "ProductEntityApiResponse"
        assert response_model.__doc__ == "API response model for ProductEntity"
        assert issubclass(response_model, ApiResponseSchemaBase)
        assert response_model.__module__ == self.ProductEntity.__module__

    def test_only_allowed_fields_on_response_model(self) -> None:
        """Internal fields are omitted from the response schema."""
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


class TestBuildResponseModelInvalidField:
    """Invalid configuration raises ``ValueError``."""

    class BadEntity(ApiResponseModelAbstract):
        """Entity listing a non-existent field for responses."""

        FIELDS_ALLOWED_FOR_RESPONSE: ClassVar[list[str]] = ["missing"]

        id: int

    def test_unknown_field_name_raises_value_error(self) -> None:
        """``FIELDS_ALLOWED_FOR_RESPONSE`` entries must exist on the model."""
        with pytest.raises(ValueError, match="Field missing is not defined on BadEntity"):
            self.BadEntity.build_response_model()


class TestBuildResponseModelExtension:
    """Consumers may subclass the dynamic response model."""

    class ItemEntity(ApiResponseModelAbstract):
        """Minimal entity."""

        FIELDS_ALLOWED_FOR_RESPONSE: ClassVar[list[str]] = ["sku"]

        sku: str

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


class TestBuildResponseModelNestedPaths:
    """Dotted ``FIELDS_ALLOWED_FOR_RESPONSE`` entries produce nested response models."""

    class ParentEntity(ApiResponseModelAbstract):
        """Entity with nested subfield and top-level attribute."""

        FIELDS_ALLOWED_FOR_RESPONSE: ClassVar[list[str]] = ["subfield.id", "subfield.name", "top"]

        subfield: _ApiNestedSubEntity
        top: str
        internal: int = 0

    class ParentEntityOptionalSub(ApiResponseModelAbstract):
        """Optional nested subfield preserves optionality on the API model."""

        FIELDS_ALLOWED_FOR_RESPONSE: ClassVar[list[str]] = ["subfield.id", "top"]

        subfield: _ApiNestedSubEntity | None = None
        top: str

    def test_nested_fields_grouped_under_subfield(self) -> None:
        """Allowed nested paths become one nested model with only those leaves."""
        response_model = cast(Any, self.ParentEntity.build_response_model())
        assert set(response_model.model_fields) == {"subfield", "top"}
        sub_ann = response_model.model_fields["subfield"].annotation
        assert sub_ann is not None
        sub_fields = set(sub_ann.model_fields) if isinstance(sub_ann, type) else set()
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

    def test_prefix_conflict_raises(self) -> None:
        """Listing both a container and a descendant path is rejected."""

        class Bad(ApiResponseModelAbstract):
            FIELDS_ALLOWED_FOR_RESPONSE: ClassVar[list[str]] = ["subfield", "subfield.id"]
            subfield: _ApiNestedSubEntity
            top: str

        with pytest.raises(ValueError, match="Conflicting field paths"):
            Bad.build_response_model()

    def test_non_nested_field_for_dotted_prefix_raises(self) -> None:
        """First segment of a dotted path must be a nested ``BaseModel`` field."""

        class Flat(ApiResponseModelAbstract):
            FIELDS_ALLOWED_FOR_RESPONSE: ClassVar[list[str]] = ["top.oops"]
            top: str

        with pytest.raises(ValueError, match="not a nested model"):
            Flat.build_response_model()
