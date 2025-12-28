"""ODM Plugin Module."""

from importlib.util import find_spec

from .depends import depends_odm_client, depends_odm_database
from .documents import BaseDocument
from .exceptions import (
    ODMPluginBaseException,
    ODMPluginConfigError,
    OperationError,
    UnableToCreateEntityDueToDuplicateKeyError,
)
from .helpers import PersistedEntity
from .plugins import ODMPlugin
from .repositories import AbstractRepository

__all__: list[str] = []  # pylint: disable=invalid-name

# Add mockers helpers only if pytest is installed
if find_spec(name="pytest"):
    from .mockers import AbstractRepositoryInMemory

    __all__ += [
        "AbstractRepositoryInMemory",
    ]

__all__ += [
    "AbstractRepository",
    "BaseDocument",
    "ODMPlugin",
    "ODMPluginBaseException",
    "ODMPluginConfigError",
    "OperationError",
    "PersistedEntity",
    "UnableToCreateEntityDueToDuplicateKeyError",
    "depends_odm_client",
    "depends_odm_database",
]
