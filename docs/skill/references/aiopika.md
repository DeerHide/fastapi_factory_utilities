# AioPika RabbitMQ Messaging

The AioPika plugin provides RabbitMQ message broker integration with automatic OpenTelemetry instrumentation.

## When to Use

Use AioPika plugin when:
- Building message-driven architectures
- Publishing and consuming messages from RabbitMQ
- Implementing event-driven microservices
- Decoupling services with message queues
- Processing messages asynchronously
- Needing automatic OpenTelemetry instrumentation for messaging

## AiopikaPlugin

The plugin manages RabbitMQ connections and provides automatic instrumentation.

### Configuration

```python
from fastapi_factory_utilities.core.plugins.aiopika import AiopikaPlugin
from fastapi_factory_utilities.core.utils.rabbitmq_configs import RabbitMQCredentialsConfig

# With automatic config from package
plugin = AiopikaPlugin()

# With custom config
rabbitmq_config = RabbitMQCredentialsConfig(
    host="localhost",
    port=5672,
    username="guest",
    password="guest",
    virtual_host="/",
)
plugin = AiopikaPlugin(rabbitmq_credentials_config=rabbitmq_config)
```

### Access Connection

```python
from fastapi import Request, Depends
from fastapi_factory_utilities.core.plugins.aiopika.depends import (
    depends_robust_connection,
)

@router.get("/status")
async def status(
    request: Request,
    connection = Depends(depends_robust_connection),
):
    return {"connected": not connection.is_closed}
```

## AbstractListener

Base class for message consumers.

### Implementation

```python
from fastapi_factory_utilities.core.plugins.aiopika import (
    AbstractListener,
    Queue,
    GenericMessage,
)
from pydantic import BaseModel

class OrderMessageData(BaseModel):
    order_id: str
    amount: float

class OrderMessage(GenericMessage[OrderMessageData]):
    pass

class OrderListener(AbstractListener[OrderMessage]):
    def __init__(self, queue: Queue):
        super().__init__(queue=queue, name="order_listener")

    async def on_message(self, message: OrderMessage) -> None:
        try:
            # Process message
            order_data = message.data
            await process_order(order_data.order_id, order_data.amount)

            # Acknowledge message
            await message.ack()
        except Exception as e:
            # Reject and requeue on error
            await message.reject(requeue=True)
            raise
```

### Message Handling

- `await message.ack()` - Acknowledge successful processing
- `await message.reject(requeue=True)` - Reject and requeue
- `await message.reject(requeue=False)` - Reject and discard

## AbstractPublisher

Base class for message producers.

### Implementation

```python
from fastapi_factory_utilities.core.plugins.aiopika import (
    AbstractPublisher,
    Exchange,
    GenericMessage,
)

class OrderPublisher(AbstractPublisher[OrderMessage]):
    def __init__(self, exchange: Exchange):
        super().__init__(exchange=exchange, name="order_publisher")

    async def publish_order(self, order_id: str, amount: float) -> None:
        message = OrderMessage(
            data=OrderMessageData(order_id=order_id, amount=amount),
        )
        routing_key = f"orders.{order_id}"
        await self.publish(message=message, routing_key=routing_key)
```

## Queue Management

### Creating Queues

```python
from fastapi_factory_utilities.core.plugins.aiopika import Queue
from aio_pika.abc import AbstractRobustConnection

async def create_queue(connection: AbstractRobustConnection) -> Queue:
    queue = Queue(
        connection=connection,
        name="orders",
        durable=True,
        auto_delete=False,
    )
    await queue.setup()
    return queue
```

### Queue Options

- `durable=True` - Queue survives broker restart
- `auto_delete=False` - Queue not deleted when unused
- `exclusive=False` - Queue accessible by multiple connections

## Exchange Management

### Creating Exchanges

```python
from fastapi_factory_utilities.core.plugins.aiopika import Exchange
from aio_pika import ExchangeType

async def create_exchange(connection: AbstractRobustConnection) -> Exchange:
    exchange = Exchange(
        connection=connection,
        name="orders_exchange",
        type=ExchangeType.TOPIC,
        durable=True,
    )
    await exchange.setup()
    return exchange
```

## GenericMessage

Type-safe message wrapper with Pydantic validation.

### Structure

