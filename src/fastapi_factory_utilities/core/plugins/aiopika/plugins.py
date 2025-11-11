"""Provides the Aiopika plugin."""

from typing import cast

from aio_pika import connect_robust  # pyright: ignore[reportUnknownMemberType]
from aio_pika.abc import AbstractRobustConnection
from fastapi import Request
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor  # pyright: ignore[reportMissingTypeStubs]
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from structlog.stdlib import BoundLogger, get_logger

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.utils.rabbitmq_configs import (
    RabbitMQCredentialsConfig,
    RabbitMQCredentialsConfigError,
    build_rabbitmq_credentials_config,
)

from .depends import DEPENDS_AIOPIKA_ROBUST_CONNECTION_KEY
from .exceptions import AiopikaPluginBaseError

_logger: BoundLogger = get_logger(__package__)


class AiopikaPlugin(PluginAbstract):
    """Aiopika plugin."""

    def __init__(self, rabbitmq_credentials_config: RabbitMQCredentialsConfig | None = None) -> None:
        """Initialize the Aiopika plugin."""
        super().__init__()
        self._rabbitmq_credentials_config: RabbitMQCredentialsConfig | None = rabbitmq_credentials_config
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
            try:
                self._rabbitmq_credentials_config = build_rabbitmq_credentials_config(
                    package_name=self._application.PACKAGE_NAME
                )
            except RabbitMQCredentialsConfigError as exception:
                raise AiopikaPluginBaseError("Unable to build the RabbitMQ credentials configuration.") from exception

    async def on_startup(self) -> None:
        """On startup."""
        assert self._application is not None
        assert self._rabbitmq_credentials_config is not None

        tracer_provider: TracerProvider | None = cast(
            TracerProvider | None, getattr(self._application.get_asgi_app().state, "tracer_provider", None)
        )
        meter_provider: MeterProvider | None = cast(
            MeterProvider | None, getattr(self._application.get_asgi_app().state, "meter_provider", None)
        )
        if tracer_provider is None or meter_provider is None:
            raise AiopikaPluginBaseError("Tracer provider or meter provider not found in the application state.")

        AioPikaInstrumentor().instrument(
            tracer_provider=tracer_provider,
            meter_provider=meter_provider,
        )

        self._robust_connection = await connect_robust(url=str(self._rabbitmq_credentials_config.amqp_url))
        self._add_to_state(key=DEPENDS_AIOPIKA_ROBUST_CONNECTION_KEY, value=self._robust_connection)
        _logger.debug(
            "Aiopika plugin connected to the AMQP server.", amqp_url=self._rabbitmq_credentials_config.amqp_url
        )

    async def on_shutdown(self) -> None:
        """On shutdown."""
        if self._robust_connection is not None:
            await self._robust_connection.close()
        _logger.debug("Aiopika plugin shutdown.")


def depends_robust_connection(request: Request) -> AbstractRobustConnection:
    """Depends on the robust connection.

    Args:
        request (Request): The request.

    Returns:
        AbstractRobustConnection: The robust connection.
    """
    return request.app.state.robust_connection
