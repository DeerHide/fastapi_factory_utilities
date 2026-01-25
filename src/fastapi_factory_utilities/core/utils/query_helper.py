"""Provides utility functions for query parameters helpers.

Objectives:
- Provide a way to simplify the process to code a search endpoint with query parameters filtering.
"""

from typing import Any

from fastapi import Request


class QueryFilterValidationError(ValueError):
    """Exception raised when a query filter is invalid."""


class QueryFilterUnauthorizedError(ValueError):
    """Exception raised when a query filter is unauthorized."""


class QueryFilterHelper:
    """Helper class to filter query parameters as a Dependency."""

    def __init__(
        self,
        authorized_filters: dict[str, type],
        raise_on_unauthorized_filter: bool = True,
        raise_on_invalid_filter: bool = True,
    ) -> None:
        """Initialize the QueryFilterHelper.

        Args:
            authorized_filters (dict[str, type]): The authorized filters.
            raise_on_unauthorized_filter (bool): Whether to raise an exception if an unauthorized filter is provided.
            raise_on_invalid_filter (bool): Whether to raise an exception if an invalid filter is provided.
        """
        self._authorized_filters: dict[str, type] = authorized_filters
        self._raise_on_unauthorized_filter: bool = raise_on_unauthorized_filter
        self._raise_on_invalid_filter: bool = raise_on_invalid_filter
        self._filters: dict[str, Any] = {}

    def _raise_on_unauthorized_filter_error(self, key: str) -> None:
        """Raise an unauthorized filter exception.

        Args:
            key (str): The key of the unauthorized filter.
        """
        if self._raise_on_unauthorized_filter:
            raise QueryFilterUnauthorizedError(f"Unauthorized filter: {key}")

    def _raise_on_invalid_filter_error(self, key: str, value: Any, error: Exception) -> None:
        """Raise an invalid filter exception.

        Args:
            key (str): The key of the invalid filter.
            value (Any): The value of the invalid filter.
            error (Exception): The error that occurred while transforming the filter.

        Raises:
            QueryFilterValidationError: If the filter is invalid and raise_on_invalid_filter is True.
        """
        if self._raise_on_invalid_filter:
            raise QueryFilterValidationError(f"Invalid filter: {key} with value: {value}") from error

    def _transform_filter(self, key: str, value: Any, filter_type: type) -> Any | None:
        """Transform the filter.

        Args:
            key (str): The key of the filter.
            value (Any): The value of the filter.
            filter_type (type): The type of the filter.

        Returns:
            Any: The transformed filter.

        Raises:
            QueryFilterValidationError: If the filter is invalid.
        """
        # If the value is already of the correct type, return it
        if isinstance(value, filter_type):
            return value
        try:
            return filter_type(value)
        except ValueError as e:
            self._raise_on_invalid_filter_error(key=key, value=value, error=e)
        return None

    def validate_filters(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Validate the filters.

        Args:
            filters (dict[str, Any]): The filters.

        Returns:
            dict[str, Any]: The validated filters.

        Raises:
            QueryFilterUnauthorizedError: If an unauthorized filter is provided
            and raise_on_unauthorized_filter is True.
            QueryFilterValidationError: If an invalid filter is provided
            and raise_on_invalid_filter is True.
        """
        validated_filters: dict[str, Any] = {}
        for key, value in filters.items():
            if key not in self._authorized_filters:
                self._raise_on_unauthorized_filter_error(key=key)
            transformed_value: Any | None = self._transform_filter(
                key=key, value=value, filter_type=self._authorized_filters[key]
            )
            if transformed_value is not None:
                validated_filters[key] = transformed_value
        return validated_filters

    def __call__(self, request: Request) -> dict[str, Any]:
        """Call the QueryFilterHelper."""
        self._filters = self.validate_filters(filters=dict(request.query_params.items()))
        return self._filters


__all__: list[str] = [
    "QueryFilterHelper",
    "QueryFilterUnauthorizedError",
    "QueryFilterValidationError",
]