```python
class GenericMessage(BaseModel, Generic[GenericMessageData]):
    data: GenericMessageData  # Your message payload
    _incoming_message: AbstractIncomingMessage | None  # Internal
    _headers: HeadersType  # Message headers
```

### Methods

- `get_headers() -> HeadersType` - Get message headers
- `set_headers(headers: HeadersType) -> None` - Set message headers
- `to_aiopika_message() -> Message` - Convert to AioPika message
- `ack() -> None` - Acknowledge message
- `reject(requeue: bool) -> None` - Reject message

## Routing Keys

Use routing keys for message routing:

```python
# Topic exchange routing
routing_key = "orders.created.user.12345"
await publisher.publish(message, routing_key=routing_key)

# Pattern: {prefix}.{action}.{entity}.{id}
```

## OpenTelemetry Integration

The plugin automatically instruments:
- Message publishing
- Message consumption
- Queue operations
- Exchange operations

Traces include:
- Routing keys
- Message sizes
- Operation duration
- Error information

## Error Handling

The AioPika plugin and message handling can encounter various errors that should be handled appropriately.

### Message Publishing Errors

```python
from aio_pika.exceptions import AMQPConnectionError, AMQPChannelError

try:
    await publisher.publish(message=message, routing_key=routing_key)
except AMQPConnectionError as e:
    # Handle connection failures
    logger.error("RabbitMQ connection error", error=e)
    # Connection will be retried automatically with robust connection
    raise
except AMQPChannelError as e:
    # Handle channel errors
    logger.error("RabbitMQ channel error", error=e)
    raise
except Exception as e:
    # Handle other publishing errors
    logger.error("Failed to publish message", error=e, routing_key=routing_key)
    raise
```

### Message Consumption Errors

```python
class OrderListener(AbstractListener[OrderMessage]):
    async def on_message(self, message: OrderMessage) -> None:
        try:
            # Process message
            order_data = message.data
            await process_order(order_data.order_id, order_data.amount)

            # Acknowledge successful processing
            await message.ack()
        except ValueError as e:
            # Handle validation errors - reject and don't requeue
            logger.error("Invalid message data", error=e)
            await message.reject(requeue=False)
        except TransientError as e:
            # Handle transient errors - reject and requeue
            logger.warning("Transient error, requeuing", error=e)
            await message.reject(requeue=True)
        except Exception as e:
            # Handle unexpected errors
            logger.error("Unexpected error processing message", error=e)
            # Requeue for retry, but consider dead letter queue after max retries
            await message.reject(requeue=True)
            raise
```

### Connection Errors

```python
from aio_pika.exceptions import AMQPConnectionError

try:
    connection = await connect_robust(amqp_url)
except AMQPConnectionError as e:
    # Handle initial connection failure
    logger.error("Failed to connect to RabbitMQ", error=e, url=amqp_url)
    # Retry logic or fail fast
    raise
```

### Queue/Exchange Setup Errors

```python
from aio_pika.exceptions import AMQPChannelError

try:
    await queue.setup()
    await exchange.setup()
except AMQPChannelError as e:
    # Handle queue/exchange declaration errors
    logger.error("Failed to setup queue/exchange", error=e)
    raise
```

### Message Validation Errors

```python
from pydantic import ValidationError

try:
    message = OrderMessage(data=message_data)
except ValidationError as e:
    # Handle Pydantic validation errors
    logger.error("Invalid message format", errors=e.errors())
    # Reject message without requeue
    await message.reject(requeue=False)
```

## Best Practices

1. **Message Acknowledgment**: Always ack or reject messages
2. **Error Handling**: Use reject with requeue for transient errors
3. **Idempotency**: Design message handlers to be idempotent
4. **Routing Keys**: Use consistent routing key patterns
5. **Connection Management**: Use robust connections for automatic reconnection
6. **Message Validation**: Use Pydantic models for message data

## Reference

- `src/fastapi_factory_utilities/core/plugins/aiopika/` - Plugin implementation
- `src/fastapi_factory_utilities/core/plugins/aiopika/listener/abstract.py` - AbstractListener
- `src/fastapi_factory_utilities/core/plugins/aiopika/publisher/abstract.py` - AbstractPublisher
- `src/fastapi_factory_utilities/core/plugins/aiopika/message.py` - GenericMessage
