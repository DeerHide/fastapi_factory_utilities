"""Unit tests for ODM plugin."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymongo.encryption_options import AutoEncryptionOpts

from fastapi_factory_utilities.core.plugins.odm_plugin.encryption import (
    STARTUP_PROBE_COLLECTION,
    STARTUP_PROBE_FIELD,
)
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

    @pytest.mark.asyncio
    @patch("fastapi_factory_utilities.core.plugins.odm_plugin.plugins.init_beanie", new_callable=AsyncMock)
    @patch("fastapi_factory_utilities.core.plugins.odm_plugin.plugins.ODMBuilder")
    async def test_on_startup_runs_csfle_probe_when_auto_encryption_enabled(
        self,
        mock_builder_class: MagicMock,
        mock_init_beanie: AsyncMock,  # pylint: disable=unused-argument
    ) -> None:
        """The CSFLE startup probe runs once ``ODMBuilder`` produced ``auto_encryption_opts``."""
        mock_client: MagicMock = MagicMock()
        mock_client.aconnect = AsyncMock(return_value=None)
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        address_future: asyncio.Future[tuple[str, int]] = asyncio.Future()
        address_future.set_result(("localhost", 27017))
        mock_client.address = address_future

        mock_builder_instance: MagicMock = MagicMock()
        mock_builder_instance.build_all = AsyncMock(return_value=None)
        mock_builder_instance.odm_client = mock_client
        mock_builder_instance.odm_database = MagicMock()
        mock_builder_instance.odm_database.name = "payments"
        mock_builder_instance.config = MagicMock(connection_timeout_ms=4000)
        mock_builder_instance.auto_encryption_opts = AutoEncryptionOpts(
            kms_providers={"local": {"key": b"k" * 96}}, key_vault_namespace="payments.__keyVault"
        )
        mock_builder_class.return_value = mock_builder_instance

        mock_app: MagicMock = MagicMock()
        mock_app.get_status_service.return_value = MagicMock()
        mock_app.ODM_DOCUMENT_MODELS = []

        plugin: ODMPlugin = ODMPlugin()
        plugin._application = mock_app
        plugin._document_models = []

        with patch.object(ODMPlugin, "_run_csfle_startup_probe", new_callable=AsyncMock) as mock_probe:
            await plugin.on_startup()

        mock_probe.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("fastapi_factory_utilities.core.plugins.odm_plugin.plugins.init_beanie", new_callable=AsyncMock)
    @patch("fastapi_factory_utilities.core.plugins.odm_plugin.plugins.ODMBuilder")
    async def test_on_startup_skips_csfle_probe_when_auto_encryption_disabled(
        self,
        mock_builder_class: MagicMock,
        mock_init_beanie: AsyncMock,  # pylint: disable=unused-argument
    ) -> None:
        """No probe runs, and no mongocryptd dependency is introduced, when CSFLE is off."""
        mock_client: MagicMock = MagicMock()
        mock_client.aconnect = AsyncMock(return_value=None)
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        address_future: asyncio.Future[tuple[str, int]] = asyncio.Future()
        address_future.set_result(("localhost", 27017))
        mock_client.address = address_future

        mock_builder_instance: MagicMock = MagicMock()
        mock_builder_instance.build_all = AsyncMock(return_value=None)
        mock_builder_instance.odm_client = mock_client
        mock_builder_instance.odm_database = MagicMock()
        mock_builder_instance.odm_database.name = "payments"
        mock_builder_instance.config = MagicMock(connection_timeout_ms=4000)
        mock_builder_instance.auto_encryption_opts = None
        mock_builder_class.return_value = mock_builder_instance

        mock_app: MagicMock = MagicMock()
        mock_app.get_status_service.return_value = MagicMock()
        mock_app.ODM_DOCUMENT_MODELS = []

        plugin: ODMPlugin = ODMPlugin()
        plugin._application = mock_app
        plugin._document_models = []

        with patch.object(ODMPlugin, "_run_csfle_startup_probe", new_callable=AsyncMock) as mock_probe:
            await plugin.on_startup()

        mock_probe.assert_not_awaited()


class TestODMPluginCsfleStartupProbe:
    """Tests for ``ODMPlugin._run_csfle_startup_probe``."""

    # pylint: disable=protected-access

    @pytest.mark.asyncio
    async def test_probe_inserts_and_deletes_the_throwaway_document(self) -> None:
        """A successful probe inserts then deletes the same document, and nothing else."""
        mock_collection: MagicMock = MagicMock()
        mock_collection.insert_one = AsyncMock(return_value=None)
        mock_collection.delete_one = AsyncMock(return_value=None)
        mock_database: MagicMock = MagicMock()
        mock_database.__getitem__ = MagicMock(return_value=mock_collection)
        mock_client: MagicMock = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_database)

        plugin: ODMPlugin = ODMPlugin()
        plugin._odm_client = mock_client
        plugin._odm_database = MagicMock()
        plugin._odm_database.name = "payments"
        plugin._monitoring_subject = MagicMock()

        await plugin._run_csfle_startup_probe()

        mock_client.__getitem__.assert_called_once_with(plugin._odm_database.name)
        mock_database.__getitem__.assert_called_once_with(STARTUP_PROBE_COLLECTION)
        insert_doc = mock_collection.insert_one.call_args.args[0]
        delete_filter = mock_collection.delete_one.call_args.args[0]
        assert insert_doc["_id"] == delete_filter["_id"]
        assert insert_doc[STARTUP_PROBE_FIELD] == "startup-smoke-test"

    @pytest.mark.asyncio
    async def test_probe_marks_unhealthy_and_reraises_on_insert_failure(self) -> None:
        """A mongocryptd spawn/connect failure on insert fails closed."""
        mock_collection: MagicMock = MagicMock()
        mock_collection.insert_one = AsyncMock(side_effect=ConnectionError("mongocryptd unreachable"))
        mock_collection.delete_one = AsyncMock(return_value=None)
        mock_database: MagicMock = MagicMock()
        mock_database.__getitem__ = MagicMock(return_value=mock_collection)
        mock_client: MagicMock = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_database)
        mock_subject: MagicMock = MagicMock()

        plugin: ODMPlugin = ODMPlugin()
        plugin._odm_client = mock_client
        plugin._odm_database = MagicMock()
        plugin._odm_database.name = "payments"
        plugin._monitoring_subject = mock_subject

        with pytest.raises(ConnectionError, match="mongocryptd unreachable"):
            await plugin._run_csfle_startup_probe()

        mock_collection.delete_one.assert_not_awaited()
        status = mock_subject.on_next.call_args.kwargs["value"]
        assert status["health"] == HealthStatusEnum.UNHEALTHY
        assert status["readiness"] == ReadinessStatusEnum.NOT_READY

    @pytest.mark.asyncio
    async def test_probe_marks_unhealthy_and_reraises_on_delete_failure(self) -> None:
        """A failure cleaning up the throwaway document also fails closed."""
        mock_collection: MagicMock = MagicMock()
        mock_collection.insert_one = AsyncMock(return_value=None)
        mock_collection.delete_one = AsyncMock(side_effect=ConnectionError("mongocryptd unreachable"))
        mock_database: MagicMock = MagicMock()
        mock_database.__getitem__ = MagicMock(return_value=mock_collection)
        mock_client: MagicMock = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_database)
        mock_subject: MagicMock = MagicMock()

        plugin: ODMPlugin = ODMPlugin()
        plugin._odm_client = mock_client
        plugin._odm_database = MagicMock()
        plugin._odm_database.name = "payments"
        plugin._monitoring_subject = mock_subject

        with pytest.raises(ConnectionError, match="mongocryptd unreachable"):
            await plugin._run_csfle_startup_probe()

        status = mock_subject.on_next.call_args.kwargs["value"]
        assert status["health"] == HealthStatusEnum.UNHEALTHY
        assert status["readiness"] == ReadinessStatusEnum.NOT_READY
