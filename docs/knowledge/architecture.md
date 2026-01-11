# FastAPI Factory Utilities - Architecture Documentation

**Generated:** 2026-01-11 | **Scan Level:** Exhaustive

> **📋 Related Documentation:**
> - **[Architecture Decision Document](../planning-artifacts/architecture.md)** - Formal architectural decisions, patterns, and implementation guidelines for AI agents
> - This document provides technical reference and implementation details

---

## Executive Summary

FastAPI Factory Utilities implements a **Plugin-Based Architecture** built on clean architecture principles. The library provides:

1. **Abstract Application Framework** - Base classes for building microservices
2. **Composable Plugin System** - Mix-and-match capabilities
3. **Type-Safe Configuration** - Pydantic-based configuration management
4. **Reactive Status Monitoring** - Component-level health tracking
5. **Full Observability** - OpenTelemetry integration across all components

---

## Architecture Pattern

### Plugin Architecture with Dependency Injection

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ApplicationGenericBuilder                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  1. Load configuration (YAML → Pydantic RootConfig)             │   │
│  │  2. Initialize FastAPIBuilder                                    │   │
│  │  3. Instantiate ApplicationAbstract subclass                     │   │
│  │  4. Call setup() to wire everything together                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         ApplicationAbstract                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │   RootConfig     │  │   FastAPI App    │  │  Plugin List     │      │
│  │  (immutable)     │  │   (ASGI)         │  │  [ODM, OTel...]  │      │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
│                                                                          │
│  Lifecycle:                                                              │
│  ┌──────────┐    ┌──────────────┐    ┌────────────┐    ┌────────────┐  │
│  │ setup()  │ →  │ load_plugins │ →  │ on_startup │ →  │ on_shutdown│  │
│  └──────────┘    └──────────────┘    └────────────┘    └────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │ PluginA     │ │ PluginB     │ │ PluginC     │
            │ on_load()   │ │ on_load()   │ │ on_load()   │
            │ on_startup()│ │ on_startup()│ │ on_startup()│
            │ on_shutdown │ │ on_shutdown │ │ on_shutdown │
            └─────────────┘ └─────────────┘ └─────────────┘
```

---

## Core Components

### 1. ApplicationAbstract (`core/app/application.py`)

The base class all microservices extend. Provides:

- **Plugin Management** - Register and lifecycle plugins
- **State Management** - Add values to FastAPI app state
- **Lifespan Context** - Async startup/shutdown handling
- **Configuration Access** - Type-safe config retrieval

```python
class ApplicationAbstract(ABC):
    PACKAGE_NAME: ClassVar[str]              # Your package name
    CONFIG_CLASS: ClassVar[type[RootConfig]] # Your config class
    ODM_DOCUMENT_MODELS: ClassVar[list]      # Beanie document models

    @abstractmethod
    def configure(self) -> None: ...         # Add routes, middleware

    @abstractmethod
    async def on_startup(self) -> None: ...  # Custom startup logic

    @abstractmethod
    async def on_shutdown(self) -> None: ... # Custom shutdown logic
```

### 2. ApplicationGenericBuilder (`core/app/builder.py`)

Builder pattern for constructing applications:

```python
class ApplicationGenericBuilder(Generic[T]):
    def add_plugin_to_activate(plugin: PluginAbstract) -> Self
    def add_config(config: RootConfig) -> Self
    def build() -> T                    # Returns configured application
    def build_and_serve() -> None       # Build and start Uvicorn
```

### 3. PluginAbstract (`core/plugins/abstracts.py`)

Base class for all plugins:

```python
class PluginAbstract(ABC):
    def set_application(app: ApplicationAbstractProtocol) -> Self

    @abstractmethod
    def on_load(self) -> None           # Sync initialization

    @abstractmethod
    async def on_startup(self) -> None  # Async initialization

    @abstractmethod
    async def on_shutdown(self) -> None # Cleanup
```

---

## Plugin Architecture

### Available Plugins

| Plugin | Purpose | Dependencies |
|--------|---------|--------------|
| **ODMPlugin** | MongoDB/Beanie ODM | pymongo, beanie |
| **OpenTelemetryPlugin** | Tracing & metrics | opentelemetry-sdk |
| **TaskiqPlugin** | Background tasks | taskiq, redis |
| **AiopikaPlugin** | RabbitMQ messaging | aio-pika |
| **AioHttpPlugin** | HTTP client | aiohttp |

### Plugin Lifecycle

```
Application.setup()
        │
        ▼
