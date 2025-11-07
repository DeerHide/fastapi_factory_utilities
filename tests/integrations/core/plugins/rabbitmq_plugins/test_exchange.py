"""Test the exchange for the RabbitMQ plugin."""

from aio_pika import ExchangeType
from docker.models.containers import ExecResult
from testcontainers.rabbitmq import RabbitMqContainer

from fastapi_factory_utilities.core.plugins.aiopika import AiopikaPlugin, Exchange


def extract_exchange_names_from_output(output: bytes) -> list[str]:
    r"""Extract exchange names from RabbitMQ list_exchanges command output.

    Args:
        output: The raw bytes output from rabbitmqctl list_exchanges command

    Returns:
        List of exchange names found in the output
    """
    # Decode bytes to string
    output_str = output.decode("utf-8")

    # Find the line that contains the table header (name\ttype)
    lines = output_str.strip().split("\n")

    exchange_names: list[str] = []
    found_header = False

    for line in lines:
        # Look for the header line
        if "name\ttype" in line:
            found_header = True
            continue

        # After finding header, extract exchange names from subsequent lines
        if found_header and line.strip():
            # Split by tab and take the first column (exchange name)
            parts = line.split("\t")
            if parts and parts[0].strip():
                exchange_names.append(parts[0].strip())

    return exchange_names


class TestExchangeRabbitMQ:
    """Test the RabbitMQ exchange."""

    async def test_exchange(
        self, aiopika_plugin: AiopikaPlugin, rabbitmq_container: RabbitMqContainer, vhost: str
    ) -> None:
        """Test the RabbitMQ exchange."""
        # Prepare the exchange
        exchange: Exchange = Exchange(name="test_exchange", exchange_type=ExchangeType.FANOUT)
        exchange.set_robust_connection(robust_connection=aiopika_plugin.robust_connection)
        await exchange.setup()

        result: ExecResult = rabbitmq_container.exec(command=f"rabbitmqctl list_exchanges -p {vhost}")
        exchange_names = extract_exchange_names_from_output(result.output)
        assert "test_exchange" in exchange_names, f"Expected 'test_exchange' in {exchange_names}"
