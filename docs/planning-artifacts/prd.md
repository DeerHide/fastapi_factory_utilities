---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
inputDocuments:
  - docs/knowledge/index.md
  - docs/knowledge/project-overview.md
  - docs/knowledge/architecture.md
  - docs/knowledge/source-tree-analysis.md
  - docs/knowledge/development-guide.md
documentCounts:
  briefs: 0
  research: 0
  brainstorming: 0
  projectDocs: 5
workflowType: 'prd'
lastStep: 11
workflowComplete: true
completedAt: "2026-01-11"
projectType: brownfield
classification:
  technicalType: developer_tool
  domain: general
  complexity: low
skippedSteps:
  - step: 5
    reason: "Domain complexity is low - no special domain requirements"
  - step: 6
    reason: "No strong innovation signals detected"
---

# Product Requirements Document - fastapi_factory_utilities

**Author:** Operator
**Date:** 2026-01-11

## Executive Summary

**fastapi_factory_utilities** is an open-source Python library that provides a production-ready foundation for building FastAPI microservices. Rather than requiring developers to manually wire up common infrastructure concerns, the library offers a composable plugin architecture with pre-built integrations for databases, message queues, task processing, and observability.

### Vision

Enable Python developers to go from zero to production-ready microservice in minutes, not days, by eliminating boilerplate while preserving flexibility through a plugin-based architecture.

### Target Users

- **Primary:** Python developers building microservices who want production-ready infrastructure without the setup overhead
- **Current Usage:** Open source project on PyPI, actively used by the maintainer in personal projects
- **Skill Level:** Intermediate to advanced Python developers familiar with FastAPI

### Problem Statement

Building a production-ready FastAPI microservice requires wiring up numerous infrastructure concerns:
- Database connectivity and ODM setup (MongoDB/Beanie)
- Message queue integration (RabbitMQ)
- Background task processing (Redis/Taskiq)
- Distributed tracing and metrics (OpenTelemetry)
- Health checks and readiness probes
- Configuration management
- Structured logging
- Authentication (JWT, Ory integration)

Each of these requires significant boilerplate code and expertise to implement correctly. Developers often reinvent the wheel or skip critical production concerns.

### What Makes This Special

> *"Zero-to-production microservice infrastructure in minutes, not days. All the boring but critical stuff (observability, health checks, message queues, database) pre-wired with best practices."*

**Key Differentiators:**
1. **Plugin Architecture:** Mix and match only what you need (ODM, OpenTelemetry, Taskiq, Aiopika, AioHttp)
2. **Clean Architecture:** Dependency injection and separation of concerns built-in
3. **Observable by Default:** OpenTelemetry instrumentation across all components
4. **Type-Safe:** Full type annotations with mypy strict mode support
5. **Testable:** In-memory repository mockers and HTTP client mockers included

## Project Classification

| Property | Value |
|----------|-------|
| **Technical Type** | Developer Tool (Library/Framework) |
| **Domain** | General (Developer Tooling) |
| **Complexity** | Low |
| **Project Context** | Retrospective PRD - documenting existing system |
| **Distribution** | Open Source (MIT License, PyPI) |
| **Status** | Alpha |

**Existing Architecture:**
- Plugin-based architecture with `PluginAbstract` base class
- Application framework with `ApplicationAbstract` and builder pattern
- Type-safe configuration via Pydantic models
- Reactive health monitoring with `StatusService`

## Success Criteria

### User Success

**Developer Experience:**
- Developers can create a new production-ready microservice by extending `ApplicationAbstract` in minutes
- Technical integrations (MongoDB, RabbitMQ, Redis, OpenTelemetry) work out of the box
- Consistent patterns across multiple microservices - same configuration structure, same observability, same health checks
- Developers spend time on business features, not infrastructure plumbing

**The "Aha!" Moment:**
- When a developer realizes they have distributed tracing across services without writing instrumentation code
- When adding a 5th microservice takes the same effort as the 1st one
- When health checks, readiness probes, and observability "just work"

### Business Success

