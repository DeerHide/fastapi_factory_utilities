# FastAPI Factory Utilities - Source Tree Analysis

**Generated:** 2026-01-11 | **Scan Level:** Exhaustive

---

## Complete Directory Structure

```
fastapi_factory_utilities/
│
├── 📁 src/                                    # Source code root
│   └── 📁 fastapi_factory_utilities/          # Main package
│       │
│       ├── 📄 __main__.py                     # CLI entry point
│       ├── 📄 py.typed                        # PEP 561 marker for type hints
│       │
│       ├── 📁 core/                           # 🎯 CORE LIBRARY (main functionality)
│       │   ├── 📄 __init__.py                 # Package init with version
│       │   ├── 📄 exceptions.py               # Base exception hierarchy
│       │   ├── 📄 protocols.py                # Protocol definitions (typing)
│       │   │
│       │   ├── 📁 app/                        # Application Framework
│       │   │   ├── 📄 __init__.py             # Public API exports
│       │   │   ├── 📄 application.py          # ApplicationAbstract base class
│       │   │   ├── 📄 builder.py              # ApplicationGenericBuilder
│       │   │   ├── 📄 config.py               # RootConfig, configuration models
│       │   │   ├── 📄 enums.py                # EnvironmentEnum, etc.
│       │   │   ├── 📄 exceptions.py           # App-specific exceptions
│       │   │   └── 📄 fastapi_builder.py      # FastAPI instance builder
│       │   │
│       │   ├── 📁 plugins/                    # Plugin Implementations
│       │   │   ├── 📄 __init__.py             # Plugin exports
│       │   │   ├── 📄 abstracts.py            # PluginAbstract base class
│       │   │   │
│       │   │   ├── 📁 odm_plugin/             # MongoDB/Beanie ODM Plugin
│       │   │   │   ├── 📄 plugins.py          # ODMPlugin implementation
│       │   │   │   ├── 📄 builder.py          # ODM connection builder
│       │   │   │   ├── 📄 configs.py          # ODMConfig model
│       │   │   │   ├── 📄 documents.py        # BaseDocument class
│       │   │   │   ├── 📄 repositories.py     # AbstractRepository
│       │   │   │   ├── 📄 depends.py          # FastAPI dependencies
│       │   │   │   ├── 📄 helpers.py          # PersistedEntity helper
│       │   │   │   ├── 📄 mockers.py          # Test mocking utilities
│       │   │   │   └── 📄 exceptions.py       # ODM exceptions
│       │   │   │
│       │   │   ├── 📁 opentelemetry_plugin/   # OpenTelemetry Plugin
│       │   │   │   ├── 📄 plugins.py          # OpenTelemetryPlugin
│       │   │   │   ├── 📄 builder.py          # Tracer/Meter provider builder
│       │   │   │   ├── 📄 configs.py          # OpenTelemetryConfig
│       │   │   │   ├── 📄 helpers.py          # OTLP helpers
│       │   │   │   ├── 📄 exceptions.py       # OTel exceptions
│       │   │   │   └── 📁 instruments/        # Auto-instrumentation modules
│       │   │   │
│       │   │   ├── 📁 taskiq_plugins/         # Taskiq Task Queue Plugin
│       │   │   │   ├── 📄 plugin.py           # TaskiqPlugin implementation
│       │   │   │   ├── 📄 schedulers.py       # Task scheduling
│       │   │   │   ├── 📄 depends.py          # FastAPI dependencies
│       │   │   │   └── 📄 exceptions.py       # Taskiq exceptions
│       │   │   │
│       │   │   ├── 📁 aiopika/                # RabbitMQ Plugin
│       │   │   │   ├── 📄 plugins.py          # AiopikaPlugin implementation
│       │   │   │   ├── 📄 abstract.py         # Abstract base classes
│       │   │   │   ├── 📄 exchange.py         # Exchange management
│       │   │   │   ├── 📄 queue.py            # Queue management
│       │   │   │   ├── 📄 message.py          # Message handling
│       │   │   │   ├── 📄 types.py            # Type definitions
│       │   │   │   ├── 📄 depends.py          # FastAPI dependencies
│       │   │   │   ├── 📄 exceptions.py       # Aiopika exceptions
│       │   │   │   ├── 📁 listener/           # Message consumers
│       │   │   │   └── 📁 publisher/          # Message publishers
│       │   │   │
│       │   │   └── 📁 aiohttp/                # HTTP Client Plugin
│       │   │       ├── 📄 plugins.py          # AioHttpPlugin implementation
│       │   │       ├── 📄 builder.py          # Client session builder
│       │   │       ├── 📄 configs.py          # AioHttpConfig
│       │   │       ├── 📄 resources.py        # Resource abstraction
│       │   │       ├── 📄 factories.py        # Resource factories
│       │   │       ├── 📄 constants.py        # Constants
│       │   │       ├── 📄 depends.py          # FastAPI dependencies
│       │   │       ├── 📄 mockers.py          # Test mocking utilities
│       │   │       └── 📄 exceptions.py       # HTTP exceptions
│       │   │
│       │   ├── 📁 security/                   # Security & Authentication
│       │   │   ├── 📄 __init__.py
│       │   │   ├── 📄 abstracts.py            # Security abstracts
│       │   │   ├── 📄 kratos.py               # Ory Kratos integration
│       │   │   │
│       │   │   └── 📁 jwt/                    # JWT Authentication
│       │   │       ├── 📄 __init__.py         # Public API
│       │   │       ├── 📄 services.py         # JWTAuthenticationService
│       │   │       ├── 📄 configs.py          # JWT configuration
│       │   │       ├── 📄 decoders.py         # Token decoders
│       │   │       ├── 📄 verifiers.py        # Token verifiers
│       │   │       ├── 📄 stores.py           # JWK stores
│       │   │       ├── 📄 objects.py          # JWTPayload, etc.
│       │   │       ├── 📄 types.py            # Type aliases
│       │   │       └── 📄 exceptions.py       # JWT exceptions
│       │   │
│       │   ├── 📁 services/                   # Business Services
│       │   │   │
│       │   │   ├── 📁 status/                 # Health & Readiness Service
│       │   │   │   ├── 📄 services.py         # StatusService
│       │   │   │   ├── 📄 enums.py            # HealthStatusEnum, etc.
│       │   │   │   ├── 📄 types.py            # Status types
│       │   │   │   ├── 📄 exceptions.py       # Status exceptions
│       │   │   │   ├── 📄 health_calculator_strategies.py
│       │   │   │   └── 📄 readiness_calculator_strategies.py
│       │   │   │
│       │   │   ├── 📁 kratos/                 # Ory Kratos Service
│       │   │   │   ├── 📄 services.py         # Identity management
│       │   │   │   ├── 📄 objects.py          # Kratos data models
│       │   │   │   ├── 📄 enums.py            # Kratos enums
│       │   │   │   ├── 📄 types.py            # Type definitions
│       │   │   │   └── 📄 exceptions.py       # Kratos exceptions
│       │   │   │
│       │   │   ├── 📁 hydra/                  # Ory Hydra Service
│       │   │   │   ├── 📄 services.py         # OAuth2/OIDC operations
│       │   │   │   ├── 📄 objects.py          # Hydra data models
│       │   │   │   ├── 📄 types.py            # Type definitions
│       │   │   │   └── 📄 exceptions.py       # Hydra exceptions
│       │   │   │
│       │   │   └── 📁 audit/                  # Audit Service
│       │   │       └── ...                    # Event auditing
│       │   │
│       │   ├── 📁 api/                        # Core API Endpoints
│       │   │   ├── 📄 __init__.py
│       │   │   ├── 📄 tags.py                 # OpenAPI tags
│       │   │   └── 📁 v1/                     # API v1 routes
│       │   │
│       │   ├── 📁 utils/                      # Utility Functions
│       │   │   ├── 📄 configs.py              # Config file readers
│       │   │   ├── 📄 log.py                  # Logging setup (structlog)
│       │   │   ├── 📄 uvicorn.py              # Uvicorn utilities
│       │   │   ├── 📄 hypercorn.py            # Hypercorn utilities
│       │   │   ├── 📄 granian.py              # Granian utilities
│       │   │   ├── 📄 yaml_reader.py          # YAML parsing
│       │   │   ├── 📄 importlib.py            # Dynamic imports
│       │   │   ├── 📄 ory.py                  # Ory helpers
│       │   │   ├── 📄 rabbitmq_configs.py     # RabbitMQ config builder
│       │   │   ├── 📄 redis_configs.py        # Redis config builder
│       │   │   └── 📄 status.py               # Status utilities
│       │   │
│       │   └── 📁 tests/                      # In-package test helpers
│       │
│       └── 📁 example/                        # 📚 USAGE EXAMPLE
│           ├── 📄 __init__.py
│           ├── 📄 __main__.py                 # Example entry point
│           ├── 📄 app.py                      # App, AppBuilder classes
│           ├── 📄 application.yaml            # Example configuration
│           ├── 📁 api/                        # Example API routes
│           ├── 📁 models/                     # Example Beanie documents
│           ├── 📁 entities/                   # Example Pydantic entities
│           └── 📁 services/                   # Example services
│
├── 📁 tests/                                  # Test Suite
│   ├── 📄 conftest.py                         # Pytest configuration & fixtures
│   ├── 📁 fixtures/                           # Shared test fixtures
│   │   ├── 📄 mongo.py                        # MongoDB fixtures
│   │   ├── 📄 redis.py                        # Redis fixtures
│   │   ├── 📄 rabbitmq_fixture.py             # RabbitMQ fixtures
│   │   └── 📄 microcks.py                     # API mocking fixtures
│   ├── 📁 units/                              # Unit tests
│   │   └── 📁 fastapi_factory_utilities/      # Mirror of src structure
│   ├── 📁 integrations/                       # Integration tests
│   │   ├── 📁 core/                           # Core integration tests
│   │   └── 📁 example/                        # Example app tests
│   ├── 📁 performance/                        # Performance tests (Locust)
│   └── 📁 portman/                            # API contract tests
│
├── 📁 docker/                                 # Docker Configurations
│   ├── 📄 apt.conf                            # APT configuration
│   ├── 📁 grafana/                            # Grafana dashboards
│   ├── 📁 otel_collector/                     # OpenTelemetry Collector config
│   ├── 📁 prometheus/                         # Prometheus config
│   └── 📁 tempo/                              # Tempo tracing backend config
│
├── 📁 helm/                                   # Kubernetes Helm Charts
│   └── 📁 example/                            # Example app Helm chart
│
├── 📁 scripts/                                # Development Scripts
│   ├── 📄 setup_dev_env.sh                    # Dev environment setup
│   └── 📄 dev-in-container.sh                 # Docker development
│
├── 📁 docs/                                   # Documentation
│   ├── 📁 openapi/                            # OpenAPI specs
│   └── 📁 knowledge/                          # AI-generated docs (this folder)
│
├── 📁 .github/                                # GitHub Configuration
│   ├── 📄 dependabot.yml                      # Dependency updates
│   └── 📁 workflows/
│       └── 📄 ci.yml                          # CI/CD pipeline
│
├── 📄 pyproject.toml                          # Poetry configuration
├── 📄 poetry.lock                             # Dependency lock file
├── 📄 docker-compose.yml                      # Local development services
├── 📄 skaffold.yaml                           # Kubernetes development
├── 📄 pylintrc                                # Pylint configuration
├── 📄 README.md                               # Project documentation
├── 📄 SECURITY.md                             # Security policy
└── 📄 LICENSE                                 # MIT License
```

