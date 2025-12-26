"""Tests for aiohttp plugin constants."""

from fastapi_factory_utilities.core.plugins.aiohttp.constants import STATE_PREFIX_KEY


class TestConstants:
    """Test cases for aiohttp plugin constants."""

    def test_state_prefix_key_value(self) -> None:
        """Test that STATE_PREFIX_KEY has the expected value."""
        assert STATE_PREFIX_KEY == "aiohttp_resource_"

    def test_state_prefix_key_is_string(self) -> None:
        """Test that STATE_PREFIX_KEY is a string."""
        assert isinstance(STATE_PREFIX_KEY, str)

    def test_state_prefix_key_not_empty(self) -> None:
        """Test that STATE_PREFIX_KEY is not empty."""
        assert len(STATE_PREFIX_KEY) > 0
