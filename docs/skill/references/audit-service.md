# Audit Service

The audit service provides event auditing capabilities with RabbitMQ message publishing.

## When to Use

Use the audit service when:
- Publishing audit events for compliance and tracking
- Recording entity lifecycle events (created, updated, deleted)
- Tracking user actions and system events
- Implementing event-driven audit logging
- Building audit trails for regulatory compliance
- Decoupling audit event publishing from business logic

## AbstractAuditPublisherService

Base class for publishing audit events to RabbitMQ.

### Implementation

```python
from fastapi_factory_utilities.core.services.audit import (
    AbstractAuditPublisherService,
    AuditEventObject,
    ServiceName,
)
from fastapi_factory_utilities.core.plugins.aiopika import (
    AbstractPublisher,
    RoutingKey,
)

class OrderAuditEvent(AuditEventObject):
    what: EntityName = "order"
    why: EntityFunctionalEventName
    where: ServiceName
    when: datetime.datetime
    who: dict[str, Any]

class OrderAuditService(AbstractAuditPublisherService[OrderAuditEvent]):
    def build_routing_key_pattern(self, audit_event: OrderAuditEvent) -> RoutingKey:
        # Pattern: {prefix}.{where}.{what}.{why}
        return RoutingKey(f"audit.{audit_event.where}.{audit_event.what}.{audit_event.why}")
```

### Publishing Events

```python
async def create_order(order_data: dict, audit_service: OrderAuditService):
    # Create order logic
    order = await repository.insert(order_data)

    # Publish audit event
    audit_event = OrderAuditEvent(
        what="order",
        why="created",
        where="order_service",
        when=datetime.datetime.now(tz=datetime.UTC),
        who={"id": str(user_id), "realm": "main"},
    )
    await audit_service.publish(audit_event)

    return order
```

## AuditEventObject

Structured audit event with what, why, where, when, who.

### Structure

```python
class AuditEventObject(BaseModel, Generic[AuditEventActorGeneric]):
    what: EntityName  # Entity name (e.g., "order", "user")
    why: EntityFunctionalEventName  # Event name (e.g., "created", "updated")
    where: ServiceName  # Service name
    when: datetime.datetime  # Event timestamp
    who: dict[str, Any]  # Actor information (must contain "id")
```

### Validation

The `who` field is validated:
- Must be a non-empty dictionary
- Must contain an `"id"` key
- Can contain additional keys (realm, group, etc.)

### Example

```python
audit_event = AuditEventObject(
    what="order",
    why="created",
    where="order_service",
    when=datetime.datetime.now(tz=datetime.UTC),
    who={
        "id": "user-123",
        "realm": "main",
        "group": "admins",
    },
)
```

## AuditableEntity

Base class for entities that can be audited.

### Implementation

```python
from fastapi_factory_utilities.core.services.audit.objects import (
    AuditableEntity,
    EntityName,
)

class OrderEntity(AuditableEntity):
    _audit_name: EntityName = EntityName("order")

    id: UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    deleted_at: datetime.datetime | None = None
    # ... other fields

# Get audit name
order = OrderEntity(...)
audit_name = order.get_audit_name()  # "order"
```

## Routing Key Pattern

Routing keys follow a consistent pattern:

```
{prefix}.{where}.{what}.{why}
```

Where:
- `prefix` - Usually "audit"
- `where` - Service name from `audit_event.where`
- `what` - Entity name from `audit_event.what`
- `why` - Event name from `audit_event.why`

### Example Routing Keys

```
audit.order_service.order.created
audit.order_service.order.updated
audit.user_service.user.deleted
audit.payment_service.payment.processed
```

## Integration with AioPika

The audit service uses AioPika publishers:

```python
from fastapi_factory_utilities.core.plugins.aiopika import (
    AbstractPublisher,
    Exchange,
)

# Setup publisher
exchange = Exchange(...)
publisher = MyPublisher(exchange=exchange)
await publisher.setup()

# Create audit service
audit_service = OrderAuditService(
    sender=ServiceName("order_service"),
    publisher=publisher,
)
```

## Error Handling

The service raises `AuditServiceError` on publishing failures:

```python
from fastapi_factory_utilities.core.services.audit.exceptions import AuditServiceError

try:
    await audit_service.publish(audit_event)
except AuditServiceError as e:
    # Handle audit publishing failure
    logger.error("Failed to publish audit event", error=e)
```

## Best Practices

1. **Consistent Naming**: Use consistent entity and event names
2. **Timestamps**: Always use UTC timestamps
3. **Actor Information**: Include all relevant actor context
4. **Routing Keys**: Follow the standard routing key pattern
5. **Error Handling**: Handle publishing failures gracefully
6. **Idempotency**: Design audit events to be idempotent

## Reference

- `src/fastapi_factory_utilities/core/services/audit/` - Audit service implementation
- `src/fastapi_factory_utilities/core/services/audit/services.py` - AbstractAuditPublisherService
- `src/fastapi_factory_utilities/core/services/audit/objects.py` - AuditEventObject, AuditableEntity
