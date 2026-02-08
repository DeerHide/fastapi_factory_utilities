# AioHttp HTTP Client

The AioHttp plugin provides instrumented HTTP client resources with OpenTelemetry integration and connection pooling.

## When to Use

Use AioHttp plugin when:
- Making outbound HTTP requests from FastAPI applications
- Integrating with external services (OAuth providers, APIs, etc.)
- Needing connection pooling for HTTP clients
- Requiring automatic OpenTelemetry instrumentation for HTTP requests
- Managing multiple HTTP service dependencies
- Testing HTTP client interactions with mocks

## AioHttpClientPlugin

The plugin manages multiple HTTP service dependencies with automatic instrumentation.

### Configuration

```python
from fastapi_factory_utilities.core.plugins.aiohttp import AioHttpClientPlugin

# Configure multiple HTTP services
plugin = AioHttpClientPlugin(keys=["hydra_admin", "hydra_public", "kratos_admin"])
```

### YAML Configuration

```yaml
http_service_dependencies:
  hydra_admin:
    base_url: "http://hydra-admin:4445"
    limit: 100
    limit_per_host: 30
    ssl:
      verify: true
      ca_cert_path: "/path/to/ca.crt"
  hydra_public:
    base_url: "http://hydra-public:4444"
    limit: 50
    limit_per_host: 10
```

## AioHttpClientResource

HTTP client resource with connection pooling and instrumentation.

### Access Client Session

```python
from fastapi import Request, Depends
from fastapi_factory_utilities.core.plugins.aiohttp.depends import (
    AioHttpResourceDepends,
)

@router.get("/call-external")
async def call_external(
    request: Request,
    http_client = Depends(AioHttpResourceDepends("hydra_admin")),
):
    async with http_client.acquire_client_session() as session:
        async with session.get("/admin/oauth2/clients") as response:
            data = await response.json()
            return data
```

### Resource Methods

- `acquire_client_session() -> AsyncContextManager[ClientSession]` - Get a client session
- `on_startup()` - Initialize connector and instrumentation
- `on_shutdown()` - Close sessions and connector

## Connection Pooling

The plugin configures TCP connectors with:
- **Connection Limits** - Total and per-host connection limits
- **DNS Caching** - Configurable DNS cache TTL
- **SSL/TLS** - Certificate verification and custom CA certificates

### Configuration Options

```python
class HttpServiceDependencyConfig(BaseModel):
    base_url: str
    limit: int = 100  # Total connection limit
    limit_per_host: int = 30  # Per-host connection limit
    use_dns_cache: bool = True
    ttl_dns_cache: int = 10
    ssl: SSLConfig | None = None
```

## OpenTelemetry Instrumentation

HTTP requests are automatically instrumented:
- Request method, URL, status code
- Request/response headers
- Duration and timing
- Error information

Traces are linked to the active span context.

## SSL/TLS Configuration

### Basic SSL

```yaml
http_service_dependencies:
  secure_service:
    base_url: "https://api.example.com"
    ssl:
      verify: true
```

### Custom CA Certificate

```yaml
http_service_dependencies:
  secure_service:
    base_url: "https://api.example.com"
    ssl:
      verify: true
      ca_cert_path: "/path/to/ca.crt"
```

### Disable SSL Verification

```yaml
http_service_dependencies:
  insecure_service:
    base_url: "https://api.example.com"
    ssl:
      verify: false
```

## Multiple Services

Configure and use multiple HTTP services:

```python
# Plugin setup
plugin = AioHttpClientPlugin(keys=["service1", "service2", "service3"])

# Usage
@router.get("/call-service1")
async def call_service1(
    client1 = Depends(AioHttpResourceDepends("service1")),
):
    async with client1.acquire_client_session() as session:
        # Use service1 client
        pass

@router.get("/call-service2")
async def call_service2(
    client2 = Depends(AioHttpResourceDepends("service2")),
):
    async with client2.acquire_client_session() as session:
        # Use service2 client
        pass
```

## Testing with Mocks

