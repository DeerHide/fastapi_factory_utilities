"""Unit tests for pagination utilities."""

from unittest.mock import MagicMock

import pytest
from fastapi import Request

from fastapi_factory_utilities.core.utils.paginations import (
    PaginationPageOffset,
    PaginationSize,
    depends_pagination_page_offset,
    depends_pagination_page_size,
    resolve_offset,
)


class TestPaginationSize:
    """Unit tests for PaginationSize type."""

    @pytest.mark.parametrize(
        "value",
        [
            1,  # min
            50,  # default
            100,  # middle value
            200,  # max
        ],
    )
    def test_valid_creation(self, value: int) -> None:
        """Test valid creation of PaginationSize.

        Args:
            value (int): The value to test.
        """
        result = PaginationSize(value)

        assert isinstance(result, PaginationSize)
        assert isinstance(result, int)
        assert result == value

    @pytest.mark.parametrize(
        "value",
        [
            0,  # below min
            201,  # above max
            -1,  # negative
        ],
    )
    def test_validation_error(self, value: int) -> None:
        """Test validation errors for PaginationSize.

        Args:
            value (int): The invalid value to test.
        """
        with pytest.raises(ValueError, match="Invalid pagination size"):
            PaginationSize(value)

    def test_default(self) -> None:
        """Test default method returns correct value."""
        result = PaginationSize.default()

        assert isinstance(result, PaginationSize)
        assert result == PaginationSize.DEFAULT_VALUE


class TestPaginationPageOffset:
    """Unit tests for PaginationPageOffset type."""

    @pytest.mark.parametrize(
        "value",
        [
            0,  # min/default
            1,  # positive
            10,  # positive
        ],
    )
    def test_valid_creation(self, value: int) -> None:
        """Test valid creation of PaginationPageOffset.

        Args:
            value (int): The value to test.
        """
        result = PaginationPageOffset(value)

        assert isinstance(result, PaginationPageOffset)
        assert isinstance(result, int)
        assert result == value

    @pytest.mark.parametrize(
        "value",
        [
            -1,  # below min
            -10,  # negative
        ],
    )
    def test_validation_error(self, value: int) -> None:
        """Test validation errors for PaginationPageOffset.

        Args:
            value (int): The invalid value to test.
        """
        with pytest.raises(ValueError, match="Invalid pagination page offset"):
            PaginationPageOffset(value)

    def test_default(self) -> None:
        """Test default method returns correct value."""
        result = PaginationPageOffset.default()

        assert isinstance(result, PaginationPageOffset)
        assert result == PaginationPageOffset.DEFAULT_VALUE


class TestResolveOffset:
    """Unit tests for resolve_offset function."""

    @pytest.mark.parametrize(
        "page_offset,page_size,expected",
        [
            (0, 50, 0),
            (1, 50, 50),
            (2, 25, 50),
            (10, 200, 2000),
        ],
    )
    def test_resolve_offset(
        self,
        page_offset: int,
        page_size: int,
        expected: int,
    ) -> None:
        """Test resolve_offset calculation.

        Args:
            page_offset (int): The page offset value.
            page_size (int): The page size value.
            expected (int): The expected result.
        """
        result = resolve_offset(
            PaginationPageOffset(page_offset),
            PaginationSize(page_size),
        )

        assert result == expected


class TestDependsPaginationPageOffset:
    """Unit tests for depends_pagination_page_offset function."""

    def test_returns_default_when_missing(self) -> None:
        """Test returns default when query param is missing."""
        mock_request = MagicMock(spec=Request)
        mock_request.query_params.get = MagicMock(return_value=None)

        result = depends_pagination_page_offset(mock_request)

        assert isinstance(result, PaginationPageOffset)
        assert result == PaginationPageOffset.default()

    def test_returns_offset_when_valid(self) -> None:
        """Test returns PaginationPageOffset when query param is valid."""
        expected_offset = 5
        mock_request = MagicMock(spec=Request)
        mock_request.query_params.get = MagicMock(return_value=str(expected_offset))

        result = depends_pagination_page_offset(mock_request)

        assert isinstance(result, PaginationPageOffset)
        assert result == PaginationPageOffset(expected_offset)


class TestDependsPaginationPageSize:
    """Unit tests for depends_pagination_page_size function."""

    def test_returns_default_when_missing(self) -> None:
        """Test returns default when query param is missing."""
        mock_request = MagicMock(spec=Request)
        mock_request.query_params.get = MagicMock(return_value=None)

        result = depends_pagination_page_size(mock_request)

        assert isinstance(result, PaginationSize)
        assert result == PaginationSize.default()

    def test_returns_size_when_valid(self) -> None:
        """Test returns PaginationSize when query param is valid."""
        expected_size = 100
        mock_request = MagicMock(spec=Request)
        mock_request.query_params.get = MagicMock(return_value=str(expected_size))

        result = depends_pagination_page_size(mock_request)

        assert isinstance(result, PaginationSize)
        assert result == PaginationSize(expected_size)
