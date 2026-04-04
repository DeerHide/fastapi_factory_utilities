"""Provides the helpers for the pagination utilities."""

from .types import PaginationPageOffset, PaginationSize


def resolve_offset(page_offset: PaginationPageOffset, page_size: PaginationSize) -> int:
    """Resolve the offset from the page offset and page size."""
    return page_offset * page_size
