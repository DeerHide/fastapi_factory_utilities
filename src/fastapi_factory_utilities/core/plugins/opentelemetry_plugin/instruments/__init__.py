"""Instruments for the OpenTelemetry plugin."""

# pyright: reportMissingTypeStubs=false

from collections.abc import Callable
from importlib.util import find_spec
from typing import Any

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from structlog.stdlib import BoundLogger, get_logger

from fastapi_factory_utilities.core.plugins.opentelemetry_plugin.configs import (
    InstrumentationName,
    OpenTelemetryConfig,
)
from fastapi_factory_utilities.core.plugins.opentelemetry_plugin.pymongo_hooks import build_pymongo_request_hook
from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol

_logger: BoundLogger = get_logger()


def _available(name: str, *modules: str) -> bool:
    """Return True when every module is importable; otherwise log a skip and return False."""
    if all(find_spec(module) for module in modules):
        return True
    _logger.info("Skipping %s instrumentation: target library not installed", name)
    return False


def instrument_fastapi(
    application: ApplicationAbstractProtocol,
    config: OpenTelemetryConfig,
    meter_provider: MeterProvider,
    tracer_provider: TracerProvider,
) -> None:
    """Instrument the FastAPI application."""
    if _available("fastapi", "fastapi", "opentelemetry.instrumentation.fastapi"):
        from opentelemetry.instrumentation.fastapi import (  # pylint: disable=import-outside-toplevel # noqa: PLC0415
            FastAPIInstrumentor,
        )

        excluded_urls_str: str | None = None if len(config.excluded_urls) == 0 else ",".join(config.excluded_urls)
        FastAPIInstrumentor.instrument_app(  # pyright: ignore[reportUnknownMemberType]
            app=application.get_asgi_app(),
            tracer_provider=tracer_provider,
            meter_provider=meter_provider,
            excluded_urls=excluded_urls_str,
        )


def instrument_aiohttp(
    application: ApplicationAbstractProtocol,  # pylint: disable=unused-argument
    config: OpenTelemetryConfig,  # pylint: disable=unused-argument
    meter_provider: MeterProvider,
    tracer_provider: TracerProvider,
) -> None:
    """Instrument the Aiohttp application.

    Args:
        application (ApplicationAbstractProtocol): The application.
        config (OpenTelemetryConfig): The configuration.
        meter_provider (MeterProvider): The meter provider.
        tracer_provider (TracerProvider): The tracer provider.

    Returns:
        None
    """
    if _available("aiohttp", "aiohttp", "opentelemetry.instrumentation.aiohttp_client"):
        from opentelemetry.instrumentation.aiohttp_client import (  # pylint: disable=import-outside-toplevel # noqa: PLC0415
            AioHttpClientInstrumentor,
        )

        AioHttpClientInstrumentor().instrument(  # pyright: ignore[reportUnknownMemberType]
            tracer_provider=tracer_provider,
            meter_provider=meter_provider,
        )


def instrument_aio_pika(
    application: ApplicationAbstractProtocol,  # pylint: disable=unused-argument
    config: OpenTelemetryConfig,  # pylint: disable=unused-argument
    meter_provider: MeterProvider,
    tracer_provider: TracerProvider,
) -> None:
    """Instrument the AioPika application."""
    if _available("aio_pika", "aio_pika", "opentelemetry.instrumentation.aio_pika"):
        from opentelemetry.instrumentation.aio_pika import (  # pylint: disable=import-outside-toplevel # noqa: PLC0415
            AioPikaInstrumentor,
        )

        AioPikaInstrumentor().instrument(  # pyright: ignore[reportUnknownMemberType]
            tracer_provider=tracer_provider,
            meter_provider=meter_provider,
        )


def instrument_pymongo(
    application: ApplicationAbstractProtocol,  # pylint: disable=unused-argument
    config: OpenTelemetryConfig,  # pylint: disable=unused-argument
    meter_provider: MeterProvider,  # pylint: disable=unused-argument
    tracer_provider: TracerProvider,
) -> None:
    """Instrument the PyMongo client (covers Beanie via the async pymongo driver).

    PyMongo's ``monitoring`` listener is global, so registering the instrumentor
    once will produce CLIENT spans for both synchronous and asynchronous
    (Beanie 2.x ``AsyncMongoClient``) operations. ``capture_statement`` is kept
    disabled to avoid persisting raw query payloads in span attributes.

    Args:
        application (ApplicationAbstractProtocol): The application.
        config (OpenTelemetryConfig): The configuration.
        meter_provider (MeterProvider): The meter provider (unused; the
            PyMongo instrumentor only emits spans).
        tracer_provider (TracerProvider): The tracer provider.

    Returns:
        None
    """
    if _available("pymongo", "pymongo", "opentelemetry.instrumentation.pymongo"):
        from opentelemetry.instrumentation.pymongo import (  # pylint: disable=import-outside-toplevel # noqa: PLC0415
            PymongoInstrumentor,
        )

        instrument_kwargs: dict[str, Any] = {
            "tracer_provider": tracer_provider,
            "capture_statement": False,
        }
        if config.pymongo_capture_statement:
            instrument_kwargs["request_hook"] = build_pymongo_request_hook()

        PymongoInstrumentor().instrument(  # pyright: ignore[reportUnknownMemberType]
            **instrument_kwargs,
        )


