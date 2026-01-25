# Status Service

The StatusService provides reactive health and readiness monitoring for application components.

## When to Use

Use the status service when:
- Implementing health check endpoints for Kubernetes/Docker
- Monitoring component health (database, message broker, etc.)
- Tracking application readiness for load balancers
- Building reactive status monitoring systems
- Implementing component-level health tracking
- Creating health dashboards and monitoring
- Managing application lifecycle status

## StatusService

Tracks component health and readiness status with reactive updates.

### Component Registration

```python
from fastapi_factory_utilities.core.services.status import (
    StatusService,
    ComponentInstanceType,
    ComponentTypeEnum,
)

status_service = StatusService()

# Register a component
component = ComponentInstanceType(
    component_type=ComponentTypeEnum.DATABASE,
    component_name="mongodb",
)
subject = status_service.register_component_instance(component)
```

### Status Updates

```python
from fastapi_factory_utilities.core.services.status import (
    Status,
    HealthStatusEnum,
    ReadinessStatusEnum,
)

# Update component status
subject.on_next(Status(
    health=HealthStatusEnum.HEALTHY,
    readiness=ReadinessStatusEnum.READY,
))
```

### Get Application Status

```python
# Get overall application status
status = status_service.get_status()
# Status(health=HealthStatusEnum.HEALTHY, readiness=ReadinessStatusEnum.READY)

# Get status by component type
status_by_type = status_service.get_components_status_by_type()
# {
#   ComponentTypeEnum.DATABASE: {
#     "mongodb": Status(...),
#   },
#   ComponentTypeEnum.MESSAGE_BROKER: {
#     "rabbitmq": Status(...),
#   },
# }
```

## MonitoredAbstract

Base class for components that need status monitoring.

### Implementation

```python
from fastapi_factory_utilities.core.utils.status import MonitoredAbstract
from fastapi_factory_utilities.core.services.status import (
    ComponentInstanceType,
    ComponentTypeEnum,
    Status,
    HealthStatusEnum,
    ReadinessStatusEnum,
)

class MyService(MonitoredAbstract):
    def __init__(self, status_service: StatusService) -> None:
        super().__init__(
            component_instance=ComponentInstanceType(
                component_type=ComponentTypeEnum.APPLICATION,
                component_name="MyService",
            ),
            status_service=status_service,
        )

    async def connect(self) -> None:
        try:
            # Connection logic
            self.update_monitoring_status(Status(
                health=HealthStatusEnum.HEALTHY,
                readiness=ReadinessStatusEnum.READY,
            ))
        except Exception:
            self.update_monitoring_status(Status(
                health=HealthStatusEnum.UNHEALTHY,
                readiness=ReadinessStatusEnum.NOT_READY,
            ))
```

## Status Types

### HealthStatusEnum

- `HEALTHY` - Component is healthy
- `UNHEALTHY` - Component is unhealthy

### ReadinessStatusEnum

- `READY` - Component is ready to serve traffic
- `NOT_READY` - Component is not ready

### Status

```python
class Status(BaseModel):
    health: HealthStatusEnum
    readiness: ReadinessStatusEnum
```

## Component Types

### ComponentTypeEnum

- `APPLICATION` - Application-level components
- `DATABASE` - Database connections
- `MESSAGE_BROKER` - Message broker connections
- `HTTP_CLIENT` - HTTP client connections
- `CACHE` - Cache connections
- `EXTERNAL_SERVICE` - External service connections

## Status Calculation Strategies

### HealthCalculatorStrategy

Determines overall health from component statuses:

```python
from fastapi_factory_utilities.core.services.status.health_calculator_strategies import (
    HealthSimpleCalculatorStrategy,
)

# Simple strategy: UNHEALTHY if any component is unhealthy
status_service = StatusService(
    health_calculator_strategy=HealthSimpleCalculatorStrategy,
)
```

### ReadinessCalculatorStrategy

Determines overall readiness from component statuses:

```python
from fastapi_factory_utilities.core.services.status.readiness_calculator_strategies import (
    ReadinessSimpleCalculatorStrategy,
)

# Simple strategy: NOT_READY if any component is not ready
status_service = StatusService(
    readiness_calculator_strategy=ReadinessSimpleCalculatorStrategy,
)
```

## Reactive Updates

Status changes trigger reactive events:

```python
from reactivex import Observer

class StatusObserver(Observer[StatusUpdateEvent]):
    def on_next(self, event: StatusUpdateEvent) -> None:
        print(f"Health: {event.health_status}")
        print(f"Readiness: {event.readiness_status}")

observer = StatusObserver()
status_service.subscribe_to_status_updates(observer)
```

## Usage in FastAPI

```python
from fastapi import APIRouter, Depends
from fastapi_factory_utilities.core.app import depends_status_service

router = APIRouter()

@router.get("/health")
async def health(
    status_service = Depends(depends_status_service),
):
    status = status_service.get_status()
    return {
        "health": status.health.value,
        "readiness": status.readiness.value,
    }
```

## Error Handling

Components should update status appropriately on errors:

```python
class DatabaseComponent(MonitoredAbstract):
    async def connect(self) -> None:
        try:
            # Connection logic
            await self.database.ping()
            self.update_monitoring_status(Status(
                health=HealthStatusEnum.HEALTHY,
                readiness=ReadinessStatusEnum.READY,
            ))
        except ConnectionError:
            self.update_monitoring_status(Status(
                health=HealthStatusEnum.UNHEALTHY,
                readiness=ReadinessStatusEnum.NOT_READY,
            ))
        except Exception as e:
            logger.error("Database connection failed", error=e)
            self.update_monitoring_status(Status(
                health=HealthStatusEnum.UNHEALTHY,
                readiness=ReadinessStatusEnum.NOT_READY,
            ))
```

## Best Practices

1. **Register Early**: Register components during application startup
2. **Update Regularly**: Update status when component state changes
3. **Error Handling**: Set unhealthy status on errors
4. **Readiness Checks**: Use readiness for startup/shutdown states
5. **Health Checks**: Use health for ongoing operational status

## Reference

- `src/fastapi_factory_utilities/core/services/status/` - StatusService implementation
- `src/fastapi_factory_utilities/core/utils/status.py` - MonitoredAbstract
