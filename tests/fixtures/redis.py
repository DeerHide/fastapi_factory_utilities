"""Configuration for Redis tests."""

from collections.abc import Callable, Generator
from typing import ClassVar
from unittest.mock import patch
from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict
from testcontainers.redis import RedisContainer

from fastapi_factory_utilities.core.plugins.taskiq_plugins.plugin import TaskiqPlugin
from fastapi_factory_utilities.core.plugins.taskiq_plugins.schedulers import SchedulerComponent
from fastapi_factory_utilities.core.utils.redis_configs import RedisCredentialsConfig


class RedisFixture(BaseModel):
    """Redis fixture."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    redis_container: RedisContainer

    def get_connection_url(self) -> str:
        """Get the connection URL for the Redis container."""
        return f"redis://{self.redis_container.get_container_host_ip()}:{self.redis_container.get_exposed_port(6379)}"


@pytest.fixture(scope="session", name="redis_container")
def fixture_redis_container() -> Generator[RedisFixture, None, None]:
    """Create a Redis container."""
    with RedisContainer(image="redis:latest") as redis_container:
        with patch.dict(
            "os.environ",
            {
                "REDIS_URL": f"redis://{redis_container.get_container_host_ip()}:"
                f"{redis_container.get_exposed_port(6379)}",
            },
        ):
            yield RedisFixture(redis_container=redis_container)


@pytest.fixture(scope="function", name="taskiq_suffix_name")
def fixture_taskiq_suffix_name() -> str:
    """Get the suffix name for the Taskiq scheduler."""
    return f"test_{uuid4()}"


@pytest.fixture(scope="function", name="taskiq_plugin")
def fixture_taskiq_plugin(taskiq_suffix_name: str, redis_container: RedisFixture) -> TaskiqPlugin:
    """Create a Taskiq plugin."""
    plugin: TaskiqPlugin = TaskiqPlugin(
        name_suffix=taskiq_suffix_name,
        redis_credentials_config=RedisCredentialsConfig(
            url=redis_container.get_connection_url(),
        ),
    )
    return plugin


@pytest.fixture(scope="function", name="taskiq_plugin_factory")
def fixture_taskiq_plugin_factory(
    taskiq_suffix_name: str, redis_container: RedisFixture
) -> Callable[[Callable[[SchedulerComponent], None] | None], TaskiqPlugin]:
    """Create a Taskiq plugin factory."""

    def _factory(register_hook: Callable[[SchedulerComponent], None] | None = None) -> TaskiqPlugin:
        return TaskiqPlugin(
            name_suffix=taskiq_suffix_name,
            redis_credentials_config=RedisCredentialsConfig(
                url=redis_container.get_connection_url(),
            ),
            register_hook=register_hook,
        )

    return _factory


@pytest.fixture(scope="function", name="scheduler_component")
def fixture_scheduler_component(taskiq_suffix_name: str) -> SchedulerComponent:
    """Create a scheduler component for testing."""
    return SchedulerComponent(name_suffix=taskiq_suffix_name)