def instrument_requests(
    application: ApplicationAbstractProtocol,  # pylint: disable=unused-argument
    config: OpenTelemetryConfig,  # pylint: disable=unused-argument
    meter_provider: MeterProvider,
    tracer_provider: TracerProvider,
) -> None:
    """Instrument the ``requests`` library (used by ``google.auth.transport.requests``).

    Args:
        application (ApplicationAbstractProtocol): The application.
        config (OpenTelemetryConfig): The configuration.
        meter_provider (MeterProvider): The meter provider.
        tracer_provider (TracerProvider): The tracer provider.

    Returns:
        None
    """
    if _available("requests", "requests", "opentelemetry.instrumentation.requests"):
        from opentelemetry.instrumentation.requests import (  # pylint: disable=import-outside-toplevel # noqa: PLC0415
            RequestsInstrumentor,
        )

        RequestsInstrumentor().instrument(  # pyright: ignore[reportUnknownMemberType]
            tracer_provider=tracer_provider,
            meter_provider=meter_provider,
        )


def instrument_urllib3(
    application: ApplicationAbstractProtocol,  # pylint: disable=unused-argument
    config: OpenTelemetryConfig,  # pylint: disable=unused-argument
    meter_provider: MeterProvider,
    tracer_provider: TracerProvider,
) -> None:
    """Instrument urllib3 (transport for ``requests`` and many SDK clients).

    Args:
        application (ApplicationAbstractProtocol): The application.
        config (OpenTelemetryConfig): The configuration.
        meter_provider (MeterProvider): The meter provider.
        tracer_provider (TracerProvider): The tracer provider.

    Returns:
        None
    """
    if _available("urllib3", "urllib3", "opentelemetry.instrumentation.urllib3"):
        from opentelemetry.instrumentation.urllib3 import (  # pylint: disable=import-outside-toplevel # noqa: PLC0415
            URLLib3Instrumentor,
        )

        URLLib3Instrumentor().instrument(  # pyright: ignore[reportUnknownMemberType]
            tracer_provider=tracer_provider,
            meter_provider=meter_provider,
        )


def instrument_asyncio(
    application: ApplicationAbstractProtocol,  # pylint: disable=unused-argument
    config: OpenTelemetryConfig,  # pylint: disable=unused-argument
    meter_provider: MeterProvider,  # pylint: disable=unused-argument
    tracer_provider: TracerProvider,
) -> None:
    """Instrument asyncio task scheduling.

    Args:
        application (ApplicationAbstractProtocol): The application.
        config (OpenTelemetryConfig): The configuration.
        meter_provider (MeterProvider): The meter provider (unused; the
            asyncio instrumentor only emits spans).
        tracer_provider (TracerProvider): The tracer provider.

    Returns:
        None
    """
    if _available("asyncio", "opentelemetry.instrumentation.asyncio"):
        from opentelemetry.instrumentation.asyncio import (  # pylint: disable=import-outside-toplevel # noqa: PLC0415
            AsyncioInstrumentor,
        )

        AsyncioInstrumentor().instrument(  # pyright: ignore[reportUnknownMemberType]
            tracer_provider=tracer_provider,
        )


def instrument_system_metrics(
    application: ApplicationAbstractProtocol,  # pylint: disable=unused-argument
    config: OpenTelemetryConfig,  # pylint: disable=unused-argument
    meter_provider: MeterProvider,
    tracer_provider: TracerProvider,  # pylint: disable=unused-argument
) -> None:
    """Instrument process and runtime system metrics (CPU, memory, GC, ...).

    Args:
        application (ApplicationAbstractProtocol): The application.
        config (OpenTelemetryConfig): The configuration.
        meter_provider (MeterProvider): The meter provider.
        tracer_provider (TracerProvider): The tracer provider (unused; the
            system metrics instrumentor only emits metrics).

    Returns:
        None
    """
    if _available("system_metrics", "psutil", "opentelemetry.instrumentation.system_metrics"):
        from opentelemetry.instrumentation.system_metrics import (  # pylint: disable=import-outside-toplevel # noqa: PLC0415
            SystemMetricsInstrumentor,
        )

        SystemMetricsInstrumentor().instrument(  # pyright: ignore[reportUnknownMemberType]
            meter_provider=meter_provider,
        )


