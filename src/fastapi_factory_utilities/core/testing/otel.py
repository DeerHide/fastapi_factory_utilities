"""OpenTelemetry test doubles via in-memory exporters."""

from dataclasses import dataclass

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


@dataclass(frozen=True, slots=True)
class InMemoryOtel:
    """Bundle of in-memory OTel providers and exporters for assertions."""

    tracer_provider: TracerProvider
    meter_provider: MeterProvider
    span_exporter: InMemorySpanExporter
    metric_reader: InMemoryMetricReader


def build_in_memory_otel() -> InMemoryOtel:
    """Build TracerProvider / MeterProvider backed by in-memory exporters.

    Returns:
        Providers plus exporters for span/metric assertions.
    """
    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))

    metric_reader = InMemoryMetricReader()
    meter_provider = MeterProvider(metric_readers=[metric_reader])
    return InMemoryOtel(
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        span_exporter=span_exporter,
        metric_reader=metric_reader,
    )