The library provides utilities for mocking AioHttp resources and responses in tests. For services that also use repositories, combine with the [Repository Pattern](repository-pattern.md#testing-with-abstractrepositoryinmemory) in-memory repository for full unit tests without external services.

### build_mocked_aiohttp_response

Creates a mock `aiohttp.ClientResponse` for testing.

#### Basic Usage

```python
from http import HTTPStatus
from fastapi_factory_utilities.core.plugins.aiohttp.mockers import (
    build_mocked_aiohttp_response,
)

# Success response with JSON
response = build_mocked_aiohttp_response(
    status=HTTPStatus.OK,
    json={"message": "Success", "data": {"id": "123"}},
)

assert response.status == HTTPStatus.OK
data = await response.json()
assert data["message"] == "Success"
```

#### Error Response

```python
# Error response that raises on raise_for_status()
response = build_mocked_aiohttp_response(
    status=HTTPStatus.NOT_FOUND,
    json={"error": "Not found"},
    error_message="Resource not found",
)

assert response.status == HTTPStatus.NOT_FOUND
# Raises ClientResponseError
response.raise_for_status()  # Raises aiohttp.ClientResponseError
```

#### Text Response

```python
response = build_mocked_aiohttp_response(
    status=HTTPStatus.OK,
    text="Plain text response",
)

text = await response.text()
assert text == "Plain text response"
```

#### Binary Response

```python
response = build_mocked_aiohttp_response(
    status=HTTPStatus.OK,
    read=b"binary data",
)

data = await response.read()
assert data == b"binary data"
```

#### Headers and Cookies

```python
response = build_mocked_aiohttp_response(
    status=HTTPStatus.OK,
    json={"data": "value"},
    headers={"Content-Type": "application/json", "X-Custom": "header"},
    cookies={"session_id": "abc123", "token": "xyz789"},
)

assert response.headers["Content-Type"] == "application/json"
assert response.cookies["session_id"].value == "abc123"
```

#### Context Manager Support

```python
# Supports both patterns:
# Direct await
response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={})
data = await response.json()

# Context manager
response = build_mocked_aiohttp_response(status=HTTPStatus.OK, json={})
async with response as resp:
    data = await resp.json()
```

### build_mocked_aiohttp_resource

Creates a mock `AioHttpClientResource` for testing services.

#### Basic Usage

```python
from fastapi_factory_utilities.core.plugins.aiohttp.mockers import (
    build_mocked_aiohttp_resource,
    build_mocked_aiohttp_response,
)

# Create mock response
get_response = build_mocked_aiohttp_response(
    status=HTTPStatus.OK,
    json={"message": "Success"},
)

# Create mock resource
resource = build_mocked_aiohttp_resource(get=get_response)

# Use in tests
async with resource.acquire_client_session() as session:
    async with session.get(url="https://api.example.com/data") as response:
        assert response.status == HTTPStatus.OK
        data = await response.json()
        assert data["message"] == "Success"
```

#### Multiple HTTP Methods

```python
get_response = build_mocked_aiohttp_response(
    status=HTTPStatus.OK,
    json={"id": "123"},
)

post_response = build_mocked_aiohttp_response(
    status=HTTPStatus.CREATED,
    json={"id": "456", "created": True},
)

resource = build_mocked_aiohttp_resource(
    get=get_response,
    post=post_response,
)

async with resource.acquire_client_session() as session:
    # GET request
    async with session.get(url="https://api.example.com/items/123") as response:
        data = await response.json()
        assert data["id"] == "123"

    # POST request
    async with session.post(url="https://api.example.com/items", json={}) as response:
        data = await response.json()
        assert data["created"] is True
```

#### Dynamic Responses

Use callables for dynamic responses based on request parameters:

```python
def get_response(url: str, **kwargs: Any) -> aiohttp.ClientResponse:
    if "page=1" in url:
        return build_mocked_aiohttp_response(
            status=HTTPStatus.OK,
            json={"page": 1, "items": [1, 2, 3]},
        )
    elif "page=2" in url:
        return build_mocked_aiohttp_response(
            status=HTTPStatus.OK,
            json={"page": 2, "items": [4, 5, 6]},
        )
    return build_mocked_aiohttp_response(
        status=HTTPStatus.NOT_FOUND,
        json={"error": "Page not found"},
    )

resource = build_mocked_aiohttp_resource(get=get_response)

async with resource.acquire_client_session() as session:
    # First call
    async with session.get(url="https://api.example.com/items?page=1") as response:
        data = await response.json()
        assert data["page"] == 1

    # Second call
    async with session.get(url="https://api.example.com/items?page=2") as response:
        data = await response.json()
        assert data["page"] == 2
```

#### Testing Services

Mock resources can be used to test services that depend on AioHttp:

```python
from fastapi_factory_utilities.core.services.hydra import (
    HydraIntrospectService,
)

# Create mock resource with responses
introspect_response = build_mocked_aiohttp_response(
    status=HTTPStatus.OK,
    json={
        "active": True,
        "scope": "read write",
        "client_id": "client-123",
    },
)

resource = build_mocked_aiohttp_resource(
    post=introspect_response,  # Introspect uses POST
)

# Create service with mock resource
service = HydraIntrospectService(
    hydra_admin_http_resource=resource,
    hydra_public_http_resource=resource,
)

# Test service
introspect = await service.introspect(token="test-token")
        assert introspect.active is True
```

## Error Handling

The AioHttp plugin and resources can encounter various errors that should be handled appropriately.

### HTTP Client Errors

```python
from aiohttp import ClientError, ClientResponseError
from http import HTTPStatus

async with http_client.acquire_client_session() as session:
    try:
        async with session.get("/api/data") as response:
            response.raise_for_status()  # Raises ClientResponseError for 4xx/5xx
            data = await response.json()
    except ClientResponseError as e:
        # Handle HTTP error responses (4xx, 5xx)
        if e.status == HTTPStatus.NOT_FOUND:
            logger.warning("Resource not found", url=e.request_info.url)
        elif e.status == HTTPStatus.UNAUTHORIZED:
            logger.error("Authentication failed", url=e.request_info.url)
        raise
    except ClientError as e:
        # Handle connection errors, timeouts, etc.
        logger.error("HTTP client error", error=e)
        raise
```

### Connection Errors

```python
from aiohttp import ClientConnectorError

try:
    async with http_client.acquire_client_session() as session:
        async with session.get("https://api.example.com/data") as response:
            data = await response.json()
except ClientConnectorError as e:
    # Handle connection failures (DNS, network, etc.)
    logger.error("Connection failed", error=e, host=e.host)
    # Retry logic or fallback
except asyncio.TimeoutError:
    # Handle request timeouts
    logger.error("Request timeout")
    # Retry logic or fallback
```

### SSL/TLS Errors

```python
from aiohttp import ClientSSLError

try:
    async with http_client.acquire_client_session() as session:
        async with session.get("https://api.example.com/data") as response:
            data = await response.json()
except ClientSSLError as e:
    # Handle SSL certificate errors
    logger.error("SSL error", error=e)
    # Check certificate configuration
    raise
```

### Resource Cleanup

The `acquire_client_session()` context manager automatically handles resource cleanup, but errors during shutdown should be handled:

```python
try:
    async with http_client.acquire_client_session() as session:
        # Use session
        pass
except Exception as e:
    # Errors are logged automatically
    # Context manager ensures cleanup
    raise
```

## Best Practices

1. **Connection Pooling**: Configure appropriate limits based on load
2. **SSL Verification**: Always verify SSL in production
3. **Resource Management**: Use `acquire_client_session()` context manager
4. **Error Handling**: Handle HTTP errors appropriately
5. **Timeout Configuration**: Set appropriate timeouts for requests
6. **Instrumentation**: Leverage automatic OpenTelemetry tracing
7. **Testing**: Use mockers for unit and integration tests

## Reference

- `src/fastapi_factory_utilities/core/plugins/aiohttp/` - Plugin implementation
- `src/fastapi_factory_utilities/core/plugins/aiohttp/resources.py` - AioHttpClientResource
- `src/fastapi_factory_utilities/core/plugins/aiohttp/configs.py` - Configuration models
- `src/fastapi_factory_utilities/core/plugins/aiohttp/mockers.py` - Testing utilities
