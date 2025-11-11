"""Configuration for RabbitMQ tests."""

from collections.abc import AsyncGenerator, Generator
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic_core import Url
from testcontainers.rabbitmq import RabbitMqContainer  # pyright: ignore[reportMissingTypeStubs]

from fastapi_factory_utilities.core.plugins.aiopika import AiopikaPlugin
from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol
from fastapi_factory_utilities.core.utils.rabbitmq_configs import RabbitMQCredentialsConfig


@pytest.fixture(scope="session", name="rabbitmq_container")
def fixture_rabbitmq_container() -> Generator[RabbitMqContainer, None, None]:
    """Create a RabbitMQ container."""
    rabbitmq_container: RabbitMqContainer = RabbitMqContainer(
        image="rabbitmq:management",
    )

    rabbitmq_container.start()
    yield rabbitmq_container
    rabbitmq_container.stop(delete_volume=True)


@pytest.fixture(scope="function", name="vhost")
def fixture_vhost() -> Generator[str, None, None]:
    """Create a RabbitMQ vhost."""
    yield str(uuid4())


def create_vhost(rabbitmq_container: RabbitMqContainer, vhost: str, user: str, password: str) -> None:
    """Create a RabbitMQ vhost."""
    rabbitmq_container.exec(command=f"rabbitmqctl add_vhost {vhost}")
    rabbitmq_container.exec(command=f"rabbitmqctl add_user {user} {password}")
    rabbitmq_container.exec(command=f'rabbitmqctl set_permissions -p {vhost} {user} ".*" ".*" ".*"')


def cleanup_vhost(rabbitmq_container: RabbitMqContainer, vhost: str, user: str) -> None:
    """Cleanup a RabbitMQ vhost."""
    rabbitmq_container.exec(command=f"rabbitmqctl delete_vhost {vhost}")
    rabbitmq_container.exec(command=f"rabbitmqctl delete_user {user}")
    rabbitmq_container.exec(command=f"rabbitmqctl delete_permissions -p {vhost} {user}")


@pytest.fixture(scope="function", name="aiopika_plugin")
async def fixture_aiopika_plugin(
    rabbitmq_container: RabbitMqContainer, vhost: str
) -> AsyncGenerator[AiopikaPlugin, None]:
    """Create a Aiopika plugin."""
    user: str = str(uuid4())
    password: str = str(uuid4())
    create_vhost(rabbitmq_container=rabbitmq_container, vhost=vhost, user=user, password=password)
    amqp_url: Url = Url(
        url="amqp://"
        + f"{user}:{password}"
        + f"@{rabbitmq_container.get_container_host_ip()}:{rabbitmq_container.get_exposed_port(port=5672)}"
        + f"/{vhost}"
        + "?heartbeat=10",
    )
    plugin: AiopikaPlugin = AiopikaPlugin(
        rabbitmq_credentials_config=RabbitMQCredentialsConfig(
            amqp_url=amqp_url,
        ),
    )
    plugin.set_application(application=MagicMock(spec=ApplicationAbstractProtocol))
    plugin.on_load()
    await plugin.on_startup()
    yield plugin
    await plugin.on_shutdown()
    cleanup_vhost(rabbitmq_container=rabbitmq_container, vhost=vhost, user=user)
