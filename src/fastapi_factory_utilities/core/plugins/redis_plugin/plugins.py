"""General-purpose async Redis client plugin."""

from reactivex import Subject
from redis.asyncio import Redis
from structlog.stdlib import BoundLogger, get_logger

from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract
from fastapi_factory_utilities.core.plugins.redis_plugin.configs import (
    RedisCredentialsConfig,
    build_redis_credentials_config,
)
from fastapi_factory_utilities.core.plugins.redis_plugin.exceptions import (
    RedisPluginConfigError,
    RedisPluginNotStartedError,
)
from fastapi_factory_utilities.core.services.status.enums import (
    ComponentTypeEnum,
    HealthStatusEnum,
    ReadinessStatusEnum,
)
from fastapi_factory_utilities.core.services.status.services import StatusService
from fastapi_factory_utilities.core.services.status.types import (
    ComponentInstanceType,
    Status,
)

from .constants import STATE_REDIS_CLIENT_KEY, STATE_REDIS_PLUGIN_KEY

_logger: BoundLogger = get_logger()


class RedisPlugin(PluginAbstract):
    """Async Redis client plugin with a namespaced key builder.

    Owns its own connection pool (separate from ``TaskiqPlugin``). Does not set
    TTL, serialization, or fail-open policy — those belong to consumers.
    """

    def __init__(
        self,
        name_suffix: str,
        redis_credentials_config: RedisCredentialsConfig | None = None,
    ) -> None:
        """Initialize the Redis plugin.

        Args:
            name_suffix: Service key prefix (e.g. ``customers-backend``). Every
                key built via ``build_key`` is prefixed with this value so
                per-service Valkey ACL grants (``~<svc>:*``) cover them.
            redis_credentials_config: Optional injected credentials (skips YAML).
        """
        super().__init__()
        if not name_suffix:
            raise ValueError("name_suffix must be a non-empty string")
        self._name_suffix: str = name_suffix
        self._redis_credentials_config: RedisCredentialsConfig | None = redis_credentials_config
        self._client: Redis | None = None
        self._component_instance: ComponentInstanceType | None = None
        self._monitoring_subject: Subject[Status] | None = None

    @property
    def client(self) -> Redis:
        """Return the async Redis client.

        Returns:
            The started ``redis.asyncio.Redis`` client.

        Raises:
            RedisPluginNotStartedError: If the plugin has not started yet.
        """
        if self._client is None:
            raise RedisPluginNotStartedError("RedisPlugin client is not available; call on_startup first")
        return self._client

    @property
    def name_suffix(self) -> str:
        """Return the key namespace prefix."""
        return self._name_suffix

    def build_key(self, *parts: str) -> str:
        """Build a namespaced Redis key ``<name_suffix>:<part>:…``.

        Consumers MUST use this helper for every key they write so per-service
        Valkey ACL grants (``~<svc>:*``) cover them.

        Args:
            *parts: Non-empty key segments after the service prefix.

        Returns:
            The colon-joined key.

        Raises:
            ValueError: If no parts are given or any part is empty.
        """
        if not parts or any(part == "" for part in parts):
            raise ValueError("build_key requires at least one non-empty part")
        return ":".join((self._name_suffix, *parts))

    def on_load(self) -> None:
        """Resolve Redis credentials without opening a connection."""
        assert self._application is not None
        if self._redis_credentials_config is None:
            try:
                self._redis_credentials_config = build_redis_credentials_config(application=self._application)
            except RedisPluginConfigError:
                _logger.exception("Unable to build Redis credentials configuration.")
                raise
        _logger.debug("Redis plugin loaded.", name_suffix=self._name_suffix)

    def _setup_status(self) -> None:
        """Register this plugin with the application status service."""
        assert self._application is not None
        status_service: StatusService = self._application.get_status_service()
        self._component_instance = ComponentInstanceType(
            component_type=ComponentTypeEnum.CACHE,
            identifier="Redis",
        )
        self._monitoring_subject = status_service.register_component_instance(
            component_instance=self._component_instance
        )

    async def on_startup(self) -> None:
        """Create the Redis client, ping it, and register health status."""
        assert self._application is not None
        assert self._redis_credentials_config is not None
        self._setup_status()
        assert self._monitoring_subject is not None

        try:
            self._client = Redis.from_url(
                self._redis_credentials_config.url,
                decode_responses=True,
            )
            await self._client.ping()
        except Exception:  # pylint: disable=broad-except
            self._monitoring_subject.on_next(
                value=Status(health=HealthStatusEnum.UNHEALTHY, readiness=ReadinessStatusEnum.NOT_READY)
            )
            if self._client is not None:
                await self._client.aclose()
                self._client = None
            _logger.exception("Redis plugin failed to start.")
            raise

        self._add_to_state(key=STATE_REDIS_CLIENT_KEY, value=self._client)
        self._add_to_state(key=STATE_REDIS_PLUGIN_KEY, value=self)
        _logger.info("Redis plugin started.", name_suffix=self._name_suffix)
        self._monitoring_subject.on_next(
            value=Status(health=HealthStatusEnum.HEALTHY, readiness=ReadinessStatusEnum.READY)
        )

    async def on_shutdown(self) -> None:
        """Close the Redis client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        _logger.debug("Redis plugin shutdown.")
