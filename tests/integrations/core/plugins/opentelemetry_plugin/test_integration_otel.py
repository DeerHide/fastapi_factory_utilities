"""Provide tests for the OpenTelemetry plugin."""

from collections.abc import Generator
from time import sleep
from typing import TypedDict
from unittest.mock import MagicMock

import pytest
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import (
    SpanProcessor,
    SynchronousMultiSpanProcessor,
    TracerProvider,
)
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.trace import Tracer
from opentelemetry.trace.span import Span
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from fastapi_factory_utilities.core.app.config import BaseApplicationConfig, RootConfig
from fastapi_factory_utilities.core.app.enums import EnvironmentEnum
from fastapi_factory_utilities.core.plugins.opentelemetry_plugin.builder import (
    OpenTelemetryPluginBuilder,
)
from fastapi_factory_utilities.core.plugins.opentelemetry_plugin.configs import (
    OpenTelemetryConfig,
    ProtocolEnum,
)


class OtelCollectorDict(TypedDict):
    """Define the OpenTelemetry collector dictionary."""

    endpoint_protobuff: str  # 4318
    endpoint_grpc: str  # 4317


class TestIntegrationOpentelemetryPlugin:
    """Test the OpenTelemetry plugin."""

    @pytest.fixture
    def fixture_otel_collector(self, tmpdir: str) -> Generator[OtelCollectorDict, None, None]:
        """Provide the OpenTelemetry collector fixture."""
        config_path: str = tmpdir.join("/otel_config.yaml")
        with open(file=config_path, mode="w", encoding="utf-8") as config_file:
            config_file.write(
                """
                receivers:
                  otlp:
                    protocols:
                      grpc:
                        endpoint:
                            0.0.0.0:4317
                      http:
                        endpoint:
                            0.0.0.0:4318
                exporters:
                  debug:
                    verbosity: detailed
                service:
                  pipelines:
                    traces:
                        receivers: [otlp]
                        exporters: [debug]
                    metrics:
                        receivers: [otlp]
                        exporters: [debug]
                """
            )

        otel_container: DockerContainer = (
            DockerContainer(
                image="otel/opentelemetry-collector-contrib:latest",
            )
            .with_exposed_ports(4318, 4317)
            .with_volume_mapping(
                str(config_path),
                "/otel-local-config.yaml",
            )
            .with_command(
                "--config=/otel-local-config.yaml",
            )
            .waiting_for(LogMessageWaitStrategy("Everything is ready").with_startup_timeout(30))
        )

        with otel_container:
            sleep(1)
            yield OtelCollectorDict(
                endpoint_protobuff=f"http://{otel_container.get_container_host_ip()}"
                f":{otel_container.get_exposed_port(port=4318)}",
                endpoint_grpc=f"http://{otel_container.get_container_host_ip()}"
                f":{otel_container.get_exposed_port(port=4317)}",
            )

    @pytest.mark.parametrize(
        "protocol",
        [
            ProtocolEnum.OTLP_HTTP,
            ProtocolEnum.OTLP_GRPC,
        ],
        ids=[
            "OTLP_HTTP",
            "OTLP_GRPC",
        ],
    )
    def test_otel_protobuf_integration(self, fixture_otel_collector: OtelCollectorDict, protocol: ProtocolEnum) -> None:
        """Provide the integration test for the OpenTelemetry plugin."""
        application_mock: MagicMock = MagicMock()
        application_mock.get_config.return_value = RootConfig(
            application=BaseApplicationConfig(
                environment=EnvironmentEnum.DEVELOPMENT,
                service_name="test",
                service_namespace="test",
                description="test",
                version="0.0.0",
                audience="test",
            )
        )

        settings: OpenTelemetryConfig = OpenTelemetryConfig(
            activate=True,
            endpoint=fixture_otel_collector.get(
                "endpoint_grpc" if protocol == ProtocolEnum.OTLP_GRPC else "endpoint_protobuff"
            ),
            protocol=protocol,
            timeout=10,
            closing_timeout=10,
        )

        assert settings.activate is True

        builder: OpenTelemetryPluginBuilder = OpenTelemetryPluginBuilder(
            application=application_mock, settings=settings
        )
        builder.build_all()
        assert builder.tracer_provider is not None
        tracer: Tracer = builder.tracer_provider.get_tracer(__package__)  # type: ignore[reportOptionalMemberAccess]
        span: Span = tracer.start_span("test_span")
        span.end()

        assert builder.tracer_provider.force_flush()
        builder.tracer_provider.shutdown()

    def test_simple(self, fixture_otel_collector: OtelCollectorDict) -> None:
        """Test the OpenTelemetry plugin.

        Args:
            fixture_otel_collector (OtelCollectorDict): The OpenTelemetry collector fixture.
        """
        exporter: OTLPSpanExporter = OTLPSpanExporter(
            endpoint=fixture_otel_collector.get("endpoint_grpc"),
            insecure=True,
        )

        processor: SpanProcessor = SimpleSpanProcessor(span_exporter=exporter)
        multi_span_processor: SynchronousMultiSpanProcessor = SynchronousMultiSpanProcessor()
        multi_span_processor.add_span_processor(span_processor=processor)

        tracer_provider: TracerProvider = TracerProvider(
            resource=Resource(
                attributes={
                    "service.name": "test",
                    "service.namespace": "test",
                    "service.version": "0.0.0",
                }
            ),
            active_span_processor=multi_span_processor,
        )

        tracer: Tracer = tracer_provider.get_tracer(__package__)
        span: Span = tracer.start_span("test_span")
        span.end()
        tracer_provider.shutdown()
        assert exporter.force_flush()
        exporter.shutdown()

        print()