**Primary (Personal Productivity):**
- Significant time savings on maintenance across personal projects
- New microservices are "ready to develop features" immediately
- Technical debt reduced by using consistent, tested patterns

**Secondary (Community Value):**
- Library available on PyPI for others facing similar challenges
- Documentation sufficient for developers to adopt independently
- Solving a real problem that others encounter

### Technical Success

| Metric | Target |
|--------|--------|
| **Test Coverage** | Comprehensive unit and integration tests |
| **Type Safety** | mypy strict mode passing |
| **Compatibility** | Works with latest FastAPI, Pydantic v2 |
| **CI/CD** | All checks pass on every commit |
| **API Stability** | Breaking changes documented, migration paths provided |

### Measurable Outcomes

- Time to create new microservice: Minutes, not days
- Infrastructure code per service: Minimal (extend base classes, configure plugins)
- Maintenance burden: Shared across all services using the library

## Product Scope

### Current State (MVP - Implemented)

**Core Framework:**
- `ApplicationAbstract` - Base class for all microservices
- `ApplicationGenericBuilder` - Builder pattern for app construction
- `RootConfig` - Type-safe YAML configuration with Pydantic

**Plugins (5 available):**
- `ODMPlugin` - MongoDB/Beanie integration
- `OpenTelemetryPlugin` - Distributed tracing and metrics
- `TaskiqPlugin` - Background task processing (Redis)
- `AiopikaPlugin` - RabbitMQ messaging
- `AioHttpPlugin` - Instrumented HTTP client

**Services:**
- `StatusService` - Reactive health and readiness monitoring
- `KratosService` / `HydraService` - Ory identity integration
- `AuditService` - Event auditing

**Security:**
- JWT authentication with JWK store
- Ory Kratos/Hydra integration

**Developer Experience:**
- In-memory repository mockers for testing
- HTTP client mockers for testing
- Example application demonstrating usage

### Growth (Need-Driven)

New plugins and capabilities will be added based on real needs encountered during usage:
- Additional database plugins (PostgreSQL, Redis as primary store)
- Additional message broker plugins (Kafka, NATS)
- Additional auth providers
- CLI tooling for scaffolding

### Vision (Evolutionary)

The library will evolve organically based on usage patterns:
- Design improvements informed by real-world experience
- Community contributions if adoption grows
- Stable API with careful evolution

## User Journeys

### Journey 1: Alex - Starting a New Microservice

Alex is a backend developer who needs to build a new user authentication service for a side project. He's built FastAPI services before, but every time he starts fresh, he spends days wiring up MongoDB, setting up OpenTelemetry, configuring health checks, and writing the same boilerplate configuration code. It's tedious, error-prone, and takes time away from the actual feature work.

This time, Alex discovers `fastapi_factory_utilities` and decides to give it a try. He installs it with `poetry add fastapi-factory-utilities`, looks at the example application, and within 30 minutes has a working service structure. He creates a new class extending `ApplicationAbstract`, defines his document models extending `BaseDocument`, and configures his plugins in `application.yaml`.

The breakthrough moment comes when he runs the service and opens his observability dashboard - distributed traces are already flowing, health endpoints respond correctly, and his MongoDB connection is properly managed with automatic reconnection. What used to take him 2-3 days of setup now took an afternoon.

**Requirements Revealed:**
- Clear example application to learn from
- Simple extension pattern (`ApplicationAbstract`)
- YAML-based configuration
- Working observability out of the box
- Health checks without manual setup

---

### Journey 2: Alex - Adding the Third Service

Three months later, Alex's project has grown. He now has the auth service running smoothly, and he needs to add an order processing service and a notification service. In the past, this would mean copying boilerplate, adjusting configurations, and hoping he didn't miss anything critical.

