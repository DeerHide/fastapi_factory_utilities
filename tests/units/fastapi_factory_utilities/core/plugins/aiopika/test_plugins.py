"""Unit tests for AiopikaPlugin."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from pydantic_core import Url

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.plugins.aiopika.configs import RabbitMQCredentialsConfig
from fastapi_factory_utilities.core.plugins.aiopika.exceptions import AiopikaPluginBaseError
from fastapi_factory_utilities.core.plugins.aiopika.plugins import AiopikaPlugin
from fastapi_factory_utilities.core.services.status.enums import (
    ComponentTypeEnum,
    HealthStatusEnum,
    ReadinessStatusEnum,
)
from fastapi_factory_utilities.core.services.status.services import StatusService


def _bind(plugin: AiopikaPlugin, *, plugins: list[object] | None = None) -> StatusService:
    fastapi_app: FastAPI = FastAPI()
    status_service: StatusService = StatusService()
    mock_app: MagicMock = MagicMock()
    mock_app.get_asgi_app.return_value = fastapi_app
    mock_app.PACKAGE_NAME = "test"
    mock_app.plugins = plugins if plugins is not None else []
    mock_app.get_status_service.return_value = status_service
    plugin.set_application(mock_app)
    plugin.on_load()
    return status_service


class TestAiopikaPluginConnectionFactory:
    """Tests for the injectable AMQP connection factory."""

    def test_inheritance(self) -> None:
        """AiopikaPlugin inherits from PluginAbstract."""
        plugin: AiopikaPlugin = AiopikaPlugin(
            rabbitmq_credentials_config=RabbitMQCredentialsConfig(amqp_url=Url("amqp://guest:guest@localhost/")),
        )
        assert isinstance(plugin, PluginAbstract)

    async def test_injected_factory_drives_startup_and_shutdown(self) -> None:
        """An injected factory is used instead of connect_robust."""
        connection: MagicMock = MagicMock()
        connection.close = AsyncMock()

        async def factory(**_kwargs: object) -> MagicMock:
            return connection

        plugin: AiopikaPlugin = AiopikaPlugin(
            rabbitmq_credentials_config=RabbitMQCredentialsConfig(amqp_url=Url("amqp://guest:guest@localhost/")),
            connection_factory=factory,
        )
        _bind(plugin)

        with patch(
            "fastapi_factory_utilities.core.plugins.aiopika.plugins.AioPikaInstrumentor",
        ) as instrumentor_cls:
            await plugin.on_startup()
            instrumentor_cls.assert_not_called()

        assert plugin.robust_connection is connection
        await plugin.on_shutdown()
        connection.close.assert_awaited_once()

    async def test_misordered_otel_names_both_plugins(self) -> None:
        """OTel in the plugin list without providers names both plugins and the order."""

        class OpenTelemetryPlugin:
            """Stand-in so type(plugin).__name__ matches."""

        plugin: AiopikaPlugin = AiopikaPlugin(
            rabbitmq_credentials_config=RabbitMQCredentialsConfig(amqp_url=Url("amqp://guest:guest@localhost/")),
        )
        _bind(plugin, plugins=[OpenTelemetryPlugin()])
        with pytest.raises(AiopikaPluginBaseError, match="OpenTelemetryPlugin must be listed before AiopikaPlugin"):
            await plugin.on_startup()

    async def test_instruments_when_otel_providers_already_on_state(self) -> None:
        """Providers on state mean OpenTelemetryPlugin loaded first; instrument."""

        class OpenTelemetryPlugin:
            """Stand-in so type(plugin).__name__ matches."""

        connection: MagicMock = MagicMock()
        connection.close = AsyncMock()

        async def factory(**_kwargs: object) -> MagicMock:
            return connection

        plugin: AiopikaPlugin = AiopikaPlugin(
            rabbitmq_credentials_config=RabbitMQCredentialsConfig(amqp_url=Url("amqp://guest:guest@localhost/")),
            connection_factory=factory,
        )
        _bind(plugin, plugins=[OpenTelemetryPlugin()])
        app: FastAPI = plugin._application.get_asgi_app()  # pylint: disable=protected-access
        app.state.tracer_provider = object()
        app.state.meter_provider = object()
        with patch(
            "fastapi_factory_utilities.core.plugins.aiopika.plugins.AioPikaInstrumentor",
        ) as instrumentor_cls:
            await plugin.on_startup()
            instrumentor_cls.return_value.instrument.assert_called_once()
        await plugin.on_shutdown()

    async def test_connect_failure_marks_broker_not_ready(self) -> None:
        """A failed AMQP connect registers MESSAGE_BROKER as not-ready."""

        async def factory(**_kwargs: object) -> AsyncMock:
            raise ConnectionError("down")

        plugin: AiopikaPlugin = AiopikaPlugin(
            rabbitmq_credentials_config=RabbitMQCredentialsConfig(amqp_url=Url("amqp://guest:guest@localhost/")),
            connection_factory=factory,
        )
        status_service: StatusService = _bind(plugin)
        with pytest.raises(AiopikaPluginBaseError, match="Unable to connect"):
            await plugin.on_startup()
        statuses = list(status_service.get_components_status_by_type()[ComponentTypeEnum.MESSAGE_BROKER].values())
        assert statuses[0]["health"] == HealthStatusEnum.UNHEALTHY
        assert statuses[0]["readiness"] == ReadinessStatusEnum.NOT_READY