┌───────────────────┐
│  plugin.on_load() │  ← Sync initialization (config validation, etc.)
└───────────────────┘
        │
        ▼
Application.startup_plugins() [called from lifespan]
        │
        ▼
┌─────────────────────┐
│ plugin.on_startup() │  ← Async initialization (connect to services)
└─────────────────────┘
        │
        ▼
    [Application Running]
        │
        ▼
Application.shutdown_plugins() [called from lifespan]
        │
        ▼
┌──────────────────────┐
│ plugin.on_shutdown() │  ← Cleanup (close connections)
└──────────────────────┘
```

### Plugin Implementation Example: ODMPlugin

```python
class ODMPlugin(PluginAbstract):
    def on_load(self) -> None:
        # Configure pymongo logger
        # Validate configuration

    async def on_startup(self) -> None:
        # 1. Build MongoDB client using ODMBuilder
        # 2. Connect to database
        # 3. Initialize Beanie with document models
        # 4. Register with StatusService
        # 5. Add client/database to FastAPI state

    async def on_shutdown(self) -> None:
        # Close MongoDB connection
```

---

## Configuration System

### Configuration Hierarchy

```
RootConfig (root)
├── application: BaseApplicationConfig
│   ├── service_namespace: str
│   ├── service_name: str
│   ├── environment: EnvironmentEnum
│   ├── version: str
│   └── description: str
├── server: ServerConfig
│   ├── host: str (default: "0.0.0.0")
│   ├── port: int (default: 8000)
│   └── workers: int (default: 1)
├── cors: CorsConfig
│   ├── allow_origins: list[str]
│   ├── allow_methods: list[str]
│   └── allow_headers: list[str]
├── development: DevelopmentConfig
│   ├── debug: bool
│   └── reload: bool
├── logging: list[LoggingConfig]
└── logging_mode: LogModeEnum
```

### Configuration Loading

1. **YAML File** - `application.yaml` in your package
2. **Pydantic Validation** - Type-safe parsing
3. **Frozen Models** - Immutable after creation (thread-safe)

```python
# GenericConfigBuilder loads config from package
config = GenericConfigBuilder[MyAppConfig](
    package_name="myapp",
    config_class=MyAppConfig,
).build()
```

---

## Exception Architecture

### Exception Hierarchy

```
FastAPIFactoryUtilitiesError (base)
│
├── ConfigBuilderError          # Configuration loading errors
├── OperationError              # Repository operation errors
├── UnableToCreateEntityDueToDuplicateKeyError
│
├── JWTAuthenticationError      # JWT errors
│   ├── InvalidJWTError
│   ├── NotVerifiedJWTError
│   └── MissingJWTCredentialsError
│
├── OpenTelemetryPluginBaseException
│   └── OpenTelemetryPluginConfigError
│
└── AiopikaPluginBaseError      # RabbitMQ errors
```

### Exception Features

All exceptions automatically:
1. **Log themselves** using structlog
2. **Record to OpenTelemetry** spans (if active)
3. **Include context** as span attributes
4. **Support custom log levels** via `DEFAULT_LOGGING_LEVEL`

```python
class FastAPIFactoryUtilitiesError(Exception):
    DEFAULT_LOGGING_LEVEL: int = logging.ERROR
    DEFAULT_MESSAGE: str | None = None

    def __init__(self, *args, **kwargs):
        # Auto-logs and records to OpenTelemetry span
```

---

## Service Layer

### StatusService - Health Monitoring

Reactive health monitoring with component-level tracking:

```
┌──────────────────────────────────────────────────────────────┐
│                       StatusService                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Components Registry                                  │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐       │   │
│  │  │  MongoDB   │ │  RabbitMQ  │ │   Redis    │       │   │
│  │  │  Subject   │ │  Subject   │ │  Subject   │       │   │
│  │  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘       │   │
│  │        │              │              │               │   │
│  │        └──────────────┼──────────────┘               │   │
│  │                       ▼                               │   │
│  │         ┌─────────────────────────┐                  │   │
│  │         │ Health Calculator       │                  │   │
│  │         │ Readiness Calculator    │                  │   │
│  │         └─────────────────────────┘                  │   │
│  │                       │                               │   │
│  │                       ▼                               │   │
│  │         ┌─────────────────────────┐                  │   │
│  │         │ Overall Status Subject  │ ← Reactive!     │   │
│  │         └─────────────────────────┘                  │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

**Usage:**
```python
# Plugin registers with StatusService
subject = status_service.register_component_instance(
    ComponentInstanceType(component_type=ComponentTypeEnum.DATABASE, identifier="MongoDB")
)

# Plugin reports status changes
subject.on_next(Status(health=HealthStatusEnum.HEALTHY, readiness=ReadinessStatusEnum.READY))
```

