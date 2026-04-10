"""Resolve dotted field paths on nested Pydantic models (shared by API and query helpers)."""

from __future__ import annotations

from types import NoneType, UnionType
from typing import Annotated, Any, Union, get_args, get_origin, get_type_hints

from pydantic import BaseModel
from pydantic.fields import FieldInfo


def raise_if_dotted_path_prefix_conflict(field_paths: list[str]) -> None:
    """Raise if any path duplicates another or is a strict prefix of another."""
    paths = list(field_paths)
    for i, a in enumerate(paths):
        for b in paths[i + 1 :]:
            if a == b:
                msg = f"Duplicate field path: {a!r}."
                raise ValueError(msg)
            if b.startswith(a + ".") or a.startswith(b + "."):
                msg = f"Conflicting field paths {a!r} and {b!r}: one is a prefix of the other."
                raise ValueError(msg)


def build_path_tree(dotted_paths: list[str]) -> dict[str, Any]:
    """Build a prefix tree from dotted paths (leaf segments map to True)."""
    tree: dict[str, Any] = {}
    for path in dotted_paths:
        parts = path.split(".")
        node: dict[str, Any] = tree
        for i, part in enumerate(parts):
            last = i == len(parts) - 1
            if last:
                if part not in node:
                    node[part] = True
                elif node[part] is True:
                    continue
                elif isinstance(node[part], dict):
                    msg = f"Path {path!r} conflicts with a longer path under {part!r}."
                    raise ValueError(msg)
            else:
                if part not in node:
                    node[part] = {}
                elif node[part] is True:
                    msg = f"Path {path!r} conflicts with an existing leaf at {part!r}."
                    raise ValueError(msg)
                next_node = node[part]
                if not isinstance(next_node, dict):
                    msg = f"Invalid tree state at segment {part!r} for path {path!r}."
                    raise ValueError(msg)
                node = next_node
    return tree


def _is_union_origin(origin: Any) -> bool:
    return origin is Union or origin is UnionType


def unwrap_optional_annotated(annotation: Any) -> Any:
    """Strip ``Annotated`` wrappers and single-branch ``X | None`` types."""
    if annotation is None:
        return None
    ann: Any = annotation
    while get_origin(ann) is Annotated:
        ann = get_args(ann)[0]
    origin = get_origin(ann)
    args = get_args(ann)
    if origin is not None and args and _is_union_origin(origin):
        non_none = tuple(a for a in args if a is not NoneType)
        if len(non_none) == 1:
            return unwrap_optional_annotated(non_none[0])
    return ann


def nested_basemodel_for_annotation(
    annotation: Any,
    *,
    exclude: tuple[type[BaseModel], ...] = (),
) -> type[BaseModel] | None:
    """Return a nested ``BaseModel`` type to descend into, or ``None`` if not unambiguous."""
    ann = unwrap_optional_annotated(annotation)
    if ann is None:
        return None
    if isinstance(ann, type) and issubclass(ann, BaseModel):
        if exclude and any(issubclass(ann, ex) for ex in exclude):
            return None
        return ann
    origin = get_origin(ann)
    args = get_args(ann) if origin is not None else ()
    if origin is not None and args and _is_union_origin(origin):
        candidates: list[type[BaseModel]] = []
        for a in args:
            if a is NoneType:
                continue
            inner = unwrap_optional_annotated(a)
            if isinstance(inner, type) and issubclass(inner, BaseModel):
                if exclude and any(issubclass(inner, ex) for ex in exclude):
                    continue
                candidates.append(inner)
        if len(candidates) == 1:
            return candidates[0]
        return None
    return None


def resolve_leaf_annotation_and_field_info(
    model_cls: type[BaseModel],
    dotted_path: str,
    *,
    include_extras: bool,
    exclude_nested: tuple[type[BaseModel], ...] = (),
) -> tuple[Any, FieldInfo]:
    """Walk ``dotted_path`` on ``model_cls`` and return leaf annotation and :class:`FieldInfo`."""
    parts = dotted_path.split(".")
    if not parts or any(not p for p in parts):
        msg = f"Invalid dotted path: {dotted_path!r}."
        raise ValueError(msg)

    current: type[BaseModel] = model_cls
    hints: dict[str, Any] = get_type_hints(current, include_extras=include_extras)

    for i, segment in enumerate(parts):
        if segment not in current.model_fields:
            msg = f"Field {segment!r} is not defined on {current.__name__} (in path {dotted_path!r})."
            raise ValueError(msg)
        field_info = current.model_fields[segment]
        annotation = hints.get(segment, field_info.annotation)
        if i == len(parts) - 1:
            return annotation, field_info
        nested = nested_basemodel_for_annotation(annotation, exclude=exclude_nested)
        if nested is None:
            msg = (
                f"Field {segment!r} on {current.__name__} is not a single nested model type (in path {dotted_path!r})."
            )
            raise ValueError(msg)
        current = nested
        hints = get_type_hints(current, include_extras=include_extras)

    raise RuntimeError("unreachable")  # pragma: no cover
