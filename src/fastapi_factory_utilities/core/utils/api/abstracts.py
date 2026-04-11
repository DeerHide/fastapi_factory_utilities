"""Provides utilities for the API.

Mark fields with :data:`ApiResponseField` inside :class:`typing.Annotated` on an
:class:`ApiResponseModelAbstract` subclass, then subclass the model returned by
:meth:`ApiResponseModelAbstract.build_response_model` or use it as a response schema.
"""

from typing import Annotated, Any, get_args, get_origin, get_type_hints

from pydantic import BaseModel, ConfigDict, Field, create_model
from pydantic.fields import FieldInfo

from fastapi_factory_utilities.core.utils.pydantic_path_fields import nested_basemodel_for_annotation


class ApiResponseSchemaBase(BaseModel):
    """Base class for dynamically built API response models.

    Subclass a model returned from :meth:`ApiResponseModelAbstract.build_response_model`
    to attach extra fields or behavior.
    """

    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)


class ApiResponseFieldMarker:
    """Marker class for API response fields."""


ApiResponseField = ApiResponseFieldMarker()  # pylint: disable=invalid-name


def _strip_api_response_to_value_type(hint: Any) -> Any:
    """Return ``T`` from ``Annotated[T, ..., ApiResponseField, ...]`` (unwrap nested ``Annotated``)."""
    ann: Any = hint
    while get_origin(ann) is Annotated:
        args = get_args(ann)
        if not args:
            break
        metadata = args[1:]
        if any(m is ApiResponseField or isinstance(m, ApiResponseFieldMarker) for m in metadata):
            return args[0]
        ann = args[0]
    return ann


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


class ApiResponseModelAbstract(BaseModel):
    """Abstract base for domain models that declare an API response projection.

    Exposed fields are those annotated with :data:`ApiResponseField`. Nested models must
    subclass :class:`ApiResponseModelAbstract` so their own marked fields define the nested
    response shape.

    Examples:
        Flat fields::

            class ProductEntity(ApiResponseModelAbstract):
                id: Annotated[int, ApiResponseField]
                label: Annotated[str, ApiResponseField] = "default"
                internal_note: str = "secret"


            ProductApi = ProductEntity.build_response_model()

        Nested entity::

            class AddressEntity(ApiResponseModelAbstract):
                city: Annotated[str, ApiResponseField]
                street: Annotated[str, ApiResponseField] = ""


            class UserEntity(ApiResponseModelAbstract):
                name: Annotated[str, ApiResponseField]
                address: Annotated[AddressEntity, ApiResponseField]


            UserApi = UserEntity.build_response_model()

        Optional nested container::

            class UserEntityOptional(ApiResponseModelAbstract):
                name: Annotated[str, ApiResponseField]
                address: Annotated[AddressEntity | None, ApiResponseField] = None
    """

    @classmethod
    def build_response_model(cls) -> type[ApiResponseSchemaBase]:
        """Build a new Pydantic model containing only fields marked with :data:`ApiResponseField`.

        The result subclasses :class:`ApiResponseSchemaBase` so you can extend it::

            UserApi = UserEntity.build_response_model()


            class UserApiWithMeta(UserApi):
                request_id: str
        """
        model_name: str = f"{cls.__name__}ApiResponse"
        hints: dict[str, Any] = get_type_hints(cls, include_extras=True)

        annotated_response: list[str] = []
        for field_name, hint in hints.items():
            if get_origin(hint) is Annotated:
                metadata = get_args(hint)[1:]
                if any(m is ApiResponseField or isinstance(m, ApiResponseFieldMarker) for m in metadata):
                    annotated_response.append(field_name)

        allowed = list(dict.fromkeys(annotated_response))
        model_fields_map: dict[str, FieldInfo] = dict(cls.model_fields.items())
        fields: dict[str, Any] = {}

        for field_name in allowed:
            try:
                field_info = model_fields_map[field_name]
            except KeyError as exc:
                msg = f"Field {field_name!r} is not defined on {cls.__name__}."
                raise ValueError(msg) from exc

            stripped = _strip_api_response_to_value_type(hints[field_name])
            nested_cls = nested_basemodel_for_annotation(stripped)

            if nested_cls is not None:
                if not issubclass(nested_cls, ApiResponseModelAbstract):
                    msg = (
                        f"Field {field_name!r} on {cls.__name__} nests type {nested_cls.__name__!r}; "
                        "nested API fields must use a type that subclasses ApiResponseModelAbstract."
                    )
                    raise ValueError(msg) from None
                inner_model = nested_cls.build_response_model()
                inner_ann = _container_response_annotation(field_info, inner_model)
                fields[field_name] = _field_to_create_model_spec(field_info, inner_ann)
            else:
                annotation: Any = stripped
                if annotation is None:
                    annotation = Any
                fields[field_name] = _field_to_create_model_spec(field_info, annotation)

        return create_model(
            model_name,
            __base__=ApiResponseSchemaBase,
            __module__=cls.__module__,
            __doc__=f"API response model for {cls.__name__}",
            **fields,
        )
