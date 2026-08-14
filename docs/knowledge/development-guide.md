# FastAPI Factory Utilities - Development Guide

**Generated:** 2026-01-11 | **Scan Level:** Exhaustive

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | >= 3.12 | Required |
| **Poetry** | Latest | Package management |
| **Docker** | Latest | Optional, for local services |
| **Git** | Latest | Version control |

---

## Environment Setup

### 1. Clone the Repository

```bash
git clone https://github.com/DeerHide/fastapi_factory_utilities.git
cd fastapi_factory_utilities
```

### 2. Install Poetry

If not already installed:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 3. Configure Poetry for Local Virtual Environment

```bash
poetry config virtualenvs.in-project true
```

### 4. Install Dependencies

```bash
# Install all dependencies including test group
poetry install --with test --extras all
```

This will:
- Create `.venv/` in the project root
- Install all production dependencies
- Install all test dependencies

### 5. Activate Virtual Environment

```bash
source .venv/bin/activate
```

### 6. Install Pre-commit Hooks

```bash
poetry run pre-commit install
poetry run pre-commit install --hook-type pre-push
```

---

## Quick Start Script

Use the provided setup script:

```bash
./scripts/setup_dev_env.sh
```

---

## Running the Example Application

### Option 1: Direct Run

```bash
poetry run fastapi_factory_utilities-example
```

### Option 2: With Local Services (Docker Compose)

```bash
# Start MongoDB and OpenTelemetry Collector
docker-compose up -d mongo otel_collector

# Run the application
poetry run fastapi_factory_utilities-example
```

The example app will be available at: `http://localhost:8000`

---

## Development Workflow

### Code Formatting

```bash
# Format code with Ruff
poetry run ruff format src tests

# Check and auto-fix linting issues
poetry run ruff check --fix src tests
```

### Type Checking

```bash
# Run mypy in strict mode
poetry run mypy
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html --cov-report=term

# Run specific test file
poetry run pytest tests/units/fastapi_factory_utilities/core/test_exceptions.py

# Run tests in parallel
poetry run pytest -n auto

# Run with verbose output
poetry run pytest -vv
```

### Pre-commit Hooks

```bash
# Run all hooks on all files
poetry run pre-commit run --all-files

# Run specific hook
poetry run pre-commit run ruff-check --all-files
poetry run pre-commit run mypy --all-files
```

---

## Project Structure for Development

```
src/fastapi_factory_utilities/
├── core/                 # Main library code
│   ├── app/              # Extend ApplicationAbstract here
│   ├── plugins/          # Add new plugins here
│   ├── security/         # Security extensions
│   ├── services/         # New services
│   └── utils/            # Utility functions
└── example/              # Reference implementation
```

---

## Adding a New Plugin

### 1. Create Plugin Directory

```bash
mkdir -p src/fastapi_factory_utilities/core/plugins/my_plugin
touch src/fastapi_factory_utilities/core/plugins/my_plugin/__init__.py
touch src/fastapi_factory_utilities/core/plugins/my_plugin/plugins.py
```

### 2. Implement Plugin

```python
# plugins.py
from fastapi_factory_utilities.core.plugins.abstracts import PluginAbstract

class MyPlugin(PluginAbstract):
    """My custom plugin."""

    def on_load(self) -> None:
        """Sync initialization."""
        # Validate configuration
        # Setup logging
        pass

    async def on_startup(self) -> None:
        """Async initialization."""
        # Connect to services
        # Register with StatusService
        pass

    async def on_shutdown(self) -> None:
        """Cleanup."""
        # Close connections
        pass
```

### 3. Export from `__init__.py`

```python
# __init__.py
from .plugins import MyPlugin

__all__ = ["MyPlugin"]
```

### 4. Add Tests

```bash
mkdir -p tests/units/fastapi_factory_utilities/core/plugins/my_plugin
touch tests/units/fastapi_factory_utilities/core/plugins/my_plugin/test_plugins.py
```

---

## Testing Patterns

### Strategy: fake at the driver seam

Prefer doubles from `fastapi_factory_utilities.core.testing` (install
`fastapi_factory_utilities[testing]`). They swap the driver so Beanie /
`AbstractRepository` / `S3BucketResource` / Depends helpers run for real:

