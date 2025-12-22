"""Test the queue for the RabbitMQ plugin."""

from aio_pika import ExchangeType
from docker.models.containers import ExecResult
from testcontainers.rabbitmq import RabbitMqContainer

from fastapi_factory_utilities.core.plugins.aiopika import Exchange, ExchangeName, Queue, QueueName, RoutingKey
from fastapi_factory_utilities.core.plugins.aiopika.plugins import AiopikaPlugin


def extract_queue_names_from_output(output: bytes) -> list[str]:
    r"""Extract queue names from RabbitMQ list_queues command output.

    Args:
        output: The raw bytes output from rabbitmqctl list_queues command

    Returns:
        List of queue names found in the output

    """
    # Decode bytes to string
    output_str = output.decode("utf-8")

    # Find the line that contains the table header (name\tmessages)
    lines = output_str.strip().split("\n")

    queue_names: list[str] = []
    found_header = False

    for line in lines:
        # Look for the header line
        if "name\tmessages" in line:
            found_header = True
            continue

        # After finding header, extract queue names from subsequent lines
        if found_header and line.strip():
            # Split by tab and take the first column (queue name)
            parts = line.split("\t")
            if parts and parts[0].strip():
                queue_names.append(parts[0].strip())

    return queue_names


class TestQueueRabbitMQ:
    """Test the RabbitMQ queue."""

    async def test_queue(
        self, aiopika_plugin: AiopikaPlugin, rabbitmq_container: RabbitMqContainer, vhost: str
    ) -> None:
        """Test the RabbitMQ queue."""
        # Prepare the exchange
        exchange: Exchange = Exchange(name=ExchangeName("test_exchange"), exchange_type=ExchangeType.FANOUT)
        exchange.set_robust_connection(robust_connection=aiopika_plugin.robust_connection)
        # Prepare the queue
        queue: Queue = Queue(
            name=QueueName("test_queue"), exchange=exchange, routing_key=RoutingKey("test_routing_key")
        )
        queue.set_robust_connection(robust_connection=aiopika_plugin.robust_connection)

        await exchange.setup()
        await queue.setup()

        result: ExecResult = rabbitmq_container.exec(command=f"rabbitmqctl list_queues -p {vhost}")

        # Extract queue names from the output
        queue_names = extract_queue_names_from_output(result.output)

        # Verify that our test queue was created
        assert "test_queue" in queue_names, f"Expected 'test_queue' in {queue_names}"