def instrument_httpx(
    application: ApplicationAbstractProtocol,  # pylint: disable=unused-argument
    config: OpenTelemetryConfig,  # pylint: disable=unused-argument
    meter_provider: MeterProvider,
    tracer_provider: TracerProvider,
) -> None:
    """Instrument the ``httpx`` HTTP client.

    Args:
        application (ApplicationAbstractProtocol): The application.
        config (OpenTelemetryConfig): The configuration.
        meter_provider (MeterProvider): The meter provider.
        tracer_provider (TracerProvider): The tracer provider.

    Returns:
        None
    """
    if _available("httpx", "httpx", "opentelemetry.instrumentation.httpx"):
        from opentelemetry.instrumentation.httpx import (  # pylint: disable=import-outside-toplevel # noqa: PLC0415
            HTTPXClientInstrumentor,
        )

        HTTPXClientInstrumentor().instrument(  # pyright: ignore[reportUnknownMemberType]
            tracer_provider=tracer_provider,
            meter_provider=meter_provider,
        )


def instrument_redis(
    application: ApplicationAbstractProtocol,  # pylint: disable=unused-argument
    config: OpenTelemetryConfig,  # pylint: disable=unused-argument
    meter_provider: MeterProvider,  # pylint: disable=unused-argument
    tracer_provider: TracerProvider,
) -> None:
    """Instrument the ``redis`` client (Valkey / Taskiq-redis).

    Args:
        application (ApplicationAbstractProtocol): The application.
        config (OpenTelemetryConfig): The configuration.
        meter_provider (MeterProvider): The meter provider (unused; the
            redis instrumentor only emits spans).
        tracer_provider (TracerProvider): The tracer provider.

    Returns:
        None
    """
    if _available("redis", "redis", "opentelemetry.instrumentation.redis"):
        from opentelemetry.instrumentation.redis import (  # pylint: disable=import-outside-toplevel # noqa: PLC0415
            RedisInstrumentor,
        )

        RedisInstrumentor().instrument(  # pyright: ignore[reportUnknownMemberType]
            tracer_provider=tracer_provider,
        )


def instrument_aiobotocore(
    application: ApplicationAbstractProtocol,  # pylint: disable=unused-argument
    config: OpenTelemetryConfig,  # pylint: disable=unused-argument
    meter_provider: MeterProvider,  # pylint: disable=unused-argument
    tracer_provider: TracerProvider,
) -> None:
    """Instrument ``aiobotocore`` (async S3 / MinIO via the S3 plugin).

    Args:
        application (ApplicationAbstractProtocol): The application.
        config (OpenTelemetryConfig): The configuration.
        meter_provider (MeterProvider): The meter provider (unused; spans only).
        tracer_provider (TracerProvider): The tracer provider.

    Returns:
        None
    """
    if _available("aiobotocore", "aiobotocore", "opentelemetry.instrumentation.botocore"):
        from opentelemetry.instrumentation.botocore import (  # pylint: disable=import-outside-toplevel # noqa: PLC0415
            AiobotocoreInstrumentor,
        )

        AiobotocoreInstrumentor().instrument(  # pyright: ignore[reportUnknownMemberType]
            tracer_provider=tracer_provider,
        )


INSTRUMENTS: dict[InstrumentationName, Callable[..., Any]] = {
    InstrumentationName.FASTAPI: instrument_fastapi,
    InstrumentationName.AIOHTTP: instrument_aiohttp,
    InstrumentationName.AIO_PIKA: instrument_aio_pika,
    InstrumentationName.PYMONGO: instrument_pymongo,
    InstrumentationName.REQUESTS: instrument_requests,
    InstrumentationName.URLLIB3: instrument_urllib3,
    InstrumentationName.ASYNCIO: instrument_asyncio,
    InstrumentationName.SYSTEM_METRICS: instrument_system_metrics,
    InstrumentationName.HTTPX: instrument_httpx,
    InstrumentationName.REDIS: instrument_redis,
    InstrumentationName.AIOBOTOCORE: instrument_aiobotocore,
}


def apply_instruments(
    application: ApplicationAbstractProtocol,
    config: OpenTelemetryConfig,
    meter_provider: MeterProvider,
    tracer_provider: TracerProvider,
) -> None:
    """Import and apply only the instrumentations listed in ``config.instrumentations``."""
    for name in config.instrumentations:
        INSTRUMENTS[name](application, config, meter_provider, tracer_provider)


__all__: list[str] = ["INSTRUMENTS", "apply_instruments"]
