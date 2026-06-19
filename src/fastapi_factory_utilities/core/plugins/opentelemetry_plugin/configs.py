"""Provides the configuration model for the OpenTelemetry plugin."""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, UrlConstraints
from pydantic_core import Url


class ProtocolEnum(StrEnum):
    """Defines the protocol enum for OpenTelemetry."""

    OTLP_GRPC = "otlp_grpc"
    OTLP_HTTP = "otlp_http"


class OpenTelemetryMeterConfig(BaseModel):
    """Provides the configuration model for the OpenTelemetry meter as sub-model."""

    # Constants for time in milliseconds and seconds
    ONE_MINUTE_IN_MILLIS: int = 60000
    ONE_SECOND_IN_MILLIS: int = 1000

    model_config = ConfigDict(frozen=True, extra="forbid")

    reader_interval_millis: float = Field(
        default=ONE_SECOND_IN_MILLIS,
        description="The interval in miliseconds to read and export metrics.",
    )

    reader_timeout_millis: float = Field(
        default=ONE_SECOND_IN_MILLIS,
        description="The timeout in miliseconds for the reader.",
    )


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
