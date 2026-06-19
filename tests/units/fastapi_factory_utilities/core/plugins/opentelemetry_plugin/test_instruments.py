"""Tests for the OpenTelemetry plugin auto-instrumentation registry."""

# pylint: disable=protected-access

from unittest.mock import MagicMock, patch

import pytest

from fastapi_factory_utilities.core.plugins.opentelemetry_plugin.configs import OpenTelemetryConfig
from fastapi_factory_utilities.core.plugins.opentelemetry_plugin.instruments import (
    INSTRUMENTS,
    instrument_aio_pika,
    instrument_aiohttp,
    instrument_asyncio,
    instrument_fastapi,
    instrument_pymongo,
    instrument_requests,
    instrument_system_metrics,
    instrument_urllib3,
)


class TestInstrumentsRegistry:
    """Tests for the global ``INSTRUMENTS`` registry."""

    def test_all_expected_instrumentors_are_registered(self) -> None:
        """Ensure every shipped instrumentor is in the registry in the documented order."""
        assert INSTRUMENTS == [
            instrument_fastapi,
            instrument_aiohttp,
            instrument_aio_pika,
            instrument_pymongo,
            instrument_requests,
            instrument_urllib3,
            instrument_asyncio,
            instrument_system_metrics,
        ]


class _BaseInstrumentTest:
    """Common helpers for instrumentor unit tests."""

    @pytest.fixture
    def application(self) -> MagicMock:
        """Provide a mocked application protocol."""
        return MagicMock()

    @pytest.fixture
    def config(self) -> OpenTelemetryConfig:
        """Provide a default OpenTelemetry configuration."""
        return OpenTelemetryConfig()

    @pytest.fixture
    def tracer_provider(self) -> MagicMock:
        """Provide a mocked tracer provider."""
        return MagicMock(name="tracer_provider")

    @pytest.fixture
    def meter_provider(self) -> MagicMock:
        """Provide a mocked meter provider."""
        return MagicMock(name="meter_provider")


class TestInstrumentPymongo(_BaseInstrumentTest):
    """Tests for ``instrument_pymongo``."""

    def test_calls_pymongo_instrumentor_when_packages_available(
        self,
        application: MagicMock,
        config: OpenTelemetryConfig,
        tracer_provider: MagicMock,
        meter_provider: MagicMock,
    ) -> None:
        """Verify the PyMongo instrumentor is invoked with ``capture_statement=False``."""
        with (
            patch(
                "fastapi_factory_utilities.core.plugins.opentelemetry_plugin.instruments.find_spec",
                return_value=MagicMock(),
            ),
            patch("opentelemetry.instrumentation.pymongo.PymongoInstrumentor") as instrumentor_cls,
        ):
            instrument_pymongo(
                application=application,
                config=config,
                meter_provider=meter_provider,
                tracer_provider=tracer_provider,
            )
            instrumentor_cls.return_value.instrument.assert_called_once_with(
                tracer_provider=tracer_provider,
                capture_statement=False,
            )

    def test_registers_request_hook_when_capture_statement_enabled(
        self,
        application: MagicMock,
        tracer_provider: MagicMock,
        meter_provider: MagicMock,
    ) -> None:
        """Sanitized MongoDB command summaries must be opt-in via config."""
        config: OpenTelemetryConfig = OpenTelemetryConfig(pymongo_capture_statement=True)
        request_hook = MagicMock(name="request_hook")

        with (
            patch(
                "fastapi_factory_utilities.core.plugins.opentelemetry_plugin.instruments.find_spec",
                return_value=MagicMock(),
            ),
            patch("opentelemetry.instrumentation.pymongo.PymongoInstrumentor") as instrumentor_cls,
            patch(
                "fastapi_factory_utilities.core.plugins.opentelemetry_plugin.instruments.build_pymongo_request_hook",
                return_value=request_hook,
            ),
        ):
            instrument_pymongo(
                application=application,
                config=config,
                meter_provider=meter_provider,
                tracer_provider=tracer_provider,
            )
            instrumentor_cls.return_value.instrument.assert_called_once_with(
                tracer_provider=tracer_provider,
                capture_statement=False,
                request_hook=request_hook,
            )

    def test_noop_when_packages_missing(
        self,
        application: MagicMock,
        config: OpenTelemetryConfig,
        tracer_provider: MagicMock,
        meter_provider: MagicMock,
    ) -> None:
        """Verify instrumentation is skipped if pymongo or its instrumentor is missing."""
        with (
            patch(
                "fastapi_factory_utilities.core.plugins.opentelemetry_plugin.instruments.find_spec",
                return_value=None,
            ),
            patch("opentelemetry.instrumentation.pymongo.PymongoInstrumentor") as instrumentor_cls,
        ):
            instrument_pymongo(
                application=application,
                config=config,
                meter_provider=meter_provider,
                tracer_provider=tracer_provider,
            )
            instrumentor_cls.assert_not_called()


