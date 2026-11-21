"""Oriented Data Model (ODM) plugin package."""

import asyncio
import os
import socket
from logging import INFO, Logger, getLogger
from typing import Any, Self, cast

from beanie import Document, init_beanie  # pyright: ignore[reportUnknownVariableType]
from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.mongo_client import AsyncMongoClient
from structlog.stdlib import BoundLogger, get_logger

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.plugins.state import ODM_CLIENT, ODM_DATABASE
from fastapi_factory_utilities.core.plugins.status import PluginStatusMixin
from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol
from fastapi_factory_utilities.core.services.status.enums import ComponentTypeEnum

from .builder import ODMBuilder
from .configs import ODMConfig
from .depends import depends_odm_client, depends_odm_database
from .documents import BaseDocument
from .encryption import STARTUP_PROBE_COLLECTION, STARTUP_PROBE_FIELD
from .exceptions import OperationError, UnableToCreateEntityDueToDuplicateKeyError
from .helpers import PersistedEntity
from .migration_lock import MongoSchemaMigrationLock, SchemaMigrationLock
from .migration_sweep import run_schema_migration_loop
from .repositories import AbstractRepository

_logger: BoundLogger = get_logger()


class ODMPlugin(PluginStatusMixin, PluginAbstract):
    """ODM plugin."""

    def __init__(
        self,
        document_models: list[type[Document]] | None = None,
        odm_config: ODMConfig | None = None,
        migration_lock: SchemaMigrationLock | None = None,
    ) -> None:
        """Initialize the ODM plugin.

        Args:
            document_models: Beanie document classes to register.
            odm_config: Optional ODM configuration override.
            migration_lock: Exclusive sweep lock. ``None`` selects the default
                Mongo lease on the same database. Pass a custom lock (e.g. Redis)
                or ``AlwaysAcquireMigrationLock`` in tests.
        """
        super().__init__()
        self._document_models: list[type[Document]] | None = document_models
        self._odm_config: ODMConfig | None = odm_config
        self._migration_lock: SchemaMigrationLock | None = migration_lock
        self._odm_client: AsyncMongoClient[Any] | None = None
        self._odm_database: AsyncDatabase[Any] | None = None
        self._migration_tasks: list[asyncio.Task[None]] = []
        self._migration_owner: str = f"{socket.gethostname()}:{os.getpid()}"

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

    async def _setup_beanie(self) -> None:
        assert self._application is not None
        assert self._odm_database is not None
        assert self._document_models is not None
        # TODO: Find a better way to initialize beanie with the document models of the concrete application
        # through an hook in the application, a dynamis import ?
        try:
            await init_beanie(
                database=self._odm_database,
                document_models=self._document_models,
            )
        except Exception:
            self._report_unhealthy()
            _logger.exception("ODM plugin failed to start.")
            raise

    async def _run_csfle_startup_probe(self) -> None:
        """Force mongocryptd to spawn and connect at startup rather than on the first real write.

        PyMongo spawns mongocryptd lazily, on the first automatically-encrypted operation,
        unlike crypt_shared, which loads eagerly at client construction (see design.md
        decision 3). A throwaway encrypted insert+delete against a dedicated startup-probe
        collection closes that gap: a broken mongocryptd install, or Vault/key vault having
        gone unreachable between the earlier unwrap and now, surfaces here instead of on the
        first real request. There is no fallback to a non-encrypting client on failure.

        Raises:
            Exception: Any failure inserting or deleting the probe document. Marks the ODM
                StatusService component unhealthy and re-raises.
        """
        assert self._odm_client is not None
        assert self._odm_database is not None

        collection = self._odm_client[self._odm_database.name][STARTUP_PROBE_COLLECTION]
        probe_id: ObjectId = ObjectId()
        try:
            await collection.insert_one({"_id": probe_id, STARTUP_PROBE_FIELD: "startup-smoke-test"})
            await collection.delete_one({"_id": probe_id})
        except Exception:
            self._report_unhealthy()
            _logger.exception("CSFLE startup smoke test failed: mongocryptd spawn/connect or Vault unreachable.")
            raise

    def _start_schema_migrations(self) -> None:
        """Spawn one non-blocking sweep task per document with CURRENT_SCHEMA_VERSION > 0."""
        assert self._odm_database is not None
        assert self._document_models is not None

        lock: SchemaMigrationLock = self._migration_lock or MongoSchemaMigrationLock(self._odm_database)
        for document_model in self._document_models:
            if not issubclass(document_model, BaseDocument):
                continue
            if document_model.CURRENT_SCHEMA_VERSION <= 0:
                continue
            task: asyncio.Task[None] = asyncio.create_task(
                run_schema_migration_loop(
                    document_model,
                    lock=lock,
                    owner=self._migration_owner,
                ),
                name=f"schema-migration:{document_model.__name__}",
            )
            self._migration_tasks.append(task)
            _logger.info(
                "schema migration sweep started",
                document=document_model.__name__,
                schema_version=document_model.CURRENT_SCHEMA_VERSION,
                owner=self._migration_owner,
            )

    async def _stop_schema_migrations(self) -> None:
        """Cancel and await background migration tasks."""
        if not self._migration_tasks:
            return
        for task in self._migration_tasks:
            task.cancel()
        await asyncio.gather(*self._migration_tasks, return_exceptions=True)
        self._migration_tasks.clear()

    async def on_startup(self) -> None:
        """Actions to perform on startup for the ODM plugin."""
        host: str
        port: int
        assert self._application is not None
        self._setup_status(component_type=ComponentTypeEnum.DATABASE, identifier="MongoDB")

        try:
            odm_factory: ODMBuilder = ODMBuilder(application=self._application, odm_config=self._odm_config)
            await odm_factory.build_all(document_models=self._document_models)
            assert odm_factory.odm_client is not None
            assert odm_factory.odm_database is not None
            assert (await odm_factory.odm_client.address) is not None
            host, port = cast(tuple[str, int], await odm_factory.odm_client.address)
            await odm_factory.odm_client.aconnect()
            assert odm_factory.config is not None
            client = odm_factory.odm_client
            timeout_s: float = odm_factory.config.connection_timeout_ms / ODMBuilder.MS_TO_S
            await self._warm_soft(
                lambda: asyncio.wait_for(client.admin.command("ping"), timeout=timeout_s),
                what="MongoDB connection",
            )
            self._odm_database = odm_factory.odm_database
            self._odm_client = odm_factory.odm_client
        except Exception:
            self._report_unhealthy()
            _logger.exception("ODM plugin failed to start.")
            raise

        self._add_to_state(key=ODM_CLIENT, value=odm_factory.odm_client)
        self._add_to_state(key=ODM_DATABASE, value=odm_factory.odm_database)

        await self._setup_beanie()

        if odm_factory.auto_encryption_opts is not None:
            await self._run_csfle_startup_probe()

        assert self._odm_client is not None

        self._start_schema_migrations()

        _logger.info(
            f"ODM plugin started. Database: {self._odm_database.name} - "
            f"Client: {host}:{port} - "
            f"Document models: {self._application.ODM_DOCUMENT_MODELS}"
        )

        self._report_healthy()

    async def on_shutdown(self) -> None:
        """Actions to perform on shutdown for the ODM plugin."""
        await self._stop_schema_migrations()
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
