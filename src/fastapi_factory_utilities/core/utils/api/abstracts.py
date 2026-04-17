"""Provides utilities for the API.

Mark fields with :data:`ApiResponseField` inside :class:`typing.Annotated` on an
:class:`ApiResponseModelAbstract` subclass, then subclass the model returned by
:meth:`ApiResponseModelAbstract.build_response_model` or use it as a response schema.
"""

from dataclasses import dataclass
from typing import Annotated, Any, Generic, Literal, TypeVar, get_args, get_origin, get_type_hints

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

    def __init__(self, updateable: bool = False) -> None:
        """Initialize the marker class."""
        self._updateable = updateable

    @property
    def updateable(self) -> bool:
        """Return the updateable flag."""
        return self._updateable


ApiResponseField = ApiResponseFieldMarker()  # pylint: disable=invalid-name
ApiField = ApiResponseFieldMarker()  # pylint: disable=invalid-name
UpdateableField = ApiResponseFieldMarker(updateable=True)  # pylint: disable=invalid-name
GenericModel = TypeVar("GenericModel", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class FieldChange:
    """Describe one field-level change for reconciliation."""

    path: str
    old_value: Any
    new_value: Any
    kind: Literal["updated", "added", "removed"]


@dataclass(frozen=True, slots=True)
class ReconcileResult(Generic[GenericModel]):
    """Result object returned by PUT reconciliation."""

    entity_updated: GenericModel
    changed: list[FieldChange]
    ignored_paths: list[str]
    unchanged_paths: list[str]


def _is_updateable_marker(metadata: Any) -> bool:
    """Return ``True`` when metadata marks a field as updateable."""
    return metadata is UpdateableField or (isinstance(metadata, ApiResponseFieldMarker) and metadata.updateable)


def _is_api_response_marker(metadata: Any) -> bool:
    """Return ``True`` when metadata marks a field as API-exposed."""
    return metadata is ApiResponseField or isinstance(metadata, ApiResponseFieldMarker)


def _collect_exposed_fields_for_model(
    model_cls: type[BaseModel],
    *,
    prefix: str = "",
    visited: set[type[BaseModel]] | None = None,
) -> list[str]:
    """Collect exposed paths recursively for a Pydantic model."""
    seen: set[type[BaseModel]] = set(visited or ())
    if model_cls in seen:
        return []
    seen.add(model_cls)

    hints: dict[str, Any] = get_type_hints(model_cls, include_extras=True)
    paths: list[str] = []

    for field_name, hint in hints.items():
        if get_origin(hint) is not Annotated:
            continue
        args = get_args(hint)
        metadata = args[1:]
        if not any(_is_api_response_marker(meta) for meta in metadata):
            continue

        path = f"{prefix}.{field_name}" if prefix else field_name
        nested_cls = nested_basemodel_for_annotation(args[0])
        if nested_cls is None:
            paths.append(path)
            continue

        nested_paths = _collect_exposed_fields_for_model(nested_cls, prefix=path, visited=seen)
        if nested_paths:
            paths.extend(nested_paths)
        else:
            paths.append(path)

    return paths


def _collect_updateable_fields_for_model(
    model_cls: type[BaseModel],
    *,
    prefix: str = "",
    visited: set[type[BaseModel]] | None = None,
) -> list[str]:
    """Collect updateable paths recursively for a Pydantic model."""
    seen: set[type[BaseModel]] = set(visited or ())
    if model_cls in seen:
        return []
    seen.add(model_cls)

    hints: dict[str, Any] = get_type_hints(model_cls, include_extras=True)
    paths: list[str] = []

    for field_name, hint in hints.items():
        if get_origin(hint) is not Annotated:
            continue
        args = get_args(hint)
        metadata = args[1:]
        if not any(_is_updateable_marker(meta) for meta in metadata):
            continue

        path = f"{prefix}.{field_name}" if prefix else field_name
        nested_cls = nested_basemodel_for_annotation(args[0])
        if nested_cls is None:
            paths.append(path)
            continue

        nested_paths = _collect_updateable_fields_for_model(nested_cls, prefix=path, visited=seen)
        if nested_paths:
            paths.extend(nested_paths)
        else:
            paths.append(path)

    return paths


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


def _field_to_create_required_model_spec(annotation: Any) -> tuple[Any, Any]:
    """Map annotation to a required create_model field spec."""
    return (annotation, ...)


def _container_required_annotation(field_info: FieldInfo, inner_model: type[BaseModel]) -> Any:
    """Pick wrapper type for a nested required request field."""
    if field_info.is_required():
        return inner_model
    return inner_model | None


def _is_mapping(value: Any) -> bool:
    """Return True when value behaves as a plain mapping."""
    return isinstance(value, dict)


def _flatten_dict(data: dict[str, Any], *, prefix: str = "") -> dict[str, Any]:
    """Flatten dictionaries into dotted paths."""
    flattened: dict[str, Any] = {}
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if _is_mapping(value):
            nested = _flatten_dict(value, prefix=path)
            if nested:
                flattened.update(nested)
            else:
                flattened[path] = value
            continue
        flattened[path] = value
    return flattened


def _set_by_path(target: dict[str, Any], path: str, value: Any) -> None:
    """Set nested dict value by dotted path."""
    parts = path.split(".")
    cursor: dict[str, Any] = target
    for part in parts[:-1]:
        next_value = cursor.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            cursor[part] = next_value
        cursor = next_value
    cursor[parts[-1]] = value


def _get_by_path(data: dict[str, Any], path: str) -> Any:
    """Get nested dict value by dotted path."""
    cursor: Any = data
    for part in path.split("."):
        if not isinstance(cursor, dict):
            return None
        if part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


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

    @classmethod
    def get_updateable_fields(cls) -> list[str]:
        """Return the updateable fields.

        This is useful to get the fields that can be updated when the entity is updated.
        It will return the fields that are annotated with :data:`UpdateableField`.
        It will also manage the nested fields.

        Args:
            cls: The class to get the updateable fields from.

        Returns:
            A list of the updateable fields.
        """
        return _collect_updateable_fields_for_model(cls)

    @classmethod
    def get_exposed_fields(cls) -> list[str]:
        """Return the exposed fields declared via :data:`ApiResponseField` markers."""
        return _collect_exposed_fields_for_model(cls)

    @classmethod
    def build_update_request_model(cls) -> type[ApiResponseSchemaBase]:
        """Build a PUT request model containing all exposed fields as required."""
        model_name: str = f"{cls.__name__}ApiUpdateRequest"
        hints: dict[str, Any] = get_type_hints(cls, include_extras=True)

        exposed_fields: list[str] = []
        for field_name, hint in hints.items():
            if get_origin(hint) is not Annotated:
                continue
            metadata = get_args(hint)[1:]
            if any(_is_api_response_marker(meta) for meta in metadata):
                exposed_fields.append(field_name)

        allowed = list(dict.fromkeys(exposed_fields))
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
                inner_model = nested_cls.build_update_request_model()
                inner_ann = _container_required_annotation(field_info, inner_model)
                fields[field_name] = _field_to_create_required_model_spec(inner_ann)
            else:
                annotation: Any = stripped
                if annotation is None:
                    annotation = Any
                fields[field_name] = _field_to_create_required_model_spec(annotation)

        return create_model(
            model_name,
            __base__=ApiResponseSchemaBase,
            __module__=cls.__module__,
            __doc__=f"PUT request model for {cls.__name__}",
            **fields,
        )

    @classmethod
    def reconcile_update_request(
        cls,
        *,
        entity_original: GenericModel,
        put_request: BaseModel,
        strict: bool = False,
    ) -> ReconcileResult[GenericModel]:
        """Merge PUT payload into original entity using updateable path policy."""
        updateable_paths = set(cls.get_updateable_fields())

        original_data = entity_original.model_dump(mode="python")
        request_data = put_request.model_dump(mode="python")
        flattened_request = _flatten_dict(request_data)

        ignored_paths: list[str] = []
        unchanged_paths: list[str] = []
        changes: list[FieldChange] = []
        merged_data = dict(original_data)

        for path, new_value in flattened_request.items():
            if path not in updateable_paths:
                ignored_paths.append(path)
                continue
            old_value = _get_by_path(original_data, path)
            if old_value == new_value:
                unchanged_paths.append(path)
                continue
            _set_by_path(merged_data, path, new_value)
            if old_value is None and new_value is not None:
                kind: Literal["updated", "added", "removed"] = "added"
            elif old_value is not None and new_value is None:
                kind = "removed"
            else:
                kind = "updated"
            changes.append(FieldChange(path=path, old_value=old_value, new_value=new_value, kind=kind))

        if strict and ignored_paths:
            msg = "PUT payload includes non-updateable fields: " + ", ".join(sorted(ignored_paths))
            raise ValueError(msg)

        entity_updated: GenericModel = type(entity_original).model_validate(merged_data)
        return ReconcileResult(
            entity_updated=entity_updated,
            changed=changes,
            ignored_paths=ignored_paths,
            unchanged_paths=unchanged_paths,
        )
