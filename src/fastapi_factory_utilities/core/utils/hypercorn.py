"""Provides Hypercorn server utilities for the application."""

import asyncio
import os
from typing import Any, cast

from hypercorn.asyncio import serve as hypercorn_serve
from hypercorn.config import Config

from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol
from fastapi_factory_utilities.core.utils.log import clean_hypercorn_logger


class HypercornUtils:
    """Provides utilities for Hypercorn."""

    def __init__(self, app: ApplicationAbstractProtocol) -> None:
        """Instantiate the Hypercorn utilities."""
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

    def build_hypercorn_config(self) -> Config:
        """Build the Hypercorn configuration."""
        app_config = self._app.get_config()
        config = Config()
        config.bind = [f"{app_config.server.host}:{app_config.server.port}"]
        config.workers = app_config.server.workers
        config.use_reloader = app_config.development.reload

        if self._ssl_keyfile:
            config.keyfile = str(self._ssl_keyfile)
        if self._ssl_certfile:
            config.certfile = str(self._ssl_certfile)
        if self._ssl_keyfile_password:
            config.keyfile_password = self._ssl_keyfile_password

        clean_hypercorn_logger()
        return config

    def serve(self) -> None:
        """Serve the application with Hypercorn."""
        config = self.build_hypercorn_config()
        asyncio.run(hypercorn_serve(cast(Any, self._app.get_asgi_app()), config))