With `fastapi_factory_utilities`, Alex creates a new package, extends `ApplicationAbstract` again, and defines his order-specific document models. He enables the `AiopikaPlugin` for RabbitMQ messaging (the auth service didn't need it) and keeps the same ODM and OpenTelemetry plugins. The configuration structure is identical - only the service name, port, and business logic differ.

When he deploys the third service, all three services report to the same observability backend. He can trace a request from the API gateway through auth, into orders, and out to notifications. The consistency across services means debugging is straightforward - he knows exactly where to look regardless of which service has an issue.

**Requirements Revealed:**
- Consistent patterns across services
- Composable plugins (enable only what you need)
- Shared observability across service fleet
- Predictable configuration structure
- Easy to add/remove plugins per service

---

### Journey 3: Alex - Debugging a Production Issue

It's 2 AM and Alex gets an alert - the order service is returning 500 errors intermittently. In his pre-library days, this would mean SSH-ing into servers, grep-ing through logs, and guessing at the cause.

Now, Alex opens his Grafana dashboard and sees the `StatusService` reporting the MongoDB connection as "degraded." He clicks into the OpenTelemetry traces and sees that some MongoDB operations are timing out. The structured logs from `structlog` show the exact query that's failing and the retry attempts.

The issue turns out to be a network hiccup between the service and MongoDB. The library's automatic health status updates had already triggered a Kubernetes probe failure, and the orchestrator was restarting affected pods. By the time Alex finishes investigating, the system has self-healed. He adds a custom health check for this edge case and goes back to sleep.

**Requirements Revealed:**
- Reactive health monitoring (`StatusService`)
- Integration with orchestrator probes
- Structured logging with context
- OpenTelemetry traces for debugging
- Automatic status reporting for infrastructure issues

---

### Journey 4: Community Developer - Contributing a Plugin

Jordan discovers `fastapi_factory_utilities` while looking for a FastAPI starter kit. They like the architecture but need PostgreSQL instead of MongoDB. Looking at the existing `ODMPlugin`, Jordan sees the clear `PluginAbstract` interface and decides to contribute a SQLAlchemy plugin.

Jordan forks the repo, follows the development guide to set up the environment, and implements `SQLAlchemyPlugin` following the same patterns as `ODMPlugin`. The test structure is clear - they create unit tests with mocked connections and integration tests using testcontainers. The PR includes documentation and an updated example.

**Requirements Revealed:**
- Clear plugin extension pattern
- Good documentation for contributors
- Test patterns to follow
- Example code to reference

---

## Journey Requirements Summary

| Journey | Key Capabilities Required |
|---------|--------------------------|
| **New Project** | Example app, ApplicationAbstract, YAML config, auto-observability, health checks |
| **Fleet Scaling** | Consistent patterns, composable plugins, shared observability, predictable config |
| **Debugging** | StatusService, structured logging, OpenTelemetry traces, orchestrator integration |
| **Contributing** | PluginAbstract interface, dev guide, test patterns, example code |

### Core Library Capabilities (Validated by Journeys)

1. **Application Framework** - `ApplicationAbstract` + builder pattern
2. **Plugin System** - Composable, optional, clear interface
3. **Configuration** - YAML-based, type-safe, consistent structure
4. **Observability** - OpenTelemetry auto-instrumentation
5. **Health Monitoring** - Reactive `StatusService` with component tracking
6. **Developer Experience** - Example app, mockers, documentation

## Developer Tool Specific Requirements

### Project-Type Overview

`fastapi_factory_utilities` is a Python library distributed via PyPI, designed for Python developers building FastAPI-based microservices. It follows standard Python library conventions with full type annotation support.

### Language & Runtime Support

| Requirement | Current State |
|-------------|---------------|
| **Python Version** | >= 3.12 (required) |
| **Type Hints** | Full annotations, mypy strict mode |
| **Async Support** | Native async/await throughout |
| **Type Marker** | `py.typed` included for PEP 561 compliance |

### Installation Methods

| Method | Command | Notes |
|--------|---------|-------|
| **PyPI (pip)** | `pip install fastapi-factory-utilities` | Production install |
| **Poetry** | `poetry add fastapi-factory-utilities` | Recommended for projects |
| **Development** | `poetry install --with test` | Full dev environment |

**Package Sources:**
- Primary: PyPI (public)
- Secondary: Custom index at `pypi.velmios.io` (for `taskiq-dependencies`)

### API Surface

**Core Public API:**

| Component | Import Path | Purpose |
|-----------|-------------|---------|
| `ApplicationAbstract` | `fastapi_factory_utilities.core.app` | Base class for microservices |
| `ApplicationGenericBuilder` | `fastapi_factory_utilities.core.app` | Builder pattern for apps |
| `RootConfig` | `fastapi_factory_utilities.core.app` | Base configuration class |
| `PluginAbstract` | `fastapi_factory_utilities.core.plugins` | Base class for plugins |

**Plugins:**

| Plugin | Import Path | Purpose |
|--------|-------------|---------|
| `ODMPlugin` | `fastapi_factory_utilities.core.plugins.odm_plugin` | MongoDB/Beanie |
| `OpenTelemetryPlugin` | `fastapi_factory_utilities.core.plugins.opentelemetry_plugin` | Tracing/Metrics |
| `TaskiqPlugin` | `fastapi_factory_utilities.core.plugins.taskiq_plugins` | Background tasks |
| `AiopikaPlugin` | `fastapi_factory_utilities.core.plugins.aiopika` | RabbitMQ |
| `AioHttpPlugin` | `fastapi_factory_utilities.core.plugins.aiohttp` | HTTP client |

**Services:**

| Service | Import Path | Purpose |
|---------|-------------|---------|
| `StatusService` | `fastapi_factory_utilities.core.services.status` | Health monitoring |
| `JWTAuthenticationService` | `fastapi_factory_utilities.core.security.jwt` | JWT auth |

### Documentation

| Type | Location | Status |
|------|----------|--------|
| **README** | `README.md` | ✅ Comprehensive quick-start |
| **Architecture** | `docs/knowledge/architecture.md` | ✅ Generated |
| **Development Guide** | `docs/knowledge/development-guide.md` | ✅ Generated |
| **API Reference** | - | ❌ Not yet generated |
| **Inline Docstrings** | Source code | ✅ Google-style docstrings |

### Code Examples

| Example | Location | Purpose |
|---------|----------|---------|
| **Full Example App** | `src/fastapi_factory_utilities/example/` | Complete working microservice |
| **Books API** | `example/api/books/` | CRUD endpoint example |
| **Document Models** | `example/models/books/` | Beanie document example |
| **Configuration** | `example/application.yaml` | YAML config example |

### Testing Utilities

**Provided Mockers for Consumer Testing:**

| Mocker | Import Path | Purpose |
|--------|-------------|---------|
| `AbstractRepositoryInMemory` | `core.plugins.odm_plugin.mockers` | In-memory repository |
| `build_mocked_aiohttp_response` | `core.plugins.aiohttp.mockers` | Mock HTTP responses |
| `build_mocked_aiohttp_resource` | `core.plugins.aiohttp.mockers` | Mock HTTP resources |

### Migration & Versioning

| Aspect | Approach |
|--------|----------|
| **Version Scheme** | Semantic versioning via git tags |
| **Dynamic Versioning** | `poetry-dynamic-versioning` plugin |
| **Breaking Changes** | Documented in release notes |
| **Migration Guide** | To be created as API stabilizes |
| **Current Status** | Alpha - API may change |

### IDE Support

| IDE Feature | Support |
|-------------|---------|
| **Type Checking** | ✅ Full mypy strict compatibility |
| **Autocompletion** | ✅ Via type annotations |
| **PEP 561** | ✅ `py.typed` marker included |
| **Editor Config** | Standard Python tooling (ruff, black) |

### Implementation Considerations

**For Library Consumers:**
1. Extend `ApplicationAbstract` for your microservice
2. Define document models extending `BaseDocument`
3. Configure plugins in `application.yaml`
4. Use provided mockers for unit testing

**For Library Contributors:**
1. Follow existing plugin patterns (`PluginAbstract`)
2. Add tests using testcontainers for integrations
3. Maintain mypy strict compatibility
4. Use Google-style docstrings

## Project Scoping & Phased Development

### MVP Philosophy: Platform MVP

**Approach:** Build a solid foundation (application framework + plugin system) that enables future expansion without requiring rewrites.

**Why This Approach:**
- Plugins are self-contained - can add/remove without breaking existing consumers
- Core patterns (ApplicationAbstract, PluginAbstract) are stable
- New capabilities = new plugins, not core changes

### Current State (MVP - Implemented)

**Core Framework:**
- ✅ `ApplicationAbstract` - Extensible base class
- ✅ `ApplicationGenericBuilder` - Builder pattern
- ✅ `RootConfig` - Type-safe YAML configuration
- ✅ `StatusService` - Reactive health monitoring

**Plugins (5):**
- ✅ `ODMPlugin` - MongoDB/Beanie
- ✅ `OpenTelemetryPlugin` - Distributed tracing
- ✅ `TaskiqPlugin` - Background tasks (Redis)
- ✅ `AiopikaPlugin` - RabbitMQ messaging
- ✅ `AioHttpPlugin` - Instrumented HTTP client

**Security:**
- ✅ JWT authentication with JWK store
- ✅ Ory Kratos/Hydra integration

**Developer Experience:**
- ✅ Full example application
- ✅ In-memory repository mockers
- ✅ HTTP client mockers
- ✅ Comprehensive type annotations

### Growth Phase (Need-Driven)

**Potential Additions (when real need arises):**

| Category | Possibilities | Trigger |
|----------|---------------|---------|
| **Databases** | PostgreSQL/SQLAlchemy plugin | Project requiring SQL |
| **Message Brokers** | Kafka, NATS plugins | Scale requirements |
| **Auth Providers** | Auth0, Keycloak plugins | Project requirements |
| **Caching** | Redis cache plugin | Performance needs |
| **CLI** | Scaffolding tool | Multiple new projects |

**Growth Principle:** Don't add until there's a real project that needs it.

### Vision Phase (Evolutionary)

**Long-term Possibilities:**
- Community-contributed plugins
- Stable API with versioned migration guides
- Broader ecosystem integration
- Template repository for quick starts

**Vision Principle:** Let usage patterns guide evolution.

### Risk Assessment

| Risk Type | Risk | Mitigation |
|-----------|------|------------|
| **Technical** | Breaking changes as API stabilizes | Semantic versioning, deprecation warnings |
| **Maintenance** | Plugin updates for dependency changes | Pin versions, integration tests |
| **Adoption** | Limited discoverability | README quality, PyPI metadata |
| **Scope Creep** | Adding features "just in case" | Need-driven growth policy |

### Resource Reality

**Current:** Solo maintainer (you)

**Implication:**
- Keep scope lean
- Don't add features speculatively
- Prioritize stability over features
- Documentation as force multiplier

## Functional Requirements

### Application Framework

- FR1: Developers can create a new microservice by extending `ApplicationAbstract`
- FR2: Developers can construct applications using the builder pattern via `ApplicationGenericBuilder`
- FR3: Applications can define custom startup logic by overriding `on_startup()`
- FR4: Applications can define custom shutdown logic by overriding `on_shutdown()`
- FR5: Applications can access FastAPI instance for custom route registration
- FR6: Applications can define dependency injection configuration via `DependencyConfig`

### Configuration Management

- FR7: Developers can configure applications using YAML configuration files
- FR8: Configuration can be validated at startup using Pydantic models
- FR9: Developers can extend `RootConfig` to define custom configuration sections
- FR10: Configuration values can be overridden via environment variables
- FR11: Applications can load configuration from a specified file path

### Plugin System

- FR12: Developers can add plugins to applications via the builder pattern
- FR13: Developers can create custom plugins by extending `PluginAbstract`
- FR14: Plugins can define their own setup and shutdown lifecycle methods
- FR15: Plugins can access application configuration during setup
- FR16: Applications can selectively enable/disable plugins per deployment

### Database Integration (ODMPlugin)

- FR17: Applications can connect to MongoDB using the ODMPlugin
- FR18: Developers can define document models extending `BaseDocument`
- FR19: Developers can implement repositories using `AbstractRepository`
- FR20: Repositories can perform CRUD operations on MongoDB collections
- FR21: Database connections are automatically managed during application lifecycle

### Message Queue Integration (AiopikaPlugin)

- FR22: Applications can connect to RabbitMQ using the AiopikaPlugin
- FR23: Applications can publish messages to RabbitMQ exchanges
- FR24: Applications can consume messages from RabbitMQ queues
- FR25: Message queue connections are automatically managed during application lifecycle

### Background Tasks (TaskiqPlugin)

- FR26: Applications can schedule background tasks using the TaskiqPlugin
- FR27: Background tasks can be distributed across worker processes
- FR28: Task state is persisted in Redis
- FR29: Developers can define task functions with automatic retry logic

### HTTP Client (AioHttpPlugin)

- FR30: Applications can make outbound HTTP requests using the AioHttpPlugin
- FR31: HTTP requests are automatically instrumented with OpenTelemetry traces
- FR32: HTTP client resources can be injected into services via dependency injection

### Observability (OpenTelemetryPlugin)

- FR33: Applications can export distributed traces using the OpenTelemetryPlugin
- FR34: Traces automatically propagate across service boundaries
- FR35: Applications can export metrics to OpenTelemetry collectors
- FR36: All plugin operations are automatically instrumented
- FR37: Structured logging integrates with trace context

### Health Monitoring

- FR38: Applications expose health check endpoints via `StatusService`
- FR39: Component health status can be reported as healthy, degraded, or unhealthy
- FR40: Health status updates trigger reactive notifications
- FR41: Applications expose readiness probe endpoints for orchestrators
- FR42: Applications expose liveness probe endpoints for orchestrators

### Security

- FR43: Applications can authenticate requests using JWT tokens
- FR44: JWT validation supports JWK (JSON Web Key) stores
- FR45: Applications can integrate with Ory Kratos for identity management
- FR46: Applications can integrate with Ory Hydra for OAuth2/OIDC

### Developer Experience

- FR47: Developers can use in-memory repository implementations for unit testing
- FR48: Developers can mock HTTP client responses for unit testing
- FR49: An example application demonstrates library usage patterns
- FR50: Library exports type stubs for IDE autocompletion

## Non-Functional Requirements

### Code Quality & Maintainability

- NFR1: Library maintains mypy strict mode compliance with zero type errors
- NFR2: All public APIs have Google-style docstrings
- NFR3: Test coverage targets comprehensive unit and integration tests
- NFR4: Code formatting follows ruff and black configuration
- NFR5: All CI checks pass on every commit to main branch

### Compatibility

- NFR6: Library supports Python >= 3.12
- NFR7: Library is compatible with FastAPI >= 0.115.13 and Pydantic v2
- NFR8: Library is installable via pip from PyPI
- NFR9: Library provides `py.typed` marker for PEP 561 compliance
- NFR10: Breaking changes follow semantic versioning with migration documentation

### Reliability

- NFR11: Plugin setup/shutdown failures are handled gracefully with clear error messages
- NFR12: Database connection failures trigger health status updates (not crashes)
- NFR13: Message queue connection failures trigger automatic reconnection attempts
- NFR14: All async operations include proper exception handling and cleanup

### Security

- NFR15: JWT tokens are validated against cryptographic signatures
- NFR16: No secrets or credentials are logged in any log level
- NFR17: Dependencies are scanned for known vulnerabilities in CI
- NFR18: Security-sensitive configuration supports environment variable injection

### Integration Quality

- NFR19: All external integrations (MongoDB, RabbitMQ, Redis) use testcontainers for integration tests
- NFR20: OpenTelemetry instrumentation adds < 5% overhead to operations
- NFR21: Plugin integrations support graceful degradation when backends unavailable
- NFR22: HTTP client responses include timeout and retry configuration

### Developer Experience

- NFR23: Library can be installed and example app running in < 5 minutes
- NFR24: Error messages include actionable guidance for common mistakes
- NFR25: Breaking changes are announced with deprecation warnings before removal
- NFR26: Example application demonstrates all core library capabilities
