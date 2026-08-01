"""Provides a factory function to build a objets for OpenTelemetry."""

from typing import Any, Self
from urllib.parse import ParseResult, urlparse

from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter as OTLPMetricExporterGRPC,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as OTLPSpanExporterGRPC,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter as OTLPMetricExporterHTTP,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as OTLPSpanExporterHTTP,
)
from opentelemetry.metrics import set_meter_provider
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import (
    DEPLOYMENT_ENVIRONMENT,
    SERVICE_NAME,
    SERVICE_NAMESPACE,
    SERVICE_VERSION,
    Resource,
)
from opentelemetry.sdk.trace import SynchronousMultiSpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import set_tracer_provider
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from fastapi_factory_utilities.core.plugins.opentelemetry_plugin.configs import (
    OpenTelemetryMeterConfig,
    OpenTelemetryTracerConfig,
)
from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol
from fastapi_factory_utilities.core.utils.importlib import get_path_file_in_package
from fastapi_factory_utilities.core.utils.yaml_reader import (
    UnableToReadYamlFileError,
    YamlFileReader,
)

from .configs import OpenTelemetryConfig, ProtocolEnum
from .exceptions import OpenTelemetryPluginConfigError

GRPC_PORT: int = 4317
HTTP_PORT: int = 4318


