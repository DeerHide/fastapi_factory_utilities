"""Cong Test."""

import logging

from fastapi_factory_utilities.core.utils.log import (
    LoggingConfig,
    LogModeEnum,
    setup_log,
)

from .fixtures.microcks import (
    fixture_microcks_container,
)
from .fixtures.mongo import (
    fixture_async_motor_database,
    fixture_mongodb_database_name,
    fixture_mongodb_server_as_container,
    fixture_odm_plugin_factory,
)
from .fixtures.rabbitmq_fixture import (
    fixture_aiopika_plugin,
    fixture_rabbitmq_container,
    fixture_vhost,
)
from .fixtures.redis import (
    fixture_redis_container,
    fixture_scheduler_component,
    fixture_taskiq_plugin,
    fixture_taskiq_plugin_factory,
    fixture_taskiq_suffix_name,
)

setup_log(
    mode=LogModeEnum.CONSOLE,
    log_level="DEBUG",
    logging_config=[
        LoggingConfig(name="pymongo", level=logging.INFO),
        LoggingConfig(name="mirakuru", level=logging.INFO),
        LoggingConfig(name="asyncio", level=logging.INFO),
    ],
)


__all__: list[str] = [
    "fixture_aiopika_plugin",
    "fixture_async_motor_database",
    "fixture_microcks_container",
    "fixture_mongodb_database_name",
    "fixture_mongodb_server_as_container",
    "fixture_odm_plugin_factory",
    "fixture_rabbitmq_container",
    "fixture_redis_container",
    "fixture_scheduler_component",
    "fixture_taskiq_plugin",
    "fixture_taskiq_plugin_factory",
    "fixture_taskiq_suffix_name",
    "fixture_vhost",
]
