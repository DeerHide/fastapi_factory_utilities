"""ODM Plugin Module."""

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
