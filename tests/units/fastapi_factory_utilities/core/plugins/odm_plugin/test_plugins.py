"""Unit tests for ODM plugin."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from fastapi_factory_utilities.core.plugins.odm_plugin.plugins import ODMPlugin

CUSTOM_MIN_POOL_SIZE = 5


class TestODMPluginWarmPool:
    """Tests for ``ODMPlugin._warm_pool``."""

    # pylint: disable=protected-access

    @pytest.mark.asyncio
    async def test_warm_pool_issues_min_pool_size_ping_commands(self) -> None:
        """Pool warm-up issues one ping per configured min pool connection."""
        plugin: ODMPlugin = ODMPlugin()
        mock_client: MagicMock = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})

        await plugin._warm_pool(client=mock_client, min_pool_size=CUSTOM_MIN_POOL_SIZE)

        assert mock_client.admin.command.await_count == CUSTOM_MIN_POOL_SIZE
        mock_client.admin.command.assert_awaited_with("ping")

    @pytest.mark.asyncio
    async def test_warm_pool_swallows_failures(self) -> None:
        """Pool warm-up failures are logged but do not abort startup."""
        plugin: ODMPlugin = ODMPlugin()
        mock_client: MagicMock = MagicMock()
        mock_client.admin.command = AsyncMock(side_effect=ConnectionError("MongoDB unavailable"))

        await plugin._warm_pool(client=mock_client, min_pool_size=1)

        mock_client.admin.command.assert_awaited_once_with("ping")

    @pytest.mark.asyncio
    async def test_warm_pool_uses_at_least_one_ping_when_min_pool_size_is_zero(self) -> None:
        """Pool warm-up still pings once when min pool size is zero."""
        plugin: ODMPlugin = ODMPlugin()
        mock_client: MagicMock = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})

        await plugin._warm_pool(client=mock_client, min_pool_size=0)

        mock_client.admin.command.assert_awaited_once_with("ping")
