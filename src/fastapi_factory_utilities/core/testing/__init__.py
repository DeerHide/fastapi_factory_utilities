"""Infrastructure test doubles for fastapi_factory_utilities.

Fake at the driver seam (mongomock, fakeredis, moto, taskiq InMemoryBroker,
OTel in-memory exporters). AMQP doubles only record — broker semantics stay on
the RabbitMQ testcontainer.

Install optional deps with::

    pip install 'fastapi_factory_utilities[testing]'
"""

from fastapi_factory_utilities.core.testing.aiopika import InMemoryPublisher, build_incoming_message
from fastapi_factory_utilities.core.testing.contracts import (
    ContractDocument,
    ContractEntity,
    ContractRepository,
    RepositoryContract,
)
from fastapi_factory_utilities.core.testing.odm import (
    build_mongomock_client,
    build_mongomock_database,
    make_contract_entity,
)
from fastapi_factory_utilities.core.testing.otel import InMemoryOtel, build_in_memory_otel
from fastapi_factory_utilities.core.testing.redis import build_fakeredis
from fastapi_factory_utilities.core.testing.s3 import build_s3_bucket_resource, moto_s3_client
from fastapi_factory_utilities.core.testing.taskiq import build_in_memory_scheduler_component

__all__ = [
    "ContractDocument",
    "ContractEntity",
    "ContractRepository",
    "InMemoryOtel",
    "InMemoryPublisher",
    "RepositoryContract",
    "build_fakeredis",
    "build_in_memory_otel",
    "build_in_memory_scheduler_component",
    "build_incoming_message",
    "build_mongomock_client",
    "build_mongomock_database",
    "build_s3_bucket_resource",
    "make_contract_entity",
    "moto_s3_client",
]
