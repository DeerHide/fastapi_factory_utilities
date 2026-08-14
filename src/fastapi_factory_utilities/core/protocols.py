"""Protocols for the base application."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, ClassVar, Protocol

from fastapi import FastAPI

from fastapi_factory_utilities.core.services.status.services import StatusService

if TYPE_CHECKING:
    from beanie import Document

    from fastapi_factory_utilities.core.app.config import RootConfig


class ApplicationAbstractProtocol(Protocol):
    """Protocol for the base application."""

    PACKAGE_NAME: ClassVar[str]

    ODM_DOCUMENT_MODELS: ClassVar[list[type[Document]]]

    @abstractmethod
    def get_config(self) -> RootConfig:
        """Get the application configuration."""

    @abstractmethod
    def get_asgi_app(self) -> FastAPI:
        """Get the ASGI application."""

    @abstractmethod
    def get_status_service(self) -> StatusService:
        """Get the status service."""
