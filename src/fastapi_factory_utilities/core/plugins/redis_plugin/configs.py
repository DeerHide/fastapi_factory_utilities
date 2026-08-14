"""Redis plugin credentials config."""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol
from fastapi_factory_utilities.core.utils.configs import build_config_from_file_in_package

from .exceptions import RedisPluginConfigError


class RedisCredentialsConfig(BaseModel):
    """Redis credentials config."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
    url: str


def build_redis_credentials_config(application: ApplicationAbstractProtocol) -> RedisCredentialsConfig:
    """Build Redis credentials from the application's ``redis:`` YAML section."""
    return build_config_from_file_in_package(
        package_name=application.PACKAGE_NAME,
        filename="application.yaml",
        config_class=RedisCredentialsConfig,
        yaml_base_key="redis",
        error_type=RedisPluginConfigError,
    )
