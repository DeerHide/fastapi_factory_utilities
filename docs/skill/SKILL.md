---
name: fastapi-factory-utilities
description: Build FastAPI microservices with plugins, message brokers, OAuth2/OIDC, OpenTelemetry, and structured logging.
metadata:
  author: Deerhide
  version: 1.0.0
---
# FastAPI Factory Utilities

## When to use this skill?

- Use this skill when building FastAPI microservices with the fastapi_factory_utilities library.
- Use this skill when implementing plugin-based architectures in FastAPI applications.
- Use this skill when setting up OAuth2/OIDC authentication with Hydra or Kratos.
- Use this skill when configuring MongoDB with Beanie ODM in FastAPI applications.
- Use this skill when implementing RabbitMQ message brokers with AioPika.
- Use this skill when setting up background task processing with Taskiq and Redis.
- Use this skill when configuring OpenTelemetry for distributed tracing and metrics.
- Use this skill when implementing structured logging with structlog.
- Use this skill when using dependency injection patterns with FastAPI's Depends system.
- Use this skill when creating mock resources for testing (AioHttp, ODM repositories).
- Use this skill when implementing repository patterns for data access.
- Use this skill when configuring health checks and status services.
- Use this skill when implementing JWT Bearer authentication with JWKS verification.

---

A library for building production-ready FastAPI microservices with plugin-based architecture.

## Quick Start

See [assets/quick_start_example.py](assets/quick_start_example.py) for a minimal application setup.

## Dependency Injection and Testing

The library uses FastAPI's `Depends` for dependency injection. Plugins expose resources via dependency functions (e.g., `AioHttpResourceDepends`, `depends_status_service`, `depends_scheduler_component`).

For testing, several plugins provide mockers to create mock resources:
- **AioHttp**: `build_mocked_aiohttp_resource`, `build_mocked_aiohttp_response` - Mock HTTP clients and responses
- **ODM**: `AbstractRepositoryInMemory` - In-memory repository for unit testing without MongoDB
- See [AioHttp reference](references/aiohttp.md#testing-with-mocks) and [Repository Pattern](references/repository-pattern.md#testing-with-abstractrepositoryinmemory) for detailed mocking examples

## Reference Documentation

### Core

| Reference | Description |
|-----------|-------------|
| [Application Framework](references/application-framework.md) | ApplicationAbstract, builders, plugin lifecycle |
| [Configuration](references/configuration-utilities.md) | YAML loading, environment variables, type-safe config |
| [Logging](references/logging-utilities.md) | Structured logging with structlog |
| [Status Service](references/status-service.md) | Health and readiness monitoring |

### Plugins

| Reference | Description |
|-----------|-------------|
| [ODM Plugin (MongoDB)](references/odm-plugin.md) | MongoDB/Beanie integration, document models |
| [Repository Pattern](references/repository-pattern.md) | Type-safe data access, in-memory testing |
| [AioHttp HTTP Client](references/aiohttp.md) | HTTP client with connection pooling, mocking utilities |
| [AioPika RabbitMQ](references/aiopika.md) | Message publishing and consuming |
| [OpenTelemetry](references/opentelemetry.md) | Distributed tracing and metrics |
| [Taskiq Tasks](references/taskiq.md) | Background task processing with Redis |

### Services

| Reference | Description |
|-----------|-------------|
| [Hydra Service](references/hydra-service.md) | OAuth2 token introspection, JWKS, client credentials |
| [Kratos Service](references/kratos-service.md) | Identity management, session validation |
| [Audit Service](references/audit-service.md) | Event auditing with RabbitMQ |

### Security

| Reference | Description |
|-----------|-------------|
| [JWT Authentication](references/jwt-authentication.md) | JWT Bearer validation, JWKS store, custom verifiers |

### Utilities

| Reference | Description |
|-----------|-------------|
| [Pagination](references/pagination.md) | Type-safe pagination types |
| [Ory Utilities](references/ory-utilities.md) | Ory API pagination helpers |

## Best Practices

1. **Plugin Order** - Load plugins in dependency order (ODM before repositories)
2. **Configuration** - Use YAML files with `${ENV_VAR:default}` syntax
3. **Lifecycle** - Keep `configure()` lightweight, use `on_startup()` for connections
4. **Observability** - Enable OpenTelemetry in production
5. **Logging** - Use JSON mode in production for log aggregation
6. **Testing** - Use mockers from aiohttp plugin for HTTP client tests
