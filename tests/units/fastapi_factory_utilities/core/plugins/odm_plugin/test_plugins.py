"""Unit tests for ODM plugin."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastapi_factory_utilities.core.plugins.odm_plugin.plugins import ODMPlugin
from fastapi_factory_utilities.core.services.status.enums import HealthStatusEnum, ReadinessStatusEnum

CUSTOM_TIMEOUT_S = 4.0


class TestODMPluginWarmPool:
    """Tests for ``ODMPlugin._warm_pool``."""

    # pylint: disable=protected-access

    @pytest.mark.asyncio
    async def test_warm_pool_issues_ping_command(self) -> None:
        """Pool warm-up issues a single ping round-trip."""
        plugin: ODMPlugin = ODMPlugin()
        mock_client: MagicMock = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})

        await plugin._warm_pool(client=mock_client, timeout_s=CUSTOM_TIMEOUT_S)

        mock_client.admin.command.assert_awaited_once_with("ping")

    @pytest.mark.asyncio
    async def test_warm_pool_swallows_failures(self) -> None:
        """Pool warm-up failures are logged but do not abort startup."""
        plugin: ODMPlugin = ODMPlugin()
        mock_client: MagicMock = MagicMock()
        mock_client.admin.command = AsyncMock(side_effect=ConnectionError("MongoDB unavailable"))

        await plugin._warm_pool(client=mock_client, timeout_s=CUSTOM_TIMEOUT_S)

        mock_client.admin.command.assert_awaited_once_with("ping")

    @pytest.mark.asyncio
    async def test_warm_pool_swallows_timeout(self) -> None:
        """Pool warm-up timeout is logged but does not abort startup."""

        async def slow_ping(*_args: object, **_kwargs: object) -> dict[str, int]:
            await asyncio.sleep(10)
            return {"ok": 1}

        plugin: ODMPlugin = ODMPlugin()
        mock_client: MagicMock = MagicMock()
        mock_client.admin.command = AsyncMock(side_effect=slow_ping)

        await plugin._warm_pool(client=mock_client, timeout_s=0.01)

        mock_client.admin.command.assert_awaited_once_with("ping")


class TestODMPluginStartup:
    """Tests for ``ODMPlugin.on_startup`` fail-fast behavior."""

    # pylint: disable=protected-access

    @pytest.mark.asyncio
    @patch("fastapi_factory_utilities.core.plugins.odm_plugin.plugins.ODMBuilder")
    async def test_on_startup_marks_unhealthy_and_reraises(self, mock_builder_class: MagicMock) -> None:
        """Connect failures mark MongoDB unhealthy and propagate to the lifespan."""
        connect_error = ConnectionError("MongoDB unavailable")
        mock_builder_instance: MagicMock = MagicMock()
        mock_builder_instance.build_all.side_effect = connect_error
        mock_builder_class.return_value = mock_builder_instance

        mock_subject: MagicMock = MagicMock()
        mock_status_service: MagicMock = MagicMock()
        mock_status_service.register_component_instance.return_value = mock_subject

        mock_app: MagicMock = MagicMock()
        mock_app.get_status_service.return_value = mock_status_service
        mock_app.ODM_DOCUMENT_MODELS = []

        plugin: ODMPlugin = ODMPlugin()
        plugin._application = mock_app

        with pytest.raises(ConnectionError, match="MongoDB unavailable"):
            await plugin.on_startup()

        status = mock_subject.on_next.call_args.kwargs["value"]
        assert status["health"] == HealthStatusEnum.UNHEALTHY
        assert status["readiness"] == ReadinessStatusEnum.NOT_READY

    @pytest.mark.asyncio
    @patch("fastapi_factory_utilities.core.plugins.odm_plugin.plugins.init_beanie", new_callable=AsyncMock)
    async def test_setup_beanie_marks_unhealthy_and_reraises(self, mock_init_beanie: AsyncMock) -> None:
        """Beanie init failures mark MongoDB unhealthy and propagate to the lifespan."""
        mock_init_beanie.side_effect = RuntimeError("beanie init failed")

        mock_subject: MagicMock = MagicMock()
        plugin: ODMPlugin = ODMPlugin()
        plugin._application = MagicMock(ODM_DOCUMENT_MODELS=[])
        plugin._odm_database = MagicMock()
        plugin._document_models = []
        plugin._monitoring_subject = mock_subject

        with pytest.raises(RuntimeError, match="beanie init failed"):
            await plugin._setup_beanie()

        status = mock_subject.on_next.call_args.kwargs["value"]
        assert status["health"] == HealthStatusEnum.UNHEALTHY
        assert status["readiness"] == ReadinessStatusEnum.NOT_READY
