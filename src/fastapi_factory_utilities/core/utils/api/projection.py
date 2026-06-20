"""Runtime sparse fieldset projection for search/list API responses."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from fastapi_factory_utilities.core.utils.pydantic_path_fields import build_path_tree

FIELDS_QUERY_PARAM: str = "fields"


def _normalize_field_segment(segment: str) -> str:
    """Strip list notation from one dotted-path segment."""
    if segment.endswith("[]"):
        return segment[:-2]
    return segment


def _normalize_field_path(raw_path: str) -> str:
    """Normalize one dotted field path (``tasks[].name`` -> ``tasks.name``)."""
    parts = raw_path.split(".")
    if not parts or any(not part for part in parts):
        msg = f"Invalid field path: {raw_path!r}."
        raise ValueError(msg)
    return ".".join(_normalize_field_segment(part) for part in parts)


def parse_fields_param(raw_values: list[str]) -> list[str]:
    """Parse repeated or comma-separated ``fields`` query values into dotted paths.

    Args:
        raw_values: Raw ``fields`` query parameter values from the request.

    Returns:
        Deduplicated normalized dotted paths.

    Raises:
        ValueError: When a token is empty or malformed.
    """
    paths: list[str] = []
    seen: set[str] = set()
    for raw_value in raw_values:
        for token in raw_value.split(","):
            stripped = token.strip()
            if not stripped:
                continue
            normalized = _normalize_field_path(stripped)
            if normalized not in seen:
                seen.add(normalized)
                paths.append(normalized)
    return paths


def _project_value(
    value: Any,
    tree: dict[str, Any] | bool,
    *,
    always_include: tuple[str, ...],
    apply_always_include: bool,
) -> Any:
    """Project one value against a prefix-tree subtree."""
    if tree is True:
        return value

    if isinstance(value, list):
        if not isinstance(tree, dict):
            return None
        return [
            _project_value(
                item,
                tree,
                always_include=always_include,
                apply_always_include=False,
            )
            for item in value
        ]

    if isinstance(value, dict):
        if not isinstance(tree, dict):
            return None
        result: dict[str, Any] = {}
        for key, subtree in tree.items():
            if key not in value:
                continue
            projected = _project_value(
                value[key],
                subtree,
                always_include=always_include,
                apply_always_include=False,
            )
            if projected is not None or value[key] is None:
                result[key] = projected
        if apply_always_include:
            for key in always_include:
                if key in value and key not in result:
                    result[key] = value[key]
        return result

    return None


def project(
    data: Any,
    paths: list[str],
    *,
    always_include: tuple[str, ...] = ("id",),
) -> Any:
    """Prune ``data`` to the requested dotted field paths.

    Intended for search/list endpoints: pass a list of already-serialized result
    items and the parsed ``fields`` paths. Each top-level list element keeps
    ``always_include`` keys (default ``id``). Nested lists (e.g. ``tasks.name``)
    are projected element-wise.

    ponytail: no validation that paths are exposed on the entity schema; unknown
    paths are silently ignored. Upgrade: list-aware ``get_exposed_fields()`` and
    HTTP 400 on unknown paths.

    Args:
        data: Serialized response payload (typically ``list[dict]`` for search).
        paths: Normalized dotted paths from :func:`parse_fields_param`; empty list
            returns ``data`` unchanged.
        always_include: Keys always kept on each top-level search result item.

    Returns:
        Pruned copy of ``data``.

    Raises:
        ValueError: When ``paths`` contains conflicting prefix paths.
    """
    if not paths:
        return data

    tree = build_path_tree(paths)

    if isinstance(data, list):
        return [
            _project_value(
                item,
                tree,
                always_include=always_include,
                apply_always_include=True,
            )
            for item in data
        ]

    return _project_value(
        data,
        tree,
        always_include=always_include,
        apply_always_include=True,
    )


def fields_query_param(request: Request) -> list[str]:
    """FastAPI dependency that parses the ``fields`` sparse-fieldset query param.

    Args:
        request: Incoming HTTP request.

    Returns:
        Normalized dotted field paths, or an empty list when omitted.
    """
    return parse_fields_param(request.query_params.getlist(FIELDS_QUERY_PARAM))
