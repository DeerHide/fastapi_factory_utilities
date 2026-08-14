"""Unit tests for AiopikaPlugin."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from pydantic_core import Url

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.plugins.aiopika.configs import RabbitMQCredentialsConfig
from fastapi_factory_utilities.core.plugins.aiopika.plugins import AiopikaPlugin


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
        connection: AsyncMock = AsyncMock()
        connection.close = AsyncMock()

        async def factory(**_kwargs: object) -> AsyncMock:
            return connection

        plugin: AiopikaPlugin = AiopikaPlugin(
            rabbitmq_credentials_config=RabbitMQCredentialsConfig(amqp_url=Url("amqp://guest:guest@localhost/")),
            connection_factory=factory,
        )
        fastapi_app: FastAPI = FastAPI()
        fastapi_app.state.tracer_provider = object()
        fastapi_app.state.meter_provider = object()
        mock_app: MagicMock = MagicMock()
        mock_app.get_asgi_app.return_value = fastapi_app
        mock_app.PACKAGE_NAME = "test"
        plugin.set_application(mock_app)
        plugin.on_load()

        with patch(
            "fastapi_factory_utilities.core.plugins.aiopika.plugins.AioPikaInstrumentor",
        ) as instrumentor_cls:
            await plugin.on_startup()
            instrumentor_cls.return_value.instrument.assert_called_once()

        assert plugin.robust_connection is connection
        await plugin.on_shutdown()
        connection.close.assert_awaited_once()
