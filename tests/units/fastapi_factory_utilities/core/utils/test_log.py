"""Test the setup.log module."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from fastapi_factory_utilities.core.utils.log import ProbeAccessLogFilter, setup_log


class TestSetupLog:
    """Various tests for the setup_log function."""

    @patch("structlog.configure")
    def test_structlog_has_been_configured(self, structlog_configure_mock: MagicMock) -> None:
        """Test that structlog has been configured.

        Args:
            structlog_configure_mock (MagicMock): The structlog.configure mock.
        """
        setup_log()

        # Called once and only once
        assert structlog_configure_mock.called
        assert structlog_configure_mock.call_count == 1

    def test_setup_log_attaches_probe_access_log_filter(self) -> None:
        """Test that setup_log attaches ProbeAccessLogFilter to the root handler."""
        setup_log()

        root_logger: logging.Logger = logging.getLogger()
        assert any(
            isinstance(log_filter, ProbeAccessLogFilter)
            for handler in root_logger.handlers
            for log_filter in handler.filters
        )


class TestProbeAccessLogFilter:
    """Tests for ProbeAccessLogFilter."""

    @pytest.mark.parametrize(
        ("logger_name", "message", "expected"),
        [
            (
                "uvicorn.access",
                '10.244.1.120:53658 - "GET /api/v1/sys/health HTTP/1.1" 200',
                False,
            ),
            (
                "uvicorn.access",
                '10.244.1.120:53666 - "GET /api/v1/sys/readiness HTTP/1.1" 200',
                False,
            ),
            (
                "hypercorn.access",
                '10.244.1.120:53658 - "GET /api/v1/sys/health HTTP/1.1" 200',
                False,
            ),
            (
                "granian.access",
                '10.244.1.120:53666 - "GET /api/v1/sys/readiness HTTP/1.1" 200',
                False,
            ),
            (
                "uvicorn.access",
                '10.244.1.120:53658 - "GET /api/v1/sys/health HTTP/1.1" 500',
                True,
            ),
            (
                "uvicorn.access",
                '10.244.1.120:53666 - "GET /api/v1/sys/readiness HTTP/1.1" 500',
                True,
            ),
            (
                "uvicorn.access",
                '10.244.1.120:53658 - "GET /api/v1/sys/health/components HTTP/1.1" 200',
                True,
            ),
            (
                "uvicorn.access",
                '10.244.1.120:53658 - "GET /api/v1/other HTTP/1.1" 200',
                True,
            ),
            (
                "myapp.service",
                "any message",
                True,
            ),
        ],
    )
    def test_filter_probe_access_logs(self, logger_name: str, message: str, expected: bool) -> None:
        """Test filtering of probe access log lines.

        Args:
            logger_name (str): The logger name for the record.
            message (str): The log message.
            expected (bool): Whether the record should pass the filter.
        """
        log_filter = ProbeAccessLogFilter()
        record = logging.LogRecord(
            name=logger_name,
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg=message,
            args=(),
            exc_info=None,
        )

        assert log_filter.filter(record) is expected
