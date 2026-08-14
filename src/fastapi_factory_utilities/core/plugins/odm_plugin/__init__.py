"""ODM Plugin Module."""

# ruff: noqa: E402
# pylint: disable=wrong-import-position
from fastapi_factory_utilities.core.plugins.extras import require_extra

require_extra("mongo", "beanie")

from .configs import ODMConfig
from .depends import depends_odm_client, depends_odm_database
from .documents import BaseDocument
from .exceptions import (
    ODMPluginBaseException,
    ODMPluginConfigError,
    OperationError,
    UnableToCreateEntityDueToDuplicateKeyError,
)
from .helpers import PersistedEntity
from .mockers import AbstractRepositoryInMemory
from .plugins import ODMPlugin
from .queries import ODMFindQuery, ODMQueryBuilder
from .repositories import AbstractRepository

__all__ = [
    "AbstractRepository",
    "AbstractRepositoryInMemory",
    "BaseDocument",
    "ODMConfig",
    "ODMFindQuery",
    "ODMPlugin",
    "ODMPluginBaseException",
    "ODMPluginConfigError",
    "ODMQueryBuilder",
    "OperationError",
    "PersistedEntity",
    "UnableToCreateEntityDueToDuplicateKeyError",
    "depends_odm_client",
    "depends_odm_database",
]
