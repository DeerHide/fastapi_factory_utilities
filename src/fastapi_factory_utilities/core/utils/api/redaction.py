"""Declarative redaction of :class:`Redacted`-marked fields on Pydantic models."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from functools import cache
from types import NoneType, UnionType
from typing import Any, TypeVar, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from .markers import Redacted, get_redacted_marker

TModel = TypeVar("TModel", bound=BaseModel)


def _annotation_allows_none(annotation: Any) -> bool:
    """Return ``True`` when ``annotation`` accepts ``None``."""
    if annotation is None or annotation is NoneType:
        return True
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        return any(_annotation_allows_none(arg) for arg in get_args(annotation))
    return False


def _validate_redacted_field(
    model_cls: type[BaseModel], field_name: str, field_info: FieldInfo, marker: Redacted
) -> None:
    """Raise ``TypeError`` when ``Redacted()`` defaults to ``None`` on a non-nullable field."""
    if marker.replacement is not None:
        return
    annotation = field_info.annotation
    if annotation is not None and not _annotation_allows_none(annotation):
        msg = (
            f"{model_cls.__qualname__}.{field_name}: Redacted() with default "
            f"replacement=None requires a nullable annotation; pass an explicit "
            f"replacement (e.g. Redacted('[redacted]'))."
        )
        raise TypeError(msg)


@cache
def _redacted_fields(model_cls: type[BaseModel]) -> tuple[tuple[str, Redacted], ...]:
    """Return ``(field_name, marker)`` pairs for ``model_cls``, validating markers once."""
    found: list[tuple[str, Redacted]] = []
    for field_name, field_info in model_cls.model_fields.items():
        marker = get_redacted_marker(tuple(field_info.metadata))
        if marker is None:
            continue
        _validate_redacted_field(model_cls, field_name, field_info, marker)
        found.append((field_name, marker))
    return tuple(found)


def _redact_sequence(value: list[Any] | tuple[Any, ...]) -> Any:
    """Redact items in a list or tuple; return ``value`` when unchanged."""
    new_items = [_redact_value(item) for item in value]
    if all(new is old for new, old in zip(new_items, value, strict=True)):
        return value
    if isinstance(value, tuple):
        return tuple(new_items)
    return new_items


def _redact_mapping(value: Mapping[Any, Any]) -> Any:
    """Redact values in a mapping; return ``value`` when unchanged."""
    new_items = {key: _redact_value(item) for key, item in value.items()}
    if all(new_items[key] is old for key, old in value.items()):
        return value
    return new_items


def _redact_value(value: Any) -> Any:
    """Recurse into nested models and containers; leave scalars untouched.

    Returns the original ``value`` when nothing inside needs redaction, so callers
    can skip ``model_copy`` for unmarked trees.
    """
    if isinstance(value, BaseModel):
        return redact(value)
    if isinstance(value, list | tuple):
        return _redact_sequence(value)
    if isinstance(value, Mapping):
        return _redact_mapping(value)
    return value


def redact(model: TModel) -> TModel:
    """Return a copy of ``model`` with every ``Redacted`` field replaced.

    Recurses into nested :class:`~pydantic.BaseModel` values and into
    ``list`` / ``tuple`` / ``dict`` containers. Uses ``model_copy`` without
    re-validation so entity-level validators (e.g. all-or-nothing token sets)
    do not reject the redacted snapshot. The original ``model`` is never mutated.
    When nothing is marked for redaction, returns ``model`` unchanged.

    Args:
        model: Pydantic model instance to redact.

    Returns:
        A new model instance with redacted fields, or ``model`` if unchanged.

    Raises:
        TypeError: When a field is marked ``Redacted()`` (replacement ``None``)
            but its annotation does not allow ``None``.
    """
    updates: dict[str, Any] = {}

    for field_name, marker in _redacted_fields(type(model)):
        updates[field_name] = copy.deepcopy(marker.replacement)

    for field_name in model.__class__.model_fields:
        if field_name in updates:
            continue
        current = getattr(model, field_name)
        redacted_current = _redact_value(current)
        if redacted_current is not current:
            updates[field_name] = redacted_current

    if not updates:
        return model
    return model.model_copy(update=updates, deep=True)