| Resource | Double | Notes |
|----------|--------|-------|
| MongoDB | `build_mongomock_database` / `mongomock_database` | mongomock via pymongo-async-mock |
| Redis | `build_fakeredis` / `fakeredis_client` | Drop onto `app.state.redis_client` |
| S3 | `moto_s3_bucket` / `moto_s3_client` | Real botocore semantics |
| Taskiq | `in_memory_scheduler_component` | `taskiq.InMemoryBroker` |
| OTel | `in_memory_otel` | Assertable spans/metrics |
| AMQP | `InMemoryPublisher` + `build_incoming_message` | Record only — no routing/confirms/DLX |
| HTTP | `build_mocked_aiohttp_*` | Unchanged |

**Container-only (do not fake):** Mongo transactions / multi-doc atomicity; all
AMQP broker semantics (topic routing, publisher confirms, consumer acks,
dead-letter / TTL retry). Keep those on the existing testcontainers.

`AbstractRepositoryInMemory` is **deprecated** — it hand-rolls a partial query
engine. Migrate to mongomock so the repository path executes for real.

### Repository contract tests

`RepositoryContract` is a shared suite the library CI runs twice (mongomock +
real Mongo). Divergence fails the build. Downstream services can subclass it:

```python
from fastapi_factory_utilities.core.testing import RepositoryContract
from fastapi_factory_utilities.core.testing.odm import make_contract_entity

class TestMyRepoContract(RepositoryContract):
    @pytest_asyncio.fixture
    async def repository(self, mongomock_odm_database):
        # Or init_beanie with your own documents on mongomock_database / async_motor_database
        ...
        return MyRepository(database=...)

    @pytest.fixture
    def new_entity(self):
        return make_contract_entity  # or your own factory with my_field/category/id
```

### Unit Test Structure

```python
class TestMyFeature:
    """Tests for MyFeature."""

    def test_specific_scenario(self) -> None:
        """Test description."""
        # Arrange
        # Act
        # Assert
```

### Async Test

```python
class TestAsyncFeature:
    """Tests for async features."""

    async def test_async_operation(self) -> None:
        """Test async operation."""
        result = await async_function()
        assert result is not None
```

### Using mongomock-backed repositories

```python
from beanie import init_beanie
from fastapi_factory_utilities.core.testing import build_mongomock_database

async def test_with_mongomock_repo() -> None:
    database = build_mongomock_database()
    await init_beanie(database=database, document_models=[UserDocument])
    repository = UserRepository(database=database)
    service = UserService(repository=repository)
    result = await service.get_user(user_id)
```

### Using Mocked HTTP Client

```python
from fastapi_factory_utilities.core.plugins.aiohttp.mockers import (
    build_mocked_aiohttp_response,
    build_mocked_aiohttp_resource,
)

async def test_with_mocked_http() -> None:
    response = build_mocked_aiohttp_response(
        status=HTTPStatus.OK,
        json={"data": "value"},
    )
    resource = build_mocked_aiohttp_resource(get=response)
    service = MyService(http_resource=resource)
```

### Recording AMQP publishes / listener decode

```python
from fastapi_factory_utilities.core.testing import InMemoryPublisher, build_incoming_message

async def test_audit_publish() -> None:
    publisher = InMemoryPublisher()
    await service_under_test(publisher)
    assert publisher.published[0][1] == expected_routing_key

async def test_listener_rejects_bad_json() -> None:
    incoming = build_incoming_message(b"not-json")
    await listener._on_message(incoming)
    incoming.reject.assert_awaited_once_with(requeue=False)
```

---

## Test Fixtures

### Shipped fixtures (`fastapi_factory_utilities.core.testing`, pytest11 plugin)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `mongomock_database` | function | Fresh mongomock `AsyncDatabase` |
| `mongomock_odm_database` | function | Same + `ContractDocument` Beanie init |
| `contract_repository_mongomock` | function | `ContractRepository` on mongomock |
| `fakeredis_client` | function | In-memory Redis |
| `app_with_fakeredis` | function | FastAPI app with `redis_client` on state |
| `moto_s3_bucket` | function | `S3BucketResource` on moto |
| `app_with_moto_s3` | function | FastAPI app with S3 state keys |
| `in_memory_scheduler_component` | function | Taskiq `InMemoryBroker` component |
| `app_with_in_memory_taskiq` | function | FastAPI app with scheduler on state |
| `in_memory_otel` | function | In-memory tracer/meter providers |
| `app_with_in_memory_otel` | function | FastAPI app with OTel on state |

