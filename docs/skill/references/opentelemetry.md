# OpenTelemetry Instrumentation

The OpenTelemetry plugin provides automatic instrumentation for distributed tracing and metrics collection.

## When to Use

Use OpenTelemetry plugin when:
- Building distributed microservices that need observability
- Tracing requests across service boundaries
- Collecting metrics for monitoring and alerting
- Debugging performance issues in production
- Implementing distributed tracing with OTLP
- Instrumenting FastAPI, MongoDB, HTTP clients, and message brokers

## OpenTelemetryPlugin

The plugin automatically instruments:
- **FastAPI** - HTTP requests and responses
- **MongoDB** - Database operations (via Beanie)
- **AioHttp** - Outbound HTTP client requests
- **AioPika** - RabbitMQ message publishing and consuming

## Configuration

### OpenTelemetryConfig

```python
class OpenTelemetryConfig(BaseModel):
    activate: bool = False  # Enable/disable OTLP export
    endpoint: Url = "http://localhost:4318"  # Collector endpoint
    protocol: ProtocolEnum | None = None  # otlp_grpc or otlp_http
    timeout: int = 10  # Timeout in seconds
    closing_timeout: int = 10  # Shutdown timeout
    excluded_urls: list[str] = []  # URLs to exclude from tracing
    meter_config: OpenTelemetryMeterConfig | None = None
    tracer_config: OpenTelemetryTracerConfig | None = None
```

### YAML Configuration

```yaml
opentelemetry:
  activate: true
  endpoint: "http://otel-collector:4318"
  protocol: "otlp_http"
  timeout: 10
  closing_timeout: 10
  excluded_urls:
    - "/health"
    - "/metrics"
  meter_config:
    reader_interval_millis: 1000
    reader_timeout_millis: 1000
  tracer_config:
    max_queue_size: 2048
    max_export_batch_size: 512
    schedule_delay_millis: 5000
    export_timeout_millis: 30000
```

## Usage

### Basic Setup

```python
from fastapi_factory_utilities.core.plugins.opentelemetry_plugin import OpenTelemetryPlugin

class MyAppBuilder(ApplicationGenericBuilder[MyApp]):
    def get_default_plugins(self):
        return [
            ODMPlugin(),
            OpenTelemetryPlugin(),  # Add OpenTelemetry
        ]
```

### Accessing Providers

```python
from fastapi import Request, Depends
from fastapi_factory_utilities.core.plugins.opentelemetry_plugin import (
    depends_tracer_provider,
    depends_meter_provider,
)
from opentelemetry.trace import get_tracer

@router.get("/example")
async def example(
    request: Request,
    tracer_provider = Depends(depends_tracer_provider),
):
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("example_operation") as span:
        span.set_attribute("custom.attribute", "value")
        # Your code here
```

## Automatic Instrumentation

### FastAPI

All HTTP requests are automatically traced:
- Request method, path, status code
- Request/response headers
- Duration and timing information

### MongoDB

Database operations are automatically traced:
- Query operations (find, insert, update, delete)
- Query filters and parameters
- Operation duration

### AioHttp

Outbound HTTP requests are automatically traced:
- Request URL, method, status code
- Request/response headers
- Duration and timing

### AioPika

RabbitMQ operations are automatically traced:
- Message publishing
- Message consumption
- Queue operations

## Resource Attributes

The plugin automatically sets resource attributes:
- `service.name` - From application config
- `service.namespace` - From application config
- `service.version` - From application config
- `deployment.environment` - From application config

## Excluded URLs

Configure URLs to exclude from tracing:

```yaml
opentelemetry:
  excluded_urls:
    - "/health"
    - "/metrics"
    - "/readiness"
```

## Protocols

### OTLP HTTP

```yaml
opentelemetry:
  protocol: "otlp_http"
  endpoint: "http://otel-collector:4318"
```

### OTLP gRPC

```yaml
opentelemetry:
  protocol: "otlp_grpc"
  endpoint: "http://otel-collector:4317"
```

## Shutdown

The plugin gracefully shuts down:
1. Flushes pending spans and metrics
2. Waits for exports to complete (up to `closing_timeout`)
3. Shuts down providers

## Error Handling

The OpenTelemetry plugin can encounter errors during initialization, instrumentation, and export.

### Plugin Initialization Errors

```python
from opentelemetry.exceptions import ConfigurationError

try:
    plugin = OpenTelemetryPlugin()
    # Plugin initialization happens in on_load()
except ConfigurationError as e:
    # Handle configuration errors
    logger.error("OpenTelemetry configuration error", error=e)
    raise
except Exception as e:
    # Handle other initialization errors
    logger.error("OpenTelemetry plugin initialization error", error=e)
    raise
```

### Export Errors

```python
# Export errors are handled internally by the plugin
# Failed exports are logged but don't raise exceptions
# to prevent disrupting application operation

# Monitor export failures via logs:
# - Check for "Failed to export" log messages
# - Monitor OTLP endpoint availability
# - Verify network connectivity to collector
```

### Collector Connection Errors

```python
# Connection errors are handled gracefully:
# - Exports are queued and retried
# - Application continues operating even if collector is unavailable
# - Spans/metrics are buffered until connection is restored

# To handle collector unavailability:
# 1. Monitor logs for connection errors
# 2. Set up alerts for export failures
# 3. Ensure collector endpoint is correct in configuration
```

### Instrumentation Errors

```python
# Instrumentation errors are rare but can occur:
# - Automatic instrumentation may fail for certain libraries
# - Manual instrumentation errors should be caught

from opentelemetry.trace import get_tracer

try:
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("operation") as span:
        # Your code
        pass
except Exception as e:
    # Handle instrumentation errors
    logger.warning("OpenTelemetry instrumentation error", error=e)
    # Continue without tracing
```

### Shutdown Errors

```python
# Shutdown errors are handled gracefully:
# - Plugin attempts to flush pending exports
# - Waits up to closing_timeout for exports to complete
# - Logs warnings if shutdown takes longer than expected

# Monitor shutdown:
# - Check for "OpenTelemetry shutdown timeout" warnings
# - Adjust closing_timeout if needed
# - Ensure collector is responsive during shutdown
```

## Best Practices

1. **Enable in Production**: Set `activate: true` in production environments
2. **Configure Endpoint**: Use environment-specific collector endpoints
3. **Exclude Health Checks**: Add health/readiness endpoints to `excluded_urls`
4. **Monitor Performance**: Adjust batch sizes and timeouts based on load
5. **Use Resource Attributes**: Ensure service name, namespace, and version are set

## Reference

- `src/fastapi_factory_utilities/core/plugins/opentelemetry_plugin/` - Plugin implementation
- `src/fastapi_factory_utilities/core/plugins/opentelemetry_plugin/configs.py` - Configuration models
- `src/fastapi_factory_utilities/core/plugins/opentelemetry_plugin/instruments/` - Instrumentation functions
