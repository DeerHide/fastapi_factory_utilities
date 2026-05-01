"""Unified annotation markers for API field behaviors.

The :class:`ApiField` marker carries three independent flags that drive the
introspection helpers in this package:

- ``response`` — field is exposed in dynamic API response schemas.
- ``updateable`` — field can be updated via PUT/PATCH reconciliation.
- ``searchable`` — field is exposed as a query filter on dynamic search models.

Multiple :class:`ApiField` markers may appear in a single ``Annotated`` metadata
tuple. When multiple markers are present, their flags are OR-combined when the
introspection helpers compute behavior. This lets the convenience singletons
(:data:`ApiResponseField`, :data:`UpdateableField`, :data:`SearchableField`)
compose exactly like the previous independent markers did.

Examples:
    Explicit :class:`ApiField` instances (preferred)::

        from typing import Annotated
        from fastapi_factory_utilities.core.utils.api import ApiField


        class Product(...):
            id: Annotated[int, ApiField(searchable=True)]
            label: Annotated[str, ApiField(updateable=True, searchable=True)]

    Legacy singleton aliases (:data:`ApiResponseField`, :data:`UpdateableField`,
    :data:`SearchableField`) remain available and compose with the same OR semantics.
"""

from __future__ import annotations

from typing import Any

# Public marker singletons intentionally use PascalCase names for ergonomic
# Annotated metadata usage: Annotated[..., ApiField(...)] (see module docstring).
# pylint: disable=invalid-name


class ApiField:
    """Unified annotation marker for API field behaviors.

    Carries ``response``, ``updateable``, and ``searchable`` flags. Use the module
    level singletons :data:`ApiResponseField`, :data:`UpdateableField`, and
    :data:`SearchableField` for the most common combinations, or instantiate
    directly with the desired flags for custom behavior.
    """

    __slots__ = ("_response", "_searchable", "_updateable")

    def __init__(
        self,
        *,
        response: bool = True,
        updateable: bool = False,
        searchable: bool = False,
    ) -> None:
        """Initialize the marker.

        Args:
            response: Whether the field is exposed in dynamic API response models.
            updateable: Whether the field is updateable via PUT/PATCH reconciliation.
            searchable: Whether the field is exposed as a query filter on dynamic
                search models built by :class:`SearchableEntity`.
        """
        self._response = response
        self._updateable = updateable
        self._searchable = searchable

    @property
    def response(self) -> bool:
        """Return whether the field is exposed in API response schemas."""
        return self._response

    @property
    def updateable(self) -> bool:
        """Return whether the field is updateable via PUT/PATCH reconciliation."""
        return self._updateable

    @property
    def searchable(self) -> bool:
        """Return whether the field is exposed as a query filter."""
        return self._searchable

    def __repr__(self) -> str:
        """Return a stable repr useful for debugging marker composition."""
        return f"ApiField(response={self._response}, updateable={self._updateable}, searchable={self._searchable})"

    def __eq__(self, other: object) -> bool:
        """Equality compares all three flags."""
        if not isinstance(other, ApiField):
            return NotImplemented
        return (
            self._response == other._response
            and self._updateable == other._updateable
            and self._searchable == other._searchable
        )

    def __hash__(self) -> int:
        """Hash matches :meth:`__eq__` so markers may live in sets."""
        return hash((self._response, self._updateable, self._searchable))


def has_response_flag(metadata: tuple[Any, ...]) -> bool:
    """Return ``True`` when any :class:`ApiField` marker in ``metadata`` enables ``response``."""
    return any(isinstance(meta, ApiField) and meta.response for meta in metadata)


def has_updateable_flag(metadata: tuple[Any, ...]) -> bool:
    """Return ``True`` when any :class:`ApiField` marker in ``metadata`` enables ``updateable``."""
    return any(isinstance(meta, ApiField) and meta.updateable for meta in metadata)


def has_searchable_flag(metadata: tuple[Any, ...]) -> bool:
    """Return ``True`` when any :class:`ApiField` marker in ``metadata`` enables ``searchable``."""
    return any(isinstance(meta, ApiField) and meta.searchable for meta in metadata)


ApiResponseField: ApiField = ApiField()
"""Default response marker: exposes the field in API response schemas only."""

UpdateableField: ApiField = ApiField(updateable=True)
"""Marker for fields exposed in API responses and updateable via PUT/PATCH."""

SearchableField: ApiField = ApiField(response=False, searchable=True)
"""Marker for query-only fields exposed via :class:`SearchableEntity` filter models."""
