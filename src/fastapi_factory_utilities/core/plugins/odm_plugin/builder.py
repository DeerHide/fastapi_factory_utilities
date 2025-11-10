"""Provides the module for the ODM plugin."""

from typing import Any, ClassVar, Self

from bson import CodecOptions
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.mongo_client import AsyncMongoClient
from pymongo.server_api import ServerApi, ServerApiVersion
from structlog.stdlib import get_logger

from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol
from fastapi_factory_utilities.core.utils.importlib import get_path_file_in_package
from fastapi_factory_utilities.core.utils.yaml_reader import (
    UnableToReadYamlFileError,
    YamlFileReader,
)

from .configs import ODMConfig
from .exceptions import ODMPluginConfigError

_logger = get_logger()


class ODMBuilder:
    """Factory to create the resources for the ODM plugin.

    The factory is responsible for creating the resources for the ODM plugin.
    - The ODM configuration.
    - The ODM client.
    - The ODM database.

    ```python
    # Example of using the ODMFactory
    odm_factory: ODMFactory = ODMFactory(application=application)
    odm_factory.build_all()
    # Access the ODM database created
    database: AsyncIOMotorDatabase[Any] = odm_factory.database
    ```

    """

    MS_TO_S: ClassVar[int] = 1000
    SLEEP_TIME_S: ClassVar[float] = 0.001

    def __init__(
        self,
        application: ApplicationAbstractProtocol,
        odm_config: ODMConfig | None = None,
        odm_client: AsyncMongoClient[Any] | None = None,
        odm_database: AsyncDatabase[Any] | None = None,
    ) -> None:
        """Initialize the ODMFactory.

        Args:
            application (BaseApplicationProtocol): The application.
            odm_config (ODMConfig): The ODM configuration for injection. (Default is None)
            odm_client (AsyncMongoClient): The ODM client for injection. (Default is None)
            odm_database (AsyncDatabase): The ODM database for injection. (Default is None)

        """
        self._application: ApplicationAbstractProtocol = application
        self._config: ODMConfig | None = odm_config
        self._odm_client: AsyncMongoClient[Any] | None = odm_client
        self._odm_database: AsyncDatabase[Any] | None = odm_database

    @property
    def config(self) -> ODMConfig | None:
        """Provide the ODM configuration object.

        Returns:
            ODMConfig: The ODM configuration object.
        """
        return self._config

    @property
    def odm_client(self) -> AsyncMongoClient[Any] | None:
        """Provide the ODM client.

        Returns:
            AsyncMongoClient | None: The ODM client.
        """
        return self._odm_client

    @property
    def odm_database(self) -> AsyncDatabase[Any] | None:
        """Provide the ODM database.

        Returns:
            AsyncDatabase | None: The ODM database.
        """
        return self._odm_database

    def build_odm_config(
        self,
    ) -> Self:
        """Build the ODM configuration object.

        Returns:
            Self: The ODM factory.

        Raises:
            ODMPluginConfigError: If the package name is not set or the configuration file is not found.
        """
        if self._config is not None:
            return self

        if self._application.PACKAGE_NAME == "":
            raise ODMPluginConfigError("The package name must be set in the concrete application class.")
        # Read the application configuration file
        try:
            yaml_file_content: dict[str, Any] = YamlFileReader(
                file_path=get_path_file_in_package(
                    filename="application.yaml",
                    package=self._application.PACKAGE_NAME,
                ),
                yaml_base_key="odm",
                use_environment_injection=True,
            ).read()
        except (FileNotFoundError, ImportError, UnableToReadYamlFileError) as exception:
            raise ODMPluginConfigError("Unable to read the application configuration file.") from exception

        # Create the application configuration model
        try:
            self._config = ODMConfig(**yaml_file_content)
        except ValueError as exception:
            raise ODMPluginConfigError("Unable to create the application configuration model.") from exception
        return self

    # ======
    # KEEP IT, Waiting for additional tests
    # @classmethod
    # def _wait_client_to_be_ready(cls, client: AsyncIOMotorClient[Any], timeout_s: int) -> None:
    #     """Wait for the ODM client to be ready.

    #     Args:
    #         client (AsyncIOMotorClient): The ODM client.
    #         timeout_s (int): The timeout in seconds.

    #     Raises:
    #         TimeoutError: If the ODM client is not ready in the given timeout.
    #     """
    #     start_time: float = time.time()
    #     message_time: float = time.time()
    #     while (time.time() - start_time) < (timeout_s):
    #         if len(client.nodes) > 0:  # type: ignore
    #             _logger.info(f"Waiting {(time.time() - start_time)*cls.MS_TO_S}ms for the ODM client to be ready.")
    #             return

    #         if (time.time() - message_time) > 1:
    #             elaps_time: float = time.time() - start_time
    #             _logger.debug(f"Waiting for the ODM client to be ready. (from {int(elaps_time)}s) ")
    #             message_time = time.time()
    #         time.sleep(cls.SLEEP_TIME_S)

    #     raise TimeoutError("The ODM client is not ready in the given timeout.")
    # ======

    def build_client(
        self,
    ) -> Self:
        """Build the ODM client.

        Returns:
            Self: The ODM factory.

        Raises:
            ODMPluginConfigError: If the ODM configuration is not build or provided.
        """
        if self._odm_client is not None:
            return self

        if self._config is None:
            raise ODMPluginConfigError(
                "ODM configuration is not set. Provide the ODM configuration using "
                "build_odm_config method or through parameter."
            )

        self._odm_client = AsyncMongoClient(
            host=self._config.uri,
            connect=True,
            connectTimeoutMS=self._config.connection_timeout_ms,
            serverSelectionTimeoutMS=self._config.connection_timeout_ms,
            server_api=ServerApi(version=ServerApiVersion.V1),
            tz_aware=True,
        )

        # KEEP IT, Waiting for additional tests
        # self._wait_client_to_be_ready(client=self._odm_client, timeout_s=self._config.connection_timeout_s)

        return self

    def build_database(
        self,
    ) -> Self:
        """Build the ODM database.

        The ODM client and ODM configuration are recommended to be provided through call to the build_client and
        build_odm_config methods.

        Returns:
            Any: The ODM database.

        Raises:
            ODMPluginConfigError: If the ODM configuration is not build or provided.
        """
        if self._odm_database is not None:
            return self

        if self._config is None:
            raise ODMPluginConfigError(
                "ODM configuration is not set. Provide the ODM configuration using "
                "build_odm_config method or through parameter."
            )

        database_name: str = self._config.database

        if self._odm_client is None:
            raise ODMPluginConfigError(
                "ODM client is not set. Provide the ODM client using build_client method or through parameter."
            )

        self._odm_database = self._odm_client.get_database(
            name=database_name,
            codec_options=CodecOptions(  # pyright: ignore[reportUnknownArgumentType]
                tz_aware=True,
            ),
        )

        return self

    def build_all(self) -> Self:
        """Build all the resources for the ODM plugin.

        Returns:
            Self: The ODM factory.

        Raises:
            ODMPluginConfigError: If the ODM configuration is not build or provided.
        """
        self.build_odm_config()
        self.build_client()
        self.build_database()

        return self