class TestInstrumentRequests(_BaseInstrumentTest):
    """Tests for ``instrument_requests``."""

    def test_calls_requests_instrumentor_when_packages_available(
        self,
        application: MagicMock,
        config: OpenTelemetryConfig,
        tracer_provider: MagicMock,
        meter_provider: MagicMock,
    ) -> None:
        """Verify the Requests instrumentor is invoked with both providers."""
        with (
            patch(
                "fastapi_factory_utilities.core.plugins.opentelemetry_plugin.instruments.find_spec",
                return_value=MagicMock(),
            ),
            patch("opentelemetry.instrumentation.requests.RequestsInstrumentor") as instrumentor_cls,
        ):
            instrument_requests(
                application=application,
                config=config,
                meter_provider=meter_provider,
                tracer_provider=tracer_provider,
            )
            instrumentor_cls.return_value.instrument.assert_called_once_with(
                tracer_provider=tracer_provider,
                meter_provider=meter_provider,
            )

    def test_noop_when_packages_missing(
        self,
        application: MagicMock,
        config: OpenTelemetryConfig,
        tracer_provider: MagicMock,
        meter_provider: MagicMock,
    ) -> None:
        """Verify instrumentation is skipped if requests or its instrumentor is missing."""
        with (
            patch(
                "fastapi_factory_utilities.core.plugins.opentelemetry_plugin.instruments.find_spec",
                return_value=None,
            ),
            patch("opentelemetry.instrumentation.requests.RequestsInstrumentor") as instrumentor_cls,
        ):
            instrument_requests(
                application=application,
                config=config,
                meter_provider=meter_provider,
                tracer_provider=tracer_provider,
            )
            instrumentor_cls.assert_not_called()


class TestInstrumentUrllib3(_BaseInstrumentTest):
    """Tests for ``instrument_urllib3``."""

    def test_calls_urllib3_instrumentor_when_packages_available(
        self,
        application: MagicMock,
        config: OpenTelemetryConfig,
        tracer_provider: MagicMock,
        meter_provider: MagicMock,
    ) -> None:
        """Verify the urllib3 instrumentor is invoked with both providers."""
        with (
            patch(
                "fastapi_factory_utilities.core.plugins.opentelemetry_plugin.instruments.find_spec",
                return_value=MagicMock(),
            ),
            patch("opentelemetry.instrumentation.urllib3.URLLib3Instrumentor") as instrumentor_cls,
        ):
            instrument_urllib3(
                application=application,
                config=config,
                meter_provider=meter_provider,
                tracer_provider=tracer_provider,
            )
            instrumentor_cls.return_value.instrument.assert_called_once_with(
                tracer_provider=tracer_provider,
                meter_provider=meter_provider,
            )

    def test_noop_when_packages_missing(
        self,
        application: MagicMock,
        config: OpenTelemetryConfig,
        tracer_provider: MagicMock,
        meter_provider: MagicMock,
    ) -> None:
        """Verify instrumentation is skipped if urllib3 or its instrumentor is missing."""
        with (
            patch(
                "fastapi_factory_utilities.core.plugins.opentelemetry_plugin.instruments.find_spec",
                return_value=None,
            ),
            patch("opentelemetry.instrumentation.urllib3.URLLib3Instrumentor") as instrumentor_cls,
        ):
            instrument_urllib3(
                application=application,
                config=config,
                meter_provider=meter_provider,
                tracer_provider=tracer_provider,
            )
            instrumentor_cls.assert_not_called()


