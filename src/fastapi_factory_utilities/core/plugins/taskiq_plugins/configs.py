"""Provides the configurations for the Taskiq plugin."""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class RedisCredentialsConfig(BaseModel):
    """Redis credentials config."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
    url: str