---

## Security Architecture

### JWT Authentication Flow

```
┌─────────┐     ┌──────────────────────┐     ┌─────────────────┐
│ Request │ →   │ JWTAuthenticationSvc │ →   │ JWKStore        │
│ Bearer  │     │ 1. Extract token     │     │ (key retrieval) │
│ Token   │     │ 2. Verify signature  │     └─────────────────┘
└─────────┘     │ 3. Decode payload    │
                │ 4. Return JWTPayload │
                └──────────────────────┘
                         │
                         ▼
                ┌──────────────────┐
                │ JWTPayload       │
                │ - sub (subject)  │
                │ - iss (issuer)   │
                │ - aud (audience) │
                │ - exp (expiry)   │
                └──────────────────┘
```

### Ory Integration

| Service | Purpose |
|---------|---------|
| **KratosService** | Identity management (users, sessions) |
| **HydraService** | OAuth2/OIDC (tokens, introspection) |

---

## Data Architecture

### Repository Pattern

```python
class AbstractRepository(ABC, Generic[DocumentGenericType, EntityGenericType]):
    """Repository interface for data access."""

    async def insert(entity) -> DocumentGenericType
    async def update(entity) -> DocumentGenericType
    async def get_one_by_id(id) -> DocumentGenericType | None
    async def delete_one_by_id(id) -> None
    async def find(*filters, skip, limit, sort) -> list[DocumentGenericType]
```

### Document Models

All MongoDB documents extend `BaseDocument`:

```python
class BaseDocument(Document):
    """Base document with common fields."""
    id: UUID
    created_at: datetime
    updated_at: datetime
```

---

## Observability Architecture

### OpenTelemetry Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                    OpenTelemetryPlugin                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │ TracerProvider  │  │ MeterProvider   │  │  Instruments   │  │
│  │ (OTLP Export)   │  │ (OTLP Export)   │  │  (Auto-instr.) │  │
│  └────────┬────────┘  └────────┬────────┘  └───────┬────────┘  │
└───────────┼─────────────────────┼──────────────────┼────────────┘
            │                     │                  │
            ▼                     ▼                  ▼
    ┌───────────────────────────────────────────────────────────┐
    │                    Instrumented Components                 │
    │  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────────┐   │
    │  │ FastAPI │ │ MongoDB  │ │ aiohttp │ │   AioPika    │   │
    │  │ (HTTP)  │ │ (pymongo)│ │ (HTTP)  │ │  (RabbitMQ)  │   │
    │  └─────────┘ └──────────┘ └─────────┘ └──────────────┘   │
    └───────────────────────────────────────────────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │   OTLP Collector      │
                │   (gRPC or HTTP)      │
                └───────────────────────┘
```

---

## Deployment Architecture

### Docker Compose (Local Development)

```yaml
services:
  otel_collector:    # OpenTelemetry Collector
  mongo:             # MongoDB
  application:       # Your microservice
```

### Kubernetes (Production)

- Helm charts in `helm/` directory
- Skaffold configuration for development

---

## Design Principles

1. **Plugin Composability** - Add only what you need
2. **Type Safety** - Full type annotations, mypy strict
3. **Async-First** - All I/O is async
4. **Immutable Configuration** - Pydantic frozen models
5. **Observable by Default** - OpenTelemetry built-in
6. **Clean Architecture** - Separation of concerns
7. **Testability** - In-memory repositories, mockers

---

## Extension Points

| Extension Point | How to Extend |
|-----------------|---------------|
| **New Plugin** | Implement `PluginAbstract` |
| **Custom Config** | Extend `RootConfig` |
| **New Repository** | Implement `AbstractRepository` |
| **Custom Health Logic** | Implement `HealthCalculatorStrategy` |
| **New Service** | Add to `core/services/` |

---

## Document Relationship

This technical architecture document complements the **[Architecture Decision Document](../planning-artifacts/architecture.md)**, which contains:

- Formal architectural decisions with rationale
- Implementation patterns and consistency rules
- Complete project structure and boundaries
- Requirements to architecture mapping
- Validation results and implementation readiness

**Use this document for:**
- Understanding how components work together
- Implementation details and code examples
- Technical reference during development

**Use the Architecture Decision Document for:**
- Understanding why architectural decisions were made
- Following implementation patterns for consistency
- AI agent implementation guidance
- Project structure and boundary definitions

---

*Generated by BMAD Document Project Workflow*
