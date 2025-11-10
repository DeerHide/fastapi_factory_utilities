"""Oriented Data Model (ODM) plugin package."""

from logging import INFO, Logger, getLogger
from typing import Any, Self, cast

from beanie import Document, init_beanie  # pyright: ignore[reportUnknownVariableType]
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.mongo_client import AsyncMongoClient
from reactivex import Subject
from structlog.stdlib import BoundLogger, get_logger

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol
from fastapi_factory_utilities.core.services.status.enums import (
    ComponentTypeEnum,
    HealthStatusEnum,
    ReadinessStatusEnum,
)
from fastapi_factory_utilities.core.services.status.services import StatusService
from fastapi_factory_utilities.core.services.status.types import (
    ComponentInstanceType,
    Status,
)

from .builder import ODMBuilder
from .configs import ODMConfig
from .depends import depends_odm_client, depends_odm_database
from .documents import BaseDocument
from .exceptions import OperationError, UnableToCreateEntityDueToDuplicateKeyError
from .helpers import PersistedEntity
from .repositories import AbstractRepository

_logger: BoundLogger = get_logger()


class ODMPlugin(PluginAbstract):
    """ODM plugin."""

    def __init__(
        self, document_models: list[type[Document]] | None = None, odm_config: ODMConfig | None = None
    ) -> None:
        """Initialize the ODM plugin."""
        super().__init__()
        self._component_instance: ComponentInstanceType | None = None
        self._monitoring_subject: Subject[Status] | None = None
        self._document_models: list[type[Document]] | None = document_models
        self._odm_config: ODMConfig | None = odm_config
        self._odm_client: AsyncMongoClient[Any] | None = None
        self._odm_database: AsyncDatabase[Any] | None = None

    def set_application(self, application: ApplicationAbstractProtocol) -> Self:
        """Set the application."""
        self._document_models = self._document_models or application.ODM_DOCUMENT_MODELS
        return super().set_application(application)

    def on_load(self) -> None:
        """Actions to perform on load for the ODM plugin."""
        # Configure the pymongo logger to INFO level

        pymongo_logger: Logger = getLogger("pymongo")
        pymongo_logger.setLevel(INFO)
        _logger.debug("ODM plugin loaded.")

    def _setup_status(self) -> None:
        assert self._application is not None
        status_service: StatusService = self._application.get_status_service()
        self._component_instance = ComponentInstanceType(
            component_type=ComponentTypeEnum.DATABASE, identifier="MongoDB"
        )
        self._monitoring_subject = status_service.register_component_instance(
            component_instance=self._component_instance
        )

    async def _setup_beanie(self) -> None:
        assert self._application is not None
        assert self._odm_database is not None
        assert self._document_models is not None
        assert self._monitoring_subject is not None
        # TODO: Find a better way to initialize beanie with the document models of the concrete application
        # through an hook in the application, a dynamis import ?
        try:
            await init_beanie(
                database=self._odm_database,
                document_models=self._document_models,
            )
        except Exception as exception:  # pylint: disable=broad-except
            _logger.error(f"ODM plugin failed to start. {exception}")
            # TODO: Report the error to the status_service
            # this will report the application as unhealthy
            self._monitoring_subject.on_next(
                value=Status(health=HealthStatusEnum.UNHEALTHY, readiness=ReadinessStatusEnum.NOT_READY)
            )

    async def on_startup(self) -> None:
        """Actions to perform on startup for the ODM plugin."""
        host: str
        port: int
        assert self._application is not None
        self._setup_status()
        assert self._monitoring_subject is not None
        assert self._component_instance is not None

        try:
            odm_factory: ODMBuilder = ODMBuilder(application=self._application, odm_config=self._odm_config).build_all()
            assert odm_factory.odm_client is not None
            assert odm_factory.odm_database is not None
            assert (await odm_factory.odm_client.address) is not None
            host, port = cast(tuple[str, int], await odm_factory.odm_client.address)
            await odm_factory.odm_client.aconnect()
            self._odm_database = odm_factory.odm_database
            self._odm_client = odm_factory.odm_client
        except Exception as exception:  # pylint: disable=broad-except
            _logger.error(f"ODM plugin failed to start. {exception}")
            # TODO: Report the error to the status_service
            # this will report the application as unhealthy
            self._monitoring_subject.on_next(
                value=Status(health=HealthStatusEnum.UNHEALTHY, readiness=ReadinessStatusEnum.NOT_READY)
            )
            return None

        self._add_to_state(key="odm_client", value=odm_factory.odm_client)
        self._add_to_state(key="odm_database", value=odm_factory.odm_database)

        await self._setup_beanie()

        assert self._odm_client is not None

        _logger.info(
            f"ODM plugin started. Database: {self._odm_database.name} - "
            f"Client: {host}:{port} - "
            f"Document models: {self._application.ODM_DOCUMENT_MODELS}"
        )

        self._monitoring_subject.on_next(
            value=Status(health=HealthStatusEnum.HEALTHY, readiness=ReadinessStatusEnum.READY)
        )

    async def on_shutdown(self) -> None:
        """Actions to perform on shutdown for the ODM plugin."""
        if self._odm_client is not None:
            await self._odm_client.close()
        _logger.debug("ODM plugin shutdown.")


__all__: list[str] = [
    "AbstractRepository",
    "BaseDocument",
    "OperationError",
    "PersistedEntity",
    "UnableToCreateEntityDueToDuplicateKeyError",
    "depends_odm_client",
    "depends_odm_database",
]
