"""Provides Granian server utilities for the application."""

import asyncio
import os
import warnings
from pathlib import Path

from granian.constants import Interfaces
from granian.server.embed import Server

from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol
from fastapi_factory_utilities.core.utils.log import clean_granian_logger


class GranianUtils:
    """Provides utilities for Granian."""

    def __init__(self, app: ApplicationAbstractProtocol) -> None:
        """Instantiate the Granian utilities."""
        self._app: ApplicationAbstractProtocol = app
        self._ssl_keyfile: str | os.PathLike[str] | None = None
        self._ssl_certfile: str | os.PathLike[str] | None = None
        self._ssl_keyfile_password: str | None = None

    def add_ssl_certificates(
        self,
        ssl_keyfile: str | os.PathLike[str] | None = None,
        ssl_certfile: str | os.PathLike[str] | None = None,
        ssl_keyfile_password: str | None = None,
    ) -> None:
        """Add SSL certificates to the application."""
        self._ssl_keyfile = ssl_keyfile
        self._ssl_certfile = ssl_certfile
        self._ssl_keyfile_password = ssl_keyfile_password

    def build_granian_server(self) -> Server:
        """Build the Granian embedded server configuration."""
        app_config = self._app.get_config()

        if app_config.server.workers > 1:
            warnings.warn(
                "Granian embed server supports a single worker; ignoring server.workers > 1.",
                stacklevel=2,
            )
        if app_config.development.reload:
            warnings.warn(
                "Granian embed server does not support file reload; ignoring development.reload.",
                stacklevel=2,
            )

        clean_granian_logger()
        return Server(
            target=self._app.get_asgi_app(),
            address=app_config.server.host,
            port=app_config.server.port,
            interface=Interfaces.ASGI,
            ssl_cert=Path(self._ssl_certfile) if self._ssl_certfile else None,
            ssl_key=Path(self._ssl_keyfile) if self._ssl_keyfile else None,
            ssl_key_password=self._ssl_keyfile_password,
            log_enabled=False,
        )

    def serve(self) -> None:
        """Serve the application with Granian."""
        server = self.build_granian_server()
        asyncio.run(server.serve())
