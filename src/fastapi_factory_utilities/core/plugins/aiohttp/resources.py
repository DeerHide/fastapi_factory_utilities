"""Aiohttp client factory."""

import asyncio
import logging
import os
import ssl
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.util import find_spec
from typing import Any

import aiohttp
import certifi
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from structlog.stdlib import BoundLogger, get_logger

from fastapi_factory_utilities.core.plugins.aiohttp.configs import HttpServiceDependencyConfig
from fastapi_factory_utilities.core.plugins.aiohttp.exceptions import AioHttpClientError

_logger: BoundLogger = get_logger()


class AioHttpClientResource:
    """Aiohttp client resource.

    Objectives:
    - Provide a resource to acquire and release Aiohttp client sessions.
    - Build the TCP connector with the dependency configuration.
    - Instrument the client session with OpenTelemetry.
    - Provide a graceful shutdown of the client sessions and the TCP connector.
    """

    @classmethod
    def build_ssl_context(cls, dependency_config: HttpServiceDependencyConfig) -> ssl.SSLContext | bool:
        """Build the SSL context.

        Args:
            dependency_config (HttpServiceDependencyConfig): The dependency configuration.

        Returns:
            ssl.SSLContext | bool: The SSL context.
        """
        ssl_context: ssl.SSLContext | bool = False

        # If the SSL verification is disabled, return False to disable the SSL verification.
        if dependency_config.verify_ssl is False:
            return ssl_context

        # If the SSL CA path is provided, use it to create the SSL context.
        if dependency_config.ssl_ca_path is not None:
            if not os.path.exists(dependency_config.ssl_ca_path):
                raise AioHttpClientError(f"SSL CA path {dependency_config.ssl_ca_path} does not exist.")
            ssl_context = ssl.create_default_context(cafile=dependency_config.ssl_ca_path)
        else:
            # If no SSL CA path is provided, use the default SSL CA path from certifi.
            ssl_context = ssl.create_default_context(cafile=certifi.where())

        if dependency_config.ssl_certfile is None or dependency_config.ssl_keyfile is None:
            return ssl_context

        if not os.path.exists(dependency_config.ssl_certfile):
            raise AioHttpClientError(f"SSL certificate file {dependency_config.ssl_certfile} does not exist.")
        if not os.path.exists(dependency_config.ssl_keyfile):
            raise AioHttpClientError(f"SSL key file {dependency_config.ssl_keyfile} does not exist.")

        # Load the SSL certificate and key files into the SSL context.
        if dependency_config.ssl_keyfile_password is not None:
            ssl_context.load_cert_chain(
                dependency_config.ssl_certfile,
                dependency_config.ssl_keyfile,
                password=dependency_config.ssl_keyfile_password,
            )
        else:
            ssl_context.load_cert_chain(dependency_config.ssl_certfile, dependency_config.ssl_keyfile)

        return ssl_context

    @classmethod
    def build_tcp_connector(cls, dependency_config: HttpServiceDependencyConfig) -> aiohttp.TCPConnector:
        """Build the TCP connector.

        Args:
            dependency_config (HttpServiceDependencyConfig): The dependency configuration.

        Returns:
            aiohttp.TCPConnector: The TCP connector.
        """
        ssl_context: ssl.SSLContext | bool = cls.build_ssl_context(dependency_config=dependency_config)
        return aiohttp.TCPConnector(
            limit=dependency_config.limit,
            limit_per_host=dependency_config.limit_per_host,
            use_dns_cache=dependency_config.use_dns_cache,
            ttl_dns_cache=dependency_config.ttl_dns_cache,
            ssl=ssl_context,
        )

    @classmethod
    def build_trace_config(
        cls, tracer_provider: TracerProvider | None, meter_provider: MeterProvider | None
    ) -> aiohttp.TraceConfig | None:
        """Build the trace config.

        Args:
            tracer_provider: The tracer provider. If None, OpenTelemetry tracing is disabled.
            meter_provider: The meter provider. If None, OpenTelemetry metrics are disabled.

        Returns:
            aiohttp.TraceConfig: The trace config, or None if providers are not available.
        """
        if tracer_provider is None or meter_provider is None:
            return None
        if find_spec(name="opentelemetry.instrumentation.aiohttp_client"):
            from opentelemetry.instrumentation.aiohttp_client import (  # pylint: disable=import-outside-toplevel # noqa: PLC0415
                create_trace_config,
            )

            return create_trace_config(tracer_provider=tracer_provider, meter_provider=meter_provider)
        return None

    def __init__(self, dependency_config: HttpServiceDependencyConfig) -> None:
        """Initialize the Aiohttp client resource.

        Args:
            dependency_config (HttpServiceDependencyConfig): The dependency configuration.

        Returns:
            None
        """
        self._dependency_config: HttpServiceDependencyConfig = dependency_config
        self._tcp_connector: aiohttp.TCPConnector | None = None
        self._client_sessions: list[aiohttp.ClientSession] = []
        self._tracer_provider: TracerProvider | None = None
        self._meter_provider: MeterProvider | None = None
        self._must_be_closed: bool = False

    def on_load(self) -> None:
        """On load.

        This method is called when the resource is loaded.
        Currently, no initialization is required at load time.
        """

    async def on_startup(
        self, tracer_provider: TracerProvider | None = None, meter_provider: MeterProvider | None = None
    ) -> None:
        """On startup.

        Args:
            tracer_provider: The tracer provider. If None, OpenTelemetry tracing is disabled.
            meter_provider: The meter provider. If None, OpenTelemetry metrics are disabled.

        Returns:
            None
        """
        self._tracer_provider = tracer_provider
        self._meter_provider = meter_provider
        if self._tcp_connector is None:
            self._tcp_connector = self.build_tcp_connector(dependency_config=self._dependency_config)

    async def on_shutdown(self) -> None:
        """On shutdown.

        Args:
            None

        Returns:
            None
        """
        # Wait for all client sessions to be released.
        initial_time = time.time()
        self._must_be_closed = True
        # Wait for all client sessions to be released or the timeout is reached.
        while self._client_sessions and time.time() - initial_time < self._dependency_config.graceful_shutdown_timeout:
            await asyncio.sleep(0.5)
        # Close all client sessions remaining.
        for session in self._client_sessions:
            try:
                await session.close()
            except (OSError, aiohttp.ClientError) as exception:
                _logger.log(
                    level=logging.WARNING,
                    event="Failed to close client session during shutdown",
                    exception=str(exception),
                )
        # Close the TCP connector.
        if self._tcp_connector is not None:
            try:
                await self._tcp_connector.close()
            except (OSError, aiohttp.ClientError) as exception:
                _logger.log(
                    level=logging.WARNING,
                    event="Failed to close TCP connector during shutdown",
                    exception=str(exception),
                )

    @asynccontextmanager
    async def acquire_client_session(self, **kwargs: Any) -> AsyncGenerator[aiohttp.ClientSession, None]:
        """Acquire the Aiohttp client session.

        Args:
            **kwargs: Any additional keyword arguments to pass to the ClientSession constructor.

        Returns:
            AsyncGenerator[aiohttp.ClientSession, None]: The Aiohttp client session.

        Raises:
            RuntimeError: If the TCP connector is not initialized.
            ValueError: If the connector is already provided in kwargs.
        """
        if self._tcp_connector is None:
            raise AioHttpClientError("TCP connector is not initialized. Call on_startup() first.")
        if self._tcp_connector.closed and self._must_be_closed:
            raise AioHttpClientError("TCP connector is closed.")
        if self._tcp_connector.closed and not self._must_be_closed:
            _logger.warning(
                "TCP connector has been closed but the resource is not being shutdown. Rebuilding the TCP connector.",
            )
            self._tcp_connector = self.build_tcp_connector(dependency_config=self._dependency_config)
        if "connector" in kwargs:
            raise ValueError("The connector is already provided.")

        kwargs["connector"] = self._tcp_connector
        # Set the connector owner to False to avoid closing the connector when the session is closed.
        kwargs["connector_owner"] = False

        if self._dependency_config.url is not None:
            kwargs["base_url"] = str(self._dependency_config.url)

        trace_config: aiohttp.TraceConfig | None = self.build_trace_config(
            tracer_provider=self._tracer_provider, meter_provider=self._meter_provider
        )

        if trace_config is not None:
            kwargs["trace_configs"] = [trace_config]

        async with aiohttp.ClientSession(**kwargs) as session:
            self._client_sessions.append(session)
            try:
                yield session
            finally:
                self._client_sessions.remove(session)
