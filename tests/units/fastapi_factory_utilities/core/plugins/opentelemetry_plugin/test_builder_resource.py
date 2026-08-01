"""Unit tests for OpenTelemetryPluginBuilder resource and propagator setup."""

# pylint: disable=protected-access

from unittest.mock import MagicMock, patch

import pytest
from opentelemetry.propagate import get_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME

from fastapi_factory_utilities.core.app.enums import EnvironmentEnum
from fastapi_factory_utilities.core.plugins.opentelemetry_plugin.builder import OpenTelemetryPluginBuilder
from fastapi_factory_utilities.core.plugins.opentelemetry_plugin.configs import (
    OpenTelemetryConfig,
    OpenTelemetryTracerConfig,
)


class TestBuildResource:
    """Tests for ``OpenTelemetryPluginBuilder.build_resource``."""

    def test_merges_otel_resource_attributes_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``OTEL_RESOURCE_ATTRIBUTES`` must merge into the app resource."""
        monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", "environment=stg")

        application: MagicMock = MagicMock()
        application.get_config.return_value.application.environment = EnvironmentEnum.STAGING
        application.get_config.return_value.application.service_name = "customers"
        application.get_config.return_value.application.service_namespace = "customer"
        application.get_config.return_value.application.version = "1.2.3"

        builder: OpenTelemetryPluginBuilder = OpenTelemetryPluginBuilder(application=application)
        builder.build_resource()

        assert builder.resource is not None
        attributes: dict[str, object] = dict(builder.resource.attributes)
        assert attributes[SERVICE_NAME] == "customers"
        assert attributes[DEPLOYMENT_ENVIRONMENT] == "staging"
        assert attributes["environment"] == "stg"


class TestBuildTracerPropagator:
    """Tests for global textmap propagator registration."""

    def test_sets_composite_w3c_and_b3_propagator(self) -> None:
        """Active export must register TraceContext + Baggage + B3."""
        application: MagicMock = MagicMock()
        application.get_config.return_value.application.environment = EnvironmentEnum.STAGING
        application.get_config.return_value.application.service_name = "customers"
        application.get_config.return_value.application.service_namespace = "customer"
        application.get_config.return_value.application.version = "1.2.3"

        config: OpenTelemetryConfig = OpenTelemetryConfig(
            activate=True,
            endpoint="http://localhost:4317",
            tracer_config=OpenTelemetryTracerConfig(),
        )
        builder: OpenTelemetryPluginBuilder = OpenTelemetryPluginBuilder(
            application=application,
            settings=config,
        )
        builder.build_resource()

        with patch(
            "fastapi_factory_utilities.core.plugins.opentelemetry_plugin.builder.OTLPSpanExporterGRPC",
        ):
            builder.build_tracer_provider()

        textmap = get_global_textmap()
        assert isinstance(textmap, CompositePropagator)
