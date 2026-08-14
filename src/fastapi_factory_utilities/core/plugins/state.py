"""Typed registry of values plugins publish on ``app.state``.

Write with ``PluginAbstract._add_to_state`` and read with ``get_from_state``
(or ``StateKey.resource_attr`` for prefixed multi-resource keys). Do not
scatter the attribute strings.
"""

from dataclasses import dataclass
from typing import Any

from fastapi.datastructures import State

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError


class PluginNotRegisteredError(FastAPIFactoryUtilitiesError):
    """Raised when a depends_* accessor finds no plugin value on application state."""


class PluginNotBoundError(FastAPIFactoryUtilitiesError):
    """Raised when a plugin method needs the application before ``set_application``."""


@dataclass(frozen=True, slots=True)
class StateKey:
    """One named value plugins publish on ``app.state``."""

    attr: str
    plugin: str

    def resource_attr(self, suffix: str) -> str:
        """Return ``attr`` concatenated with a resource suffix (aiohttp / s3)."""
        return f"{self.attr}{suffix}"


def get_from_state(state: State, key: StateKey) -> Any:
    """Return ``state.<key.attr>``, or raise if the plugin was not registered.

    Args:
        state: FastAPI application state.
        key: Registry entry for the value.

    Returns:
        The published value.

    Raises:
        PluginNotRegisteredError: If the attribute is missing or ``None``.
    """
    value: Any = getattr(state, key.attr, None)
    if value is None:
        raise PluginNotRegisteredError(f"{key.plugin} is not registered; {key.attr} missing from application state.")
    return value


ODM_CLIENT = StateKey(attr="odm_client", plugin="ODMPlugin")
ODM_DATABASE = StateKey(attr="odm_database", plugin="ODMPlugin")
REDIS_CLIENT = StateKey(attr="redis_client", plugin="RedisPlugin")
REDIS_PLUGIN = StateKey(attr="redis_plugin", plugin="RedisPlugin")
S3_CLIENT = StateKey(attr="s3_client", plugin="S3Plugin")
S3_BUCKET_PREFIX = StateKey(attr="s3_bucket_", plugin="S3Plugin")
AIOHTTP_RESOURCE_PREFIX = StateKey(attr="aiohttp_resource_", plugin="AioHttpClientPlugin")
AIOPIKA_CONNECTION = StateKey(attr="aiopika_robust_connection", plugin="AiopikaPlugin")
SCHEDULER_COMPONENT = StateKey(attr="scheduler_component", plugin="TaskiqPlugin")
TRACER_PROVIDER = StateKey(attr="tracer_provider", plugin="OpenTelemetryPlugin")
METER_PROVIDER = StateKey(attr="meter_provider", plugin="OpenTelemetryPlugin")
OTEL_CONFIG = StateKey(attr="otel_config", plugin="OpenTelemetryPlugin")

ALL_KEYS: tuple[StateKey, ...] = (
    ODM_CLIENT,
    ODM_DATABASE,
    REDIS_CLIENT,
    REDIS_PLUGIN,
    S3_CLIENT,
    S3_BUCKET_PREFIX,
    AIOHTTP_RESOURCE_PREFIX,
    AIOPIKA_CONNECTION,
    SCHEDULER_COMPONENT,
    TRACER_PROVIDER,
    METER_PROVIDER,
    OTEL_CONFIG,
)
