"""Unit tests for Granian server utilities."""

from unittest.mock import MagicMock, patch

from fastapi_factory_utilities.core.app.config import DevelopmentConfig, ServerConfig
from fastapi_factory_utilities.core.utils.granian import GranianUtils


class TestGranianUtils:
    """Tests for ``GranianUtils``."""

    @patch("fastapi_factory_utilities.core.utils.granian.clean_granian_logger")
    @patch("fastapi_factory_utilities.core.utils.granian.Server")
    def test_build_granian_server_enables_logging(
        self,
        mock_server_class: MagicMock,
        mock_clean_granian_logger: MagicMock,
    ) -> None:
        """Granian embed server keeps logging enabled so startup errors are visible."""
        mock_app: MagicMock = MagicMock()
        mock_app.get_asgi_app.return_value = MagicMock()
        mock_app.get_config.return_value = MagicMock(
            server=ServerConfig(host="127.0.0.1", port=8000, workers=1),
            development=DevelopmentConfig(debug=False, reload=False),
        )

        GranianUtils(app=mock_app).build_granian_server()

        mock_clean_granian_logger.assert_called_once()
        assert mock_server_class.call_args.kwargs["log_enabled"] is True
