"""Provide the configuration for the app server."""

from typing import Any, ClassVar, Generic, TypeVar, get_args

from pydantic import BaseModel, ConfigDict, Field

from fastapi_factory_utilities.core.app.exceptions import ConfigBuilderError
from fastapi_factory_utilities.core.utils.configs import (
    UnableToReadConfigFileError,
    ValueErrorConfigError,
    build_config_from_file_in_package,
)
from fastapi_factory_utilities.core.utils.log import LoggingConfig

from .enums import EnvironmentEnum


def default_allow_all() -> list[str]:
    """Default allow all."""
    return ["*"]


class CorsConfig(BaseModel):
    """CORS configuration."""

    allow_origins: list[str] = Field(default_factory=default_allow_all, description="Allowed origins")
    allow_credentials: bool = Field(default=True, description="Allow credentials")
    allow_methods: list[str] = Field(default_factory=default_allow_all, description="Allowed methods")
    allow_headers: list[str] = Field(default_factory=default_allow_all, description="Allowed headers")
    expose_headers: list[str] = Field(default_factory=list, description="Exposed headers")
    max_age: int = Field(default=600, description="Max age")


class ServerConfig(BaseModel):
    """Server configuration."""

    # Pydantic configuration
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    # Server configuration mainly used by uvicorn
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of workers")


class DevelopmentConfig(BaseModel):
    """Development configuration."""

    # Pydantic configuration
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    # Development configuration
    debug: bool = Field(default=False, description="Debug mode")
    reload: bool = Field(default=False, description="Reload mode")


class BaseApplicationConfig(BaseModel):
    """Application configuration abstract class."""

    # Pydantic configuration
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    # Application configuration
    # (mainly used for monitoring and information reporting)
    service_namespace: str = Field(description="Service namespace")
    environment: EnvironmentEnum = Field(description="Deployed environment")
    service_name: str = Field(description="Service name")
    description: str = Field(description="Service description")
    version: str = Field(description="Service version")
    # Root path for the application
    root_path: str = Field(default="", description="Root path")


class RootConfig(BaseModel):
    """Root configuration."""

    # Pydantic configuration
    # extra = Extra.ignore, to be able to add extra categories for your application purposes
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    # Root configuration with all sub configurations
    application: BaseApplicationConfig = Field(description="Application configuration")
    server: ServerConfig = Field(description="Server configuration", default_factory=ServerConfig)
    cors: CorsConfig = Field(description="CORS configuration", default_factory=CorsConfig)
    development: DevelopmentConfig = Field(description="Development configuration", default_factory=DevelopmentConfig)
    logging: list[LoggingConfig] = Field(description="Logging configuration", default_factory=list)


GenericConfig = TypeVar("GenericConfig", bound=BaseModel)


class GenericConfigBuilder(Generic[GenericConfig]):
    """Application configuration builder.

    This class is used to build the application configuration from a YAML file.
    It can be used to build any configuration model
    """

    DEFAULT_FILENAME: str = "application.yaml"
    DEFAULT_YAML_BASE_KEY: str | None = None

    def __init__(
        self,
        package_name: str,
        config_class: type[GenericConfig] | None = None,
        filename: str = DEFAULT_FILENAME,
        yaml_base_key: str | None = DEFAULT_YAML_BASE_KEY,
    ) -> None:
        """Instantiate the builder.

        Args:
            package_name (str): The package name.
            config_class (Type[AppConfigAbstract]): The configuration class.
            filename (str, optional): The filename. Defaults to DEFAULT_FILENAME.
            yaml_base_key (str, optional): The YAML base key. Defaults to DEFAULT_YAML_BASE_KEY.

        TODO: prevent the double definition of config_class and through the generic type
        """
        self.package_name: str = package_name
        generic_args: tuple[Any, ...] = get_args(self.__orig_bases__[0])  # type: ignore

        self.config_class: type[GenericConfig] = config_class if config_class is not None else generic_args[0]
        self.filename: str = filename
        self.yaml_base_key: str | None = yaml_base_key

    def build(self) -> GenericConfig:
        """Build the configuration.

        Returns:
            GenericConfig: The configuration.

        Raises:
            ApplicationConfigFactoryException: Any error occurred
        """
        try:
            config: GenericConfig = build_config_from_file_in_package(
                package_name=self.package_name,
                config_class=self.config_class,
                filename=self.filename,
                yaml_base_key=self.yaml_base_key,
            )
        except UnableToReadConfigFileError as exception:
            raise ConfigBuilderError(
                message="Unable to read the application configuration file.",
                config_class=self.config_class,
                package=self.package_name,
                filename=self.filename,
            ) from exception
        except ValueErrorConfigError as exception:
            raise ConfigBuilderError(
                message="Value error when creating the configuration object.",
                config_class=self.config_class,
                package=self.package_name,
                filename=self.filename,
            ) from exception
        except Exception as exception:
            raise ConfigBuilderError(
                message="An error occurred while building the application configuration.",
                config_class=self.config_class,
                package=self.package_name,
                filename=self.filename,
            ) from exception

        return config
