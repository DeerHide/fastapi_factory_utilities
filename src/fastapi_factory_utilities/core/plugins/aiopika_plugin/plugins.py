"""Provides the Aiopika plugin.

OpenTelemetry instrumentation is optional. If ``OpenTelemetryPlugin`` is in
the application plugin list it MUST appear before ``AiopikaPlugin`` so tracer
and meter providers are on application state. With no OpenTelemetry plugin,
the AMQP connection starts without instrumentation.
"""

from collections.abc import Awaitable, Callable
from typing import Any, cast

from aio_pika import connect_robust  # pyright: ignore[reportUnknownMemberType]
from aio_pika.abc import AbstractRobustConnection
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor  # pyright: ignore[reportMissingTypeStubs]
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from structlog.stdlib import BoundLogger, get_logger

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.plugins.aiopika_plugin.builder import build_rabbitmq_credentials_config
from fastapi_factory_utilities.core.plugins.aiopika_plugin.configs import RabbitMQCredentialsConfig
from fastapi_factory_utilities.core.plugins.state import AIOPIKA_CONNECTION, METER_PROVIDER, TRACER_PROVIDER
from fastapi_factory_utilities.core.plugins.status import PluginStatusMixin
from fastapi_factory_utilities.core.services.status.enums import ComponentTypeEnum

from .exceptions import AiopikaPluginBaseError

_logger: BoundLogger = get_logger(__package__)

ConnectionFactory = Callable[..., Awaitable[AbstractRobustConnection]]

_OTEL_PLUGIN_NAME: str = "OpenTelemetryPlugin"
_AIOPIKA_PLUGIN_NAME: str = "AiopikaPlugin"


class AiopikaPlugin(PluginStatusMixin, PluginAbstract):
    """Aiopika plugin."""

    def __init__(
        self,
        rabbitmq_credentials_config: RabbitMQCredentialsConfig | None = None,
        connection_factory: ConnectionFactory | None = None,
    ) -> None:
        """Initialize the Aiopika plugin.

        Args:
            rabbitmq_credentials_config: Optional injected credentials (skips YAML).
            connection_factory: Optional AMQP connection factory. Defaults to
                ``aio_pika.connect_robust``. Tests inject a double here instead of
                patching this module.
        """
        super().__init__()
        self._rabbitmq_credentials_config: RabbitMQCredentialsConfig | None = rabbitmq_credentials_config
        self._connection_factory: ConnectionFactory = connection_factory or connect_robust
        self._robust_connection: AbstractRobustConnection | None = None

    @property
    def robust_connection(self) -> AbstractRobustConnection:
        """Get the robust connection."""
        assert self._robust_connection is not None
        return self._robust_connection

    def on_load(self) -> None:
        """On load."""
        assert self._application is not None

        # Build the RabbitMQ credentials configuration if not provided
        if self._rabbitmq_credentials_config is None:
            self._rabbitmq_credentials_config = build_rabbitmq_credentials_config(
                package_name=self._application.PACKAGE_NAME
            )

    def _otel_plugin_registered(self) -> bool:
        """Return True when ``OpenTelemetryPlugin`` is in the application plugin list."""
        if self._application is None:
            return False
        plugins = getattr(self._application, "plugins", [])
        return any(type(plugin).__name__ == _OTEL_PLUGIN_NAME for plugin in plugins)

    def _maybe_instrument(self) -> None:
        """Instrument AMQP when OTel providers are present; fail clearly on mis-order."""
        assert self._application is not None
        app_state = self._application.get_asgi_app().state
        tracer_provider: TracerProvider | None = cast(
            TracerProvider | None, getattr(app_state, TRACER_PROVIDER.attr, None)
        )
        meter_provider: MeterProvider | None = cast(MeterProvider | None, getattr(app_state, METER_PROVIDER.attr, None))
        if tracer_provider is not None and meter_provider is not None:
            AioPikaInstrumentor().instrument(
                tracer_provider=tracer_provider,
                meter_provider=meter_provider,
            )
            return
        if self._otel_plugin_registered():
            raise AiopikaPluginBaseError(
                f"{_OTEL_PLUGIN_NAME} must be listed before {_AIOPIKA_PLUGIN_NAME} "
                "so tracer and meter providers are on application state."
            )
        _logger.debug("OpenTelemetry plugin not registered; starting AMQP without instrumentation.")

    def _on_amqp_close(self, *_args: Any, **_kwargs: Any) -> None:
        """Arm not-ready after a sustained disconnect; ignore shutdown closes."""
        self._arm_unhealthy()

    def _on_amqp_reconnect(self, *_args: Any, **_kwargs: Any) -> None:
        """A successful reconnect cancels the grace timer and marks ready."""
        self._report_healthy()

    def _bind_connection_callbacks(self) -> None:
        """Watch robust-connection close/reconnect without hooking publish errors."""
        assert self._robust_connection is not None
        close_callbacks = getattr(self._robust_connection, "close_callbacks", None)
        reconnect_callbacks = getattr(self._robust_connection, "reconnect_callbacks", None)
        if close_callbacks is not None and hasattr(close_callbacks, "add"):
            close_callbacks.add(self._on_amqp_close)
        if reconnect_callbacks is not None and hasattr(reconnect_callbacks, "add"):
            reconnect_callbacks.add(self._on_amqp_reconnect)

    async def on_startup(self) -> None:
        """On startup."""
        assert self._application is not None
        assert self._rabbitmq_credentials_config is not None
        self._setup_status(component_type=ComponentTypeEnum.MESSAGE_BROKER, identifier="RabbitMQ")
        self._maybe_instrument()
        try:
            self._robust_connection = await self._connection_factory(
                url=str(self._rabbitmq_credentials_config.amqp_url)
            )
        except Exception as exception:
            self._report_unhealthy()
            raise AiopikaPluginBaseError("Unable to connect to the AMQP server.") from exception
        self._bind_connection_callbacks()
        self._add_to_state(key=AIOPIKA_CONNECTION, value=self._robust_connection)
        self._report_healthy()
        _logger.debug(
            "Aiopika plugin connected to the AMQP server.", amqp_url=self._rabbitmq_credentials_config.amqp_url
        )

    async def on_shutdown(self) -> None:
        """On shutdown."""
        self._shutting_down = True
        self._disarm_unhealthy()
        if self._robust_connection is not None:
            await self._robust_connection.close()
        _logger.debug("Aiopika plugin shutdown.")
