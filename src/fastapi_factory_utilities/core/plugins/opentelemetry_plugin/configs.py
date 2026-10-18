"""Provides the configuration model for the OpenTelemetry plugin."""

from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, UrlConstraints, model_validator
from pydantic_core import Url


class ProtocolEnum(StrEnum):
    """Defines the protocol enum for OpenTelemetry."""

    OTLP_GRPC = "otlp_grpc"
    OTLP_HTTP = "otlp_http"


class InstrumentationName(StrEnum):
    """OpenTelemetry instrumentations that can be enabled by configuration."""

    FASTAPI = "fastapi"
    AIOHTTP = "aiohttp"
    AIO_PIKA = "aio_pika"
    PYMONGO = "pymongo"
    REQUESTS = "requests"
    URLLIB3 = "urllib3"
    ASYNCIO = "asyncio"
    SYSTEM_METRICS = "system_metrics"
    HTTPX = "httpx"
    REDIS = "redis"
    AIOBOTOCORE = "aiobotocore"


# Heavy / high-cardinality runtime instrumentors — opt-in via
# ``OpenTelemetryConfig.enable_runtime_instrumentation``.
# Order is deterministic (enum declaration order). There is no separate CPython
# instrumentor: ``system_metrics`` covers process + CPython runtime (GC, …).
RUNTIME_INSTRUMENTATIONS: tuple[InstrumentationName, ...] = (
    InstrumentationName.ASYNCIO,
    InstrumentationName.SYSTEM_METRICS,
)


def _default_instrumentations() -> list[InstrumentationName]:
    """Return default instrumentations (HTTP/clients/etc.; runtime ones excluded)."""
    runtime = frozenset(RUNTIME_INSTRUMENTATIONS)
    return [name for name in InstrumentationName if name not in runtime]


class OpenTelemetryMeterConfig(BaseModel):
    """Provides the configuration model for the OpenTelemetry meter as sub-model."""

    # Constants for time in milliseconds and seconds
    ONE_MINUTE_IN_MILLIS: int = 60000
    TEN_SECONDS_IN_MILLIS: int = 10000
    ONE_SECOND_IN_MILLIS: int = 1000

    model_config = ConfigDict(frozen=True, extra="forbid")

    reader_interval_millis: float = Field(
        default=ONE_MINUTE_IN_MILLIS,
        description="The interval in miliseconds to read and export metrics.",
    )

    reader_timeout_millis: float = Field(
        default=TEN_SECONDS_IN_MILLIS,
        description="The timeout in miliseconds for the reader.",
    )

    @model_validator(mode="after")
    def validate_timeout_not_greater_than_interval(self) -> Self:
        """Ensure the export timeout does not exceed the export interval.

        Returns:
            The validated meter configuration.

        Raises:
            ValueError: If ``reader_timeout_millis`` is greater than
                ``reader_interval_millis``.
        """
        if self.reader_timeout_millis > self.reader_interval_millis:
            raise ValueError(
                "reader_timeout_millis must be less than or equal to reader_interval_millis "
                f"(got timeout={self.reader_timeout_millis}, interval={self.reader_interval_millis})"
            )
        return self


class OpenTelemetryTracerConfig(BaseModel):
    """Provides the configuration model for the OpenTelemetry tracer as sub-model."""

    # Constants for time in milliseconds and seconds
    FIVE_SECONDS_IN_MILLIS: int = 5000
    THIRTY_SECONDS_IN_MILLIS: int = 30000

    # Default values for the OpenTelemetry tracer
    DEFAULT_OTEL_TRACER_MAX_QUEUE_SIZE: int = 2048
    DEFAULT_OTEL_TRACER_MAX_EXPORT_BATCH_SIZE: int = 512

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_queue_size: int = Field(
        default=DEFAULT_OTEL_TRACER_MAX_QUEUE_SIZE,
        description="The maximum queue size for the tracer.",
    )
    max_export_batch_size: int = Field(
        default=DEFAULT_OTEL_TRACER_MAX_EXPORT_BATCH_SIZE,
        description="The maximum export batch size for the tracer.",
    )
    schedule_delay_millis: int = Field(
        default=FIVE_SECONDS_IN_MILLIS,
        description="The schedule delay in miliseconds for the tracer.",
    )
    export_timeout_millis: int = Field(
        default=THIRTY_SECONDS_IN_MILLIS,
        description="The export timeout in miliseconds for the tracer.",
    )


class OpenTelemetryConfig(BaseModel):
    """Provides the configuration model for the OpenTelemetry plugin."""

    # Constants for time in milliseconds and seconds
    TEN_SECONDS_IN_SECONDS: int = 10

    # Default value for the collector endpoint
    DEFAULT_COLLECTOR_ENDPOINT: str = "http://localhost:4318"

    model_config = ConfigDict(frozen=True, extra="forbid")

    activate: bool = Field(
        default=False,
        description="Whether to activate the OpenTelemetry collector export.",
    )
    endpoint: Annotated[Url, UrlConstraints(allowed_schemes=["http", "https"])] = Field(
        default=Url(url=DEFAULT_COLLECTOR_ENDPOINT),
        description="The collector endpoint.",
    )

    protocol: ProtocolEnum | None = Field(
        default=None,
        description="The protocol to use for the collector.",
    )

    timeout: int = Field(
        default=TEN_SECONDS_IN_SECONDS,
        description="The timeout in seconds for the collector.",
    )

    closing_timeout: int = Field(
        default=TEN_SECONDS_IN_SECONDS,
        description="The closing timeout in seconds for the collector.",
    )

    meter_config: OpenTelemetryMeterConfig | None = Field(
        default_factory=OpenTelemetryMeterConfig,
        description="The meter configuration.",
    )

    tracer_config: OpenTelemetryTracerConfig | None = Field(
        default_factory=OpenTelemetryTracerConfig,
        description="The tracer configuration.",
    )

    excluded_urls: list[str] = Field(
        default_factory=list,
        description="The excluded URLs for both the metrics and traces.",
    )

    pymongo_capture_statement: bool = Field(
        default=False,
        description=(
            "When enabled, attach a sanitized MongoDB command summary to PyMongo CLIENT spans "
            "via a request hook. Large ``$in`` arrays are truncated to keep span payloads bounded."
        ),
    )

    enable_runtime_instrumentation: bool = Field(
        default=False,
        description=(
            "Opt-in to system metrics, asyncio, and CPython runtime auto-instrumentation. "
            "Disabled by default to avoid high-frequency / high-cardinality metric export. "
            "HTTP and other library instrumentors are unchanged and controlled by "
            "``instrumentations``."
        ),
    )

    instrumentations: list[InstrumentationName] = Field(
        default_factory=_default_instrumentations,
        description=(
            "Instrumentations to load. Absent target libraries are skipped with a log line. "
            "Defaults exclude ``asyncio`` and ``system_metrics``; set "
            "``enable_runtime_instrumentation`` to opt in to those."
        ),
    )
