"""Provides the configuration for the ODM plugin."""

from pydantic import BaseModel, ConfigDict


class ODMConfig(BaseModel):
    """Provides the configuration model for the ODM plugin."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    uri: str

    database: str = "test"

    connection_timeout_ms: int = 4000

    min_pool_size: int = 0

    max_pool_size: int = 100

    max_idle_time_ms: int | None = None

    heartbeat_frequency_ms: int | None = None