class TestInstrumentAsyncio(_BaseInstrumentTest):
    """Tests for ``instrument_asyncio``."""

    def test_calls_asyncio_instrumentor_when_package_available(
        self,
        application: MagicMock,
        config: OpenTelemetryConfig,
        tracer_provider: MagicMock,
        meter_provider: MagicMock,
    ) -> None:
        """Verify the asyncio instrumentor is invoked with the tracer provider only."""
        with (
            patch(
                "fastapi_factory_utilities.core.plugins.opentelemetry_plugin.instruments.find_spec",
                return_value=MagicMock(),
            ),
            patch("opentelemetry.instrumentation.asyncio.AsyncioInstrumentor") as instrumentor_cls,
        ):
            instrument_asyncio(
                application=application,
                config=config,
                meter_provider=meter_provider,
                tracer_provider=tracer_provider,
            )
            instrumentor_cls.return_value.instrument.assert_called_once_with(
                tracer_provider=tracer_provider,
            )

    def test_noop_when_package_missing(
        self,
        application: MagicMock,
        config: OpenTelemetryConfig,
        tracer_provider: MagicMock,
        meter_provider: MagicMock,
    ) -> None:
        """Verify instrumentation is skipped if the asyncio instrumentor is missing."""
        with (
            patch(
                "fastapi_factory_utilities.core.plugins.opentelemetry_plugin.instruments.find_spec",
                return_value=None,
            ),
            patch("opentelemetry.instrumentation.asyncio.AsyncioInstrumentor") as instrumentor_cls,
        ):
            instrument_asyncio(
                application=application,
                config=config,
                meter_provider=meter_provider,
                tracer_provider=tracer_provider,
            )
            instrumentor_cls.assert_not_called()


class TestInstrumentSystemMetrics(_BaseInstrumentTest):
    """Tests for ``instrument_system_metrics``."""

    def test_calls_system_metrics_instrumentor_when_packages_available(
        self,
        application: MagicMock,
        config: OpenTelemetryConfig,
        tracer_provider: MagicMock,
        meter_provider: MagicMock,
    ) -> None:
        """Verify the SystemMetrics instrumentor is invoked with the meter provider only."""
        with (
            patch(
                "fastapi_factory_utilities.core.plugins.opentelemetry_plugin.instruments.find_spec",
                return_value=MagicMock(),
            ),
            patch(
                "opentelemetry.instrumentation.system_metrics.SystemMetricsInstrumentor",
            ) as instrumentor_cls,
        ):
            instrument_system_metrics(
                application=application,
                config=config,
                meter_provider=meter_provider,
                tracer_provider=tracer_provider,
            )
            instrumentor_cls.return_value.instrument.assert_called_once_with(
                meter_provider=meter_provider,
            )

    def test_noop_when_packages_missing(
        self,
        application: MagicMock,
        config: OpenTelemetryConfig,
        tracer_provider: MagicMock,
        meter_provider: MagicMock,
    ) -> None:
        """Verify instrumentation is skipped if psutil or the instrumentor is missing."""
        with (
            patch(
                "fastapi_factory_utilities.core.plugins.opentelemetry_plugin.instruments.find_spec",
                return_value=None,
            ),
            patch(
                "opentelemetry.instrumentation.system_metrics.SystemMetricsInstrumentor",
            ) as instrumentor_cls,
        ):
            instrument_system_metrics(
                application=application,
                config=config,
                meter_provider=meter_provider,
                tracer_provider=tracer_provider,
            )
            instrumentor_cls.assert_not_called()
