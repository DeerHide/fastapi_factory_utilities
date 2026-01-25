"""Provides utilities for pagination."""

from fastapi import Request

from .types import PaginationPageOffset, PaginationSize


def resolve_offset(page_offset: PaginationPageOffset, page_size: PaginationSize) -> int:
    """Resolve the offset from the page offset and page size."""
    return page_offset * page_size


def depends_pagination_page_offset(request: Request) -> PaginationPageOffset:
    """Get the pagination page offset from the request.

    Args:
        request (Request): The request.

    Returns:
        PaginationPageOffset: The pagination page offset.

    Raises:
        ValidationError: If the pagination page offset is not a valid integer.
    """
    raw_page_offset: str | None = request.query_params.get("page_offset")
    if raw_page_offset is None:
        return PaginationPageOffset.default()

    return PaginationPageOffset(int(raw_page_offset))


def depends_pagination_page_size(request: Request) -> PaginationSize:
    """Get the pagination page size from the request.

    Args:
        request (Request): The request.

    Returns:
        PaginationSize: The pagination page size.

    Raises:
        ValidationError: If the pagination page size is not a valid integer.
    """
    raw_page_size: str | None = request.query_params.get("page_size")
    if raw_page_size is None:
        return PaginationSize.default()
    return PaginationSize(int(raw_page_size))


__all__: list[str] = [
    "PaginationPageOffset",
    "PaginationSize",
    "depends_pagination_page_offset",
    "depends_pagination_page_size",
    "resolve_offset",
]