### Available Fixtures (from `tests/conftest.py` — containers)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `mongodb_server_as_container` | session | MongoDB Testcontainer |
| `mongodb_database_name` | function | Unique database name |
| `async_motor_database` | function | Async MongoDB database |
| `odm_plugin_factory` | function | ODM plugin factory |
| `redis_container` | session | Redis Testcontainer |
| `taskiq_plugin` | function | Taskiq plugin |
| `rabbitmq_container` | session | RabbitMQ Testcontainer |
| `aiopika_plugin` | function | Aiopika plugin |
| `minio_container` | session | MinIO Testcontainer |
| `s3_buckets` | function | Created logical→physical buckets |
| `s3_plugin_factory` | function | S3 plugin factory |

---

## Docker Development

### Using Dev Container

```bash
./scripts/dev-in-container.sh
```

### Docker Compose Services

```yaml
# Available services in docker-compose.yml
services:
  otel_collector:   # OpenTelemetry Collector (ports 4317, 4318)
  mongo:            # MongoDB (port 27017)
  application:      # Example application (port 8000)
```

### Start Individual Services

```bash
# MongoDB only
docker-compose up -d mongo

# OpenTelemetry stack
docker-compose up -d otel_collector

# All services
docker-compose up -d
```

---

## Configuration for Development

### Example `application.yaml`

```yaml
application:
  service_namespace: "my-company"
  service_name: "my-service"
  description: "My microservice description"
  version: "1.0.0"
  environment: "development"

server:
  host: "0.0.0.0"
  port: 8000
  workers: 1

cors:
  allow_origins: ["*"]
  allow_credentials: true
  allow_methods: ["*"]
  allow_headers: ["*"]

development:
  debug: true
  reload: true

logging_mode: "console"
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

The CI pipeline (`.github/workflows/ci.yml`) runs:

1. **Setup** - Install dependencies, generate `poetry.lock`
2. **SBOM Creation** - Generate Software Bill of Materials
3. **Dependency Scan** - Grype vulnerability scanning
4. **Pre-commit** - Run all linting, formatting, type checking, tests
5. **Release** (on tags) - Build and publish to PyPI

### Running CI Locally

```bash
# Simulate CI pre-commit step
poetry run pre-commit run --all-files
```

---

## Code Style Guidelines

### Import Order

```python
# 1. Standard library
import logging
from typing import Any

# 2. Third-party
from fastapi import FastAPI
from pydantic import BaseModel

# 3. Local application
from fastapi_factory_utilities.core.app import ApplicationAbstract
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `ApplicationAbstract` |
| Functions | snake_case | `get_config()` |
| Constants | UPPER_SNAKE | `DEFAULT_PORT` |
| Private | Leading underscore | `_internal_method()` |
| Type Variables | Descriptive + Type | `DocumentGenericType` |

### Docstrings (Google Style)

```python
def my_function(param1: str, param2: int) -> bool:
    """Brief description.

    Longer description if needed.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: When something is wrong.
    """
```

---

## Troubleshooting

### Poetry Lock Issues

```bash
poetry lock --no-update
poetry install --with test --extras all
```

### Pre-commit Cache Issues

```bash
pre-commit clean
pre-commit install
```

### MongoDB Connection Issues

```bash
# Check if MongoDB is running
docker-compose ps mongo

# View MongoDB logs
docker-compose logs mongo
```

### Import Errors in Tests

Ensure PYTHONPATH includes `src` and `tests`:

```bash
export PYTHONPATH=./src:./tests:$PYTHONPATH
```

---

## Useful Commands Reference

| Task | Command |
|------|---------|
| Install deps | `poetry install --with test --extras all` |
| Run tests | `poetry run pytest` |
| Format code | `poetry run ruff format src tests` |
| Lint code | `poetry run ruff check --fix src tests` |
| Type check | `poetry run mypy` |
| Pre-commit | `poetry run pre-commit run --all-files` |
| Run example | `poetry run fastapi_factory_utilities-example` |
| Update deps | `poetry update --with test` |

---

*Generated by BMAD Document Project Workflow*
