"""Provides utilities for the API."""

from typing import Any, ClassVar, cast, get_type_hints

from pydantic import BaseModel, ConfigDict, Field, create_model
from pydantic.fields import FieldInfo

from fastapi_factory_utilities.core.utils.pydantic_path_fields import (
    build_path_tree,
    nested_basemodel_for_annotation,
    raise_if_dotted_path_prefix_conflict,
)


class ApiResponseSchemaBase(BaseModel):
    """Base class for dynamically built API response models.

    Subclass a model returned from :meth:`ApiResponseModelAbstract.build_response_model`
    to attach extra fields or behavior.
    """

    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)


def _field_to_create_model_spec(field_info: FieldInfo, annotation: Any) -> tuple[Any, Any]:
    """Map a Pydantic v2 :class:`FieldInfo` to a :func:`create_model` field spec."""
    if field_info.is_required():
        return (annotation, ...)
    if field_info.default_factory is not None:
        return (annotation, Field(default_factory=field_info.default_factory))
    return (annotation, field_info.default)


def _container_response_annotation(field_info: FieldInfo, inner_model: type[BaseModel]) -> Any:
    """Pick wrapper type for a nested response field (preserve optionality of the container)."""
    if field_info.is_required():
        return inner_model
    return inner_model | None


def _build_dynamic_subset_model(
    source: type[BaseModel],
    subtree: dict[str, Any],
    model_name: str,
    *,
    include_extras: bool,
    module: str,
) -> type[BaseModel]:
    """Recursively build a response model that exposes only paths under ``subtree``."""
    hints: dict[str, Any] = get_type_hints(source, include_extras=include_extras)
    fields: dict[str, Any] = {}

    for seg, val in subtree.items():
        if seg not in source.model_fields:
            msg = f"Field {seg!r} is not defined on {source.__name__}."
            raise ValueError(msg) from None
        field_info = source.model_fields[seg]
        if val is True:
            annotation = hints.get(seg, field_info.annotation)
            if annotation is None:
                annotation = Any
            fields[seg] = _field_to_create_model_spec(field_info, annotation)
        elif isinstance(val, dict):
            annotation = hints.get(seg, field_info.annotation)
            nested_cls = nested_basemodel_for_annotation(annotation)
            if nested_cls is None:
                msg = f"Field {seg!r} on {source.__name__} is not a single nested model type."
                raise ValueError(msg) from None
            safe_seg = seg.replace(".", "_")
            inner_name = f"{model_name}_{safe_seg}"
            inner_model = _build_dynamic_subset_model(
                nested_cls,
                cast(dict[str, Any], val),
                inner_name,
                include_extras=include_extras,
                module=module,
            )
            inner_ann = _container_response_annotation(field_info, inner_model)
            fields[seg] = _field_to_create_model_spec(field_info, inner_ann)
        else:
            msg = f"Invalid path subtree for segment {seg!r}."
            raise TypeError(msg)

    return create_model(
        model_name,
        __base__=ApiResponseSchemaBase,
        __module__=module,
        __doc__=f"Nested API response subset for {source.__name__}",
        **fields,
    )


class ApiResponseModelAbstract(BaseModel):
    """Abstract base class for the API response."""

    FIELDS_ALLOWED_FOR_RESPONSE: ClassVar[list[str]] = []

    @classmethod
    def build_response_model(cls) -> type[ApiResponseSchemaBase]:
        """Build a new Pydantic model with only the allowed fields.

        The result subclasses :class:`ApiResponseSchemaBase` so you can extend it::

            UserApi = User.build_response_model()


            class UserApiWithMeta(UserApi):
                request_id: str
        """
        allowed = list(cls.FIELDS_ALLOWED_FOR_RESPONSE)
        raise_if_dotted_path_prefix_conflict(allowed)

        model_name: str = f"{cls.__name__}ApiResponse"
        hints: dict[str, Any] = get_type_hints(cls, include_extras=True)
        fields: dict[str, Any] = {}

        plain = [f for f in allowed if "." not in f]
        dotted = [f for f in allowed if "." in f]

        model_fields_map: dict[str, FieldInfo] = dict(cls.model_fields.items())

        for field_name in plain:
            try:
                field_info = model_fields_map[field_name]
            except KeyError as exc:
                msg = f"Field {field_name} is not defined on {cls.__name__}."
                raise ValueError(msg) from exc
            annotation = hints.get(field_name, field_info.annotation)
            if annotation is None:
                annotation = Any
            fields[field_name] = _field_to_create_model_spec(field_info, annotation)

        if dotted:
            tree = build_path_tree(dotted)
            for prefix, subtree in tree.items():
                if prefix not in model_fields_map:
                    msg = f"Field {prefix} is not defined on {cls.__name__}."
                    raise ValueError(msg) from None
                field_info = model_fields_map[prefix]
                annotation = hints.get(prefix, field_info.annotation)
                nested_cls = nested_basemodel_for_annotation(annotation)
                if nested_cls is None:
                    msg = (
                        f"Field {prefix!r} is not a nested model on {cls.__name__}; "
                        f"cannot build nested response fields {subtree!r}."
                    )
                    raise ValueError(msg) from None
                if not isinstance(subtree, dict):
                    msg = f"Invalid nested path tree for field {prefix!r}."
                    raise TypeError(msg)
                safe_prefix = prefix.replace(".", "_")
                inner_name = f"{model_name}_{safe_prefix}"
                inner_model = _build_dynamic_subset_model(
                    nested_cls,
                    cast(dict[str, Any], subtree),
                    inner_name,
                    include_extras=True,
                    module=cls.__module__,
                )
                inner_ann = _container_response_annotation(field_info, inner_model)
                fields[prefix] = _field_to_create_model_spec(field_info, inner_ann)

        return create_model(
            model_name,
            __base__=ApiResponseSchemaBase,
            __module__=cls.__module__,
            __doc__=f"API response model for {cls.__name__}",
            **fields,
        )