---

## Critical Directories Explained

### `src/fastapi_factory_utilities/core/` - Main Library

| Directory | Purpose | Key Files |
|-----------|---------|-----------|
| **`app/`** | Application framework - base classes and builders | `application.py`, `builder.py`, `config.py` |
| **`plugins/`** | All plugin implementations | `odm_plugin/`, `opentelemetry_plugin/`, etc. |
| **`security/`** | Authentication and authorization | `jwt/`, `kratos.py` |
| **`services/`** | Business logic services | `status/`, `kratos/`, `hydra/` |
| **`api/`** | Core API endpoints (health, status) | `v1/` |
| **`utils/`** | Helper utilities | `log.py`, `configs.py` |

### `src/fastapi_factory_utilities/example/` - Usage Example

Demonstrates how to:
- Extend `ApplicationAbstract`
- Configure plugins
- Define Beanie documents
- Set up API routes
- Write `application.yaml` configuration

### `tests/` - Test Suite

| Directory | Purpose |
|-----------|---------|
| **`fixtures/`** | Testcontainers for MongoDB, Redis, RabbitMQ |
| **`units/`** | Unit tests (fast, isolated) |
| **`integrations/`** | Integration tests (with real services) |
| **`performance/`** | Load testing with Locust |

---

## Entry Points

| Entry Point | Location | Description |
|-------------|----------|-------------|
| **CLI** | `src/fastapi_factory_utilities/__main__.py` | Package CLI entry |
| **Example App** | `src/fastapi_factory_utilities/example/__main__.py` | Run example app |
| **Script Command** | `pyproject.toml` → `fastapi_factory_utilities-example` | Poetry script |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Poetry config, mypy, ruff, pytest settings |
| `pylintrc` | Pylint configuration |
| `.pre-commit-config.yaml` | Pre-commit hooks |
| `docker-compose.yml` | Local services (MongoDB, OTel Collector) |
| `skaffold.yaml` | Kubernetes development |
| `.github/workflows/ci.yml` | CI/CD pipeline |

---

*Generated by BMAD Document Project Workflow*
