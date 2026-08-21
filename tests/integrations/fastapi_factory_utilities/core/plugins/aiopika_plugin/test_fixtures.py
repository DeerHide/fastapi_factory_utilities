"""Test the RabbitMQ fixtures."""

from fastapi_factory_utilities.core.plugins.aiopika_plugin import AiopikaPlugin


class TestFixturesRabbitMQ:
    """Test the RabbitMQ fixtures."""

    def test_rabbitmq_container(self, aiopika_plugin: AiopikaPlugin) -> None:
        """Test the RabbitMQ container."""
        assert aiopika_plugin is not None
