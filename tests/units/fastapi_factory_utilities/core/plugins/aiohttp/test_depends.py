"""Tests for aiohttp plugin depends."""
# pylint: disable=protected-access

from unittest.mock import MagicMock, Mock, patch

import pytest
from opentelemetry.trace import INVALID_SPAN

from fastapi_factory_utilities.core.plugins.aiohttp.constants import STATE_PREFIX_KEY
from fastapi_factory_utilities.core.plugins.aiohttp.depends import AioHttpResourceDepends
from fastapi_factory_utilities.core.plugins.aiohttp.exceptions import AioHttpClientResourceNotFoundError
from fastapi_factory_utilities.core.plugins.aiohttp.resources import AioHttpClientResource


class TestAioHttpResourceDepends:
    """Test cases for AioHttpResourceDepends class."""

    def test_init(self) -> None:
        """Test AioHttpResourceDepends initialization."""
        key = "test_service"
        depends = AioHttpResourceDepends(key=key)

        assert depends._key == key

    def test_call_with_resource_found(self) -> None:
        """Test __call__ when resource is found in app state."""
        key = "test_service"
        depends = AioHttpResourceDepends(key=key)

        # Create a mock resource
        mock_resource = MagicMock(spec=AioHttpClientResource)

        # Create a mock request with app state containing the resource
        mock_request = MagicMock()
        mock_state = MagicMock()
        setattr(mock_state, f"{STATE_PREFIX_KEY}{key}", mock_resource)
        mock_request.app.state = mock_state

        result = depends(mock_request)

        assert result == mock_resource

    def test_call_with_resource_not_found(self) -> None:
        """Test __call__ when resource is not found in app state."""
        key = "test_service"
        depends = AioHttpResourceDepends(key=key)

        # Create a mock request with app state not containing the resource
        mock_request = MagicMock()
        mock_state = MagicMock(spec=[])  # Empty spec means no attributes
        mock_request.app.state = mock_state

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN
                with pytest.raises(AioHttpClientResourceNotFoundError) as exc_info:
                    depends(mock_request)

                assert hasattr(exc_info.value, "key")
                assert getattr(exc_info.value, "key") == key

    def test_call_with_none_resource(self) -> None:
        """Test __call__ when resource is explicitly None in app state."""
        key = "test_service"
        depends = AioHttpResourceDepends(key=key)

        # Create a mock request with app state containing None for the resource
        mock_request = MagicMock()
        mock_state = MagicMock()
        setattr(mock_state, f"{STATE_PREFIX_KEY}{key}", None)
        mock_request.app.state = mock_state

        mock_logger = Mock()
        mock_logger.log = Mock()
        with patch("fastapi_factory_utilities.core.exceptions.get_logger", return_value=mock_logger):
            with patch("fastapi_factory_utilities.core.exceptions.get_current_span") as mock_span:
                mock_span.return_value = INVALID_SPAN
                with pytest.raises(AioHttpClientResourceNotFoundError):
                    depends(mock_request)

    def test_multiple_depends_with_different_keys(self) -> None:
        """Test multiple AioHttpResourceDepends with different keys."""
        key1 = "service1"
        key2 = "service2"
        depends1 = AioHttpResourceDepends(key=key1)
        depends2 = AioHttpResourceDepends(key=key2)

        # Create mock resources
        mock_resource1 = MagicMock(spec=AioHttpClientResource)
        mock_resource2 = MagicMock(spec=AioHttpClientResource)

        # Create a mock request with both resources
        mock_request = MagicMock()
        mock_state = MagicMock()
        setattr(mock_state, f"{STATE_PREFIX_KEY}{key1}", mock_resource1)
        setattr(mock_state, f"{STATE_PREFIX_KEY}{key2}", mock_resource2)
        mock_request.app.state = mock_state

        result1 = depends1(mock_request)
        result2 = depends2(mock_request)

        assert result1 == mock_resource1
        assert result2 == mock_resource2
        assert result1 != result2

    def test_state_prefix_key_is_used(self) -> None:
        """Test that STATE_PREFIX_KEY is correctly used for attribute lookup."""
        key = "my_service"
        depends = AioHttpResourceDepends(key=key)

        mock_resource = MagicMock(spec=AioHttpClientResource)
        mock_request = MagicMock()
        mock_state = MagicMock()

        # Set the resource with the correct prefixed key
        expected_attr = f"{STATE_PREFIX_KEY}{key}"
        setattr(mock_state, expected_attr, mock_resource)
        mock_request.app.state = mock_state

        result = depends(mock_request)

        assert result == mock_resource
