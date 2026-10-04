# FastAPI Factory Utilities - Project Overview

**Generated:** 2026-01-11 | **Scan Level:** Exhaustive

---

## Executive Summary

**FastAPI Factory Utilities** is a comprehensive Python library designed to accelerate the development of production-ready microservices. It provides a plugin-based architecture that consolidates common patterns for building modern Python applications with FastAPI, featuring built-in support for:

- **Database Operations** via Beanie ODM (MongoDB)
- **Object Storage** via S3Plugin (MinIO / S3)
- **Cache / keys** via RedisPlugin (separate from Taskiq)
- **Message Queuing** via AioPika (RabbitMQ)
- **Task Processing** via Taskiq (Redis)
- **Observability** via OpenTelemetry
- **Security** via JWT authentication and Ory integration

---

## Project Identity

| Property | Value |
|----------|-------|
| **Name** | fastapi_factory_utilities |
| **Type** | Python Library |
| **License** | MIT |
| **Status** | Production/Stable |
| **Python Version** | See `pyproject.toml` |
| **Repository** | https://github.com/DeerHide/fastapi_factory_utilities |
| **PyPI** | https://pypi.org/project/fastapi-factory-utilities/ |

---

## Technology Stack Summary

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Web Framework** | FastAPI | see `pyproject.toml` (`>=0.115.13`) | REST API framework |
| **Data Validation** | Pydantic | ^2.8.2 | Type-safe data models |
| **ODM** | Beanie | ^2.0.0 (extra `mongo`) | MongoDB async ODM |
| **Message Broker** | AioPika | ^9.5.7 (extra `amqp`) | RabbitMQ client |
| **Object Storage** | aioboto3 | extra `s3` | MinIO / S3 |
| **Cache / keys** | Redis | extra `redis` | Standalone `RedisPlugin` |
| **Task Queue** | Taskiq | extra `taskiq` | Distributed task processing |
| **Observability** | OpenTelemetry | API `^1.45.0`, instrumentation `>=0.66b0,<1` | Distributed tracing & metrics |
| **Logging** | Structlog | `>=26.1.0,<27.0` | Structured logging |
| **HTTP Client** | aiohttp | ^3.12.13 | Async HTTP operations |
| **Package Manager** | Poetry | - | Dependency management |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    ApplicationGenericBuilder                     │
│                    (builds and configures)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ApplicationAbstract                          │
│              (your microservice extends this)                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Instance                      │   │
│  │              (auto-configured with CORS, etc.)           │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   ODM Plugin    │  │  OpenTelemetry  │  │  Taskiq Plugin  │
│   (MongoDB)     │  │     Plugin      │  │  (task queue)   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
          │                   │                   │
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  AioPika Plugin │  │  S3 / Redis     │  │ Status Service  │
│   (RabbitMQ)    │  │  Plugins        │  │ (Health Check)  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Repository Structure

```
fastapi_factory_utilities/
├── src/
│   └── fastapi_factory_utilities/
│       ├── core/               # 🎯 MAIN LIBRARY CODE
│       │   ├── app/            # Application framework
│       │   ├── plugins/        # Plugin implementations
│       │   ├── security/       # Authentication/authorization
│       │   ├── services/       # Business services
│       │   ├── api/            # Core API endpoints
│       │   └── utils/          # Utility functions
│       └── example/            # 📚 Usage example
├── tests/                      # Test suite
│   ├── units/                  # Unit tests
│   ├── integrations/           # Integration tests
│   └── fixtures/               # Test fixtures
├── docker/                     # Docker configurations
├── helm/                       # Kubernetes Helm charts
├── docs/                       # Documentation
└── scripts/                    # Development scripts
```

---

## Core Components

### 1. Application Framework (`core/app/`)
- `ApplicationAbstract` - Base class for microservices
- `ApplicationGenericBuilder` - Builder pattern for app construction
- `RootConfig` - Type-safe configuration management

### 2. Plugins (`core/plugins/`)
- `ODMPlugin` - MongoDB integration with Beanie
- `OpenTelemetryPlugin` - Distributed tracing and metrics
- `TaskiqPlugin` - Background task processing
- `AiopikaPlugin` - RabbitMQ messaging
- `AioHttpPlugin` - Instrumented HTTP client
- `S3Plugin` - MinIO / S3 via aioboto3
- `RedisPlugin` - Standalone Redis / Valkey client

### 3. Security (`core/security/`)
- JWT Bearer token authentication
- JWK store for key management
- Ory Kratos integration for identity management

### 4. Services (`core/services/`)
- `StatusService` - Health and readiness checks
- `KratosService` - Identity management operations
- `HydraService` - OAuth2/OIDC operations
- `AuditService` - Event auditing

---

## Key Features

### ✅ Plugin Architecture
Composable plugins that can be mixed and matched based on requirements.

### ✅ Configuration Management
YAML-based configuration with Pydantic validation and environment variable support.

### ✅ Observability Built-In
Automatic instrumentation for tracing across all components.

### ✅ Health Monitoring
Reactive status service with component-level health tracking.

### ✅ Clean Architecture
Separation of concerns with abstract base classes and dependency injection.

### ✅ Type Safety
Full type annotations with mypy strict mode support.

---

## Links to Detailed Documentation

- [Architecture Documentation](./architecture.md)
- [Source Tree Analysis](./source-tree-analysis.md)
- [Development Guide](./development-guide.md)

---

## Related External Documentation

- [README.md](../../README.md) - Project introduction and quick start
- [SECURITY.md](../../SECURITY.md) - Security policy

---

*Generated by BMAD Document Project Workflow*