class OpenTelemetryPluginBuilder:
    """Configure the injection bindings for OpenTelemetryPlugin."""

    def __init__(self, application: ApplicationAbstractProtocol, settings: OpenTelemetryConfig | None = None) -> None:
        """Instantiate the OpenTelemetryPluginFactory.

        Args:
            application (BaseApplicationProtocol): The application object.
            settings (OpenTelemetryConfig | None): The OpenTelemetry configuration object.
        """
        self._application: ApplicationAbstractProtocol = application
        self._resource: Resource | None = None
        self._config: OpenTelemetryConfig | None = settings
        self._meter_provider: MeterProvider | None = None
        self._tracer_provider: TracerProvider | None = None
        self._trace_exporter: OTLPSpanExporterGRPC | OTLPSpanExporterHTTP | None = None
        self._metric_exporter: OTLPMetricExporterGRPC | OTLPMetricExporterHTTP | None = None

    @property
    def resource(self) -> Resource | None:
        """Provide the resource object for OpenTelemetry.

        Returns:
            Resource | None: The resource object for OpenTelemetry.
        """
        return self._resource

    @property
    def config(self) -> OpenTelemetryConfig | None:
        """Provide the configuration object for OpenTelemetry.

        Returns:
            OpenTelemetryConfig | None: The configuration object for OpenTelemetry.
        """
        return self._config

    @property
    def meter_provider(self) -> MeterProvider | None:
        """Provide the meter provider object for OpenTelemetry.

        Returns:
            MeterProvider | None: The meter provider object for OpenTelemetry.
        """
        return self._meter_provider

    @property
    def tracer_provider(self) -> TracerProvider | None:
        """Provide the tracer provider object for OpenTelemetry.

        Returns:
            TracerProvider | None: The tracer provider object for OpenTelemetry.
        """
        return self._tracer_provider

    def build_resource(self) -> Self:
        """Build a resource object for OpenTelemetry from the application and configs.

        Uses ``Resource.create`` so ``OTEL_RESOURCE_ATTRIBUTES`` (and other
        SDK resource detectors) merge with the application attributes. App
        keys win on conflict.

        Returns:
            Self: The OpenTelemetryPluginFactory object.
        """
        self._resource = Resource.create(
            attributes={
                DEPLOYMENT_ENVIRONMENT: self._application.get_config().application.environment.value,
                SERVICE_NAME: self._application.get_config().application.service_name,
                SERVICE_NAMESPACE: self._application.get_config().application.service_namespace,
                SERVICE_VERSION: self._application.get_config().application.version,
            }
        )
        return self

    def build_config(
        self,
    ) -> Self:
        """Build the configuration object for OpenTelemetry from the application.

        Returns:
            Self: The OpenTelemetryPluginFactory object.

        Raises:
            OpenTelemetryPluginConfigError: If the package name is not set in the application.
            OpenTelemetryPluginConfigError: If the application configuration file is not found.

        """
        if self._application.PACKAGE_NAME == "":
            raise OpenTelemetryPluginConfigError("The package name must be set in the concrete application class.")

        # Read the application configuration file
        try:
            yaml_file_content: dict[str, Any] = YamlFileReader(
                file_path=get_path_file_in_package(
                    filename="application.yaml",
                    package=self._application.PACKAGE_NAME,
                ),
                yaml_base_key="opentelemetry",
                use_environment_injection=True,
            ).read()
        except (FileNotFoundError, ImportError, UnableToReadYamlFileError) as exception:
            raise OpenTelemetryPluginConfigError("Unable to read the application configuration file.") from exception

        # Create the application configuration model
        try:
            self._config = OpenTelemetryConfig(**yaml_file_content)
        except ValueError as exception:
            raise OpenTelemetryPluginConfigError("Unable to create the application configuration model.") from exception

        return self

    def build_meter_provider(
        self,
    ) -> Self:
        """Build a meter provider object for OpenTelemetry.

        Returns:
            Self: The OpenTelemetryPluginFactory object.
        """
        if self._resource is None:
            raise OpenTelemetryPluginConfigError("The resource object is missing.")

        if self._config is None:
            raise OpenTelemetryPluginConfigError("The configuration object is missing.")

        readers: list[MetricReader] = []
        if self._config.activate is True:
            if self._config.meter_config is None:
                # TODO: switch to a custom exception
                raise OpenTelemetryPluginConfigError("The meter configuration is missing.")

            # TODO: Extract to a dedicated method for the exporter and period reader setup

            url_parsed: ParseResult = urlparse(self._config.endpoint.unicode_string())

            exporter: OTLPMetricExporterGRPC | OTLPMetricExporterHTTP
            # Setup the Exporter
            if url_parsed.port == GRPC_PORT or self._config.protocol == ProtocolEnum.OTLP_GRPC:
                exporter = OTLPMetricExporterGRPC(
                    endpoint=f"{self._config.endpoint.unicode_string()}",
                    timeout=self._config.timeout,
                    insecure=True if str(self._config.endpoint).startswith("http") else False,
                )
            elif url_parsed.port == HTTP_PORT or self._config.protocol == ProtocolEnum.OTLP_HTTP:
                exporter = OTLPMetricExporterHTTP(
                    endpoint=f"{self._config.endpoint.unicode_string()}/v1/metrics",
                    timeout=self._config.timeout,
                )
            else:
                raise OpenTelemetryPluginConfigError(
                    "The endpoint port is not supported. Use 4317 for gRPC or 4318 for HTTP or set the protocol."
                )

            self._metric_exporter = exporter

            # Setup the Metric Reader
            meter_config: OpenTelemetryMeterConfig = self._config.meter_config
            reader = PeriodicExportingMetricReader(
                exporter=exporter,
                export_interval_millis=meter_config.reader_interval_millis,
                export_timeout_millis=meter_config.reader_timeout_millis,
            )
            readers.append(reader)

        # Setup the Meter Provider
        self._meter_provider = MeterProvider(
            resource=self._resource,
            metric_readers=readers,
            shutdown_on_exit=True,
            views=[],
        )

        set_meter_provider(self._meter_provider)

        return self

    def build_tracer_provider(
        self,
    ) -> Self:
        """Provides a tracer provider for OpenTelemetry.

        Returns:
            Self: The OpenTelemetryPluginFactory object.

        Raises:
            OpenTelemetryPluginConfigError: If the resource object is missing.
            OpenTelemetryPluginConfigError: If the configuration object is missing.
        """
        if self._resource is None:
            raise OpenTelemetryPluginConfigError("The resource object is missing.")

        if self._config is None:
            raise OpenTelemetryPluginConfigError("The configuration object is missing.")

        active_span_processor: SynchronousMultiSpanProcessor | None = None

        # Exit with a void TracerProvider if the export is not activated
        if self._config.activate is True:
            if self._config.tracer_config is None:
                raise OpenTelemetryPluginConfigError("The tracer configuration is missing.")

            exporter: OTLPSpanExporterGRPC | OTLPSpanExporterHTTP
            url_parsed: ParseResult = urlparse(self._config.endpoint.unicode_string())
            # Setup the Exporter
            if url_parsed.port == GRPC_PORT or self._config.protocol == ProtocolEnum.OTLP_GRPC:
                insecure: bool = False if str(self._config.endpoint).startswith("https") else True
                endpoint: str = f"{self._config.endpoint.unicode_string()}"
                exporter = OTLPSpanExporterGRPC(
                    endpoint=endpoint,
                    # timeout=self._config.timeout,
                    insecure=insecure,
                )
            elif url_parsed.port == HTTP_PORT or self._config.protocol == ProtocolEnum.OTLP_HTTP:
                exporter = OTLPSpanExporterHTTP(
                    endpoint=f"{self._config.endpoint.unicode_string()}/v1/traces",
                    # timeout=self._config.timeout,
                )
            else:
                raise OpenTelemetryPluginConfigError(
                    "The endpoint port is not supported. Use 4317 for gRPC or 4318 for HTTP or set the protocol."
                )

            self._trace_exporter = exporter

            # Setup the Span Processor
            tracer_config: OpenTelemetryTracerConfig = self._config.tracer_config
            span_processor = BatchSpanProcessor(
                span_exporter=exporter,
                max_queue_size=tracer_config.max_queue_size,
                max_export_batch_size=tracer_config.max_export_batch_size,
                schedule_delay_millis=tracer_config.schedule_delay_millis,
                export_timeout_millis=tracer_config.export_timeout_millis,
            )

            # Setup the Multi Span Processor
            active_span_processor = SynchronousMultiSpanProcessor()
            active_span_processor.add_span_processor(span_processor=span_processor)

            # W3C tracecontext + baggage first; B3 kept for existing peers.
            set_global_textmap(
                http_text_format=CompositePropagator(
                    [
                        TraceContextTextMapPropagator(),
                        W3CBaggagePropagator(),
                        B3MultiFormat(),
                    ]
                )
            )

        # Setup the Tracer Provider
        self._tracer_provider = TracerProvider(
            sampler=None,
            resource=self._resource,
            active_span_processor=active_span_processor,
            id_generator=None,
            span_limits=None,
            shutdown_on_exit=True,
        )

        set_tracer_provider(self._tracer_provider)

        return self

    def build_all(
        self,
    ) -> Self:
        """Build all the objects for OpenTelemetry.

        Returns:
            Self: The OpenTelemetryPluginFactory object.
        """
        self.build_resource()
        if self._config is None:
            self.build_config()
        self.build_meter_provider()
        self.build_tracer_provider()

        return self
