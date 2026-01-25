# Configuration Utilities

Utilities for loading and managing type-safe configuration from YAML files with environment variable support.

## When to Use

Use configuration utilities when:
- Loading application configuration from YAML files
- Injecting environment variables into configuration
- Building type-safe configuration with Pydantic
- Managing configuration for different environments (dev, staging, prod)
- Overriding configuration values with environment variables
- Creating immutable (frozen) configuration objects
- Loading Redis or RabbitMQ connection credentials

## YamlFileReader

Reads YAML files with environment variable injection.

### Basic Usage

```python
from pathlib import Path
from fastapi_factory_utilities.core.utils.yaml_reader import YamlFileReader

reader = YamlFileReader(
    file_path=Path("application.yaml"),
    yaml_base_key="application",  # Optional: read from specific key
    use_environment_injection=True,  # Enable ${VAR:default} syntax
)

data = reader.read()
```

### Environment Variable Injection

YAML files support environment variable injection:

```yaml
database:
  host: ${DB_HOST:localhost}
  port: ${DB_PORT:27017}
  password: ${DB_PASSWORD}
```

Syntax: `${VARIABLE_NAME:default_value}`

### Base Key Filtering

Read from a specific section:

```python
# YAML file
application:
  service_name: "my-app"
  version: "1.0.0"

database:
  host: "localhost"

# Read only application section
reader = YamlFileReader(
    file_path=Path("config.yaml"),
    yaml_base_key="application",
)
data = reader.read()  # Only application section
```

## GenericConfigBuilder

Type-safe configuration builder from YAML files.

### Usage

```python
from fastapi_factory_utilities.core.app.config import (
    GenericConfigBuilder,
    RootConfig,
)

builder = GenericConfigBuilder[RootConfig](
    package_name="my_app",
    config_class=RootConfig,
)

config = builder.build()
```

### Configuration Loading

The builder:
1. Loads `{package_name}/application.yaml`
2. Injects environment variables
3. Validates with Pydantic
4. Returns frozen (immutable) config instance

### Custom Configuration

```python
from fastapi_factory_utilities.core.app.config import (
    BaseApplicationConfig,
    RootConfig,
)

class MyCustomConfig(BaseApplicationConfig):
    api_key: str
    timeout: int = 30

class MyRootConfig(RootConfig):
    my_custom: MyCustomConfig

# Build custom config
builder = GenericConfigBuilder[MyRootConfig](
    package_name="my_app",
    config_class=MyRootConfig,
)
config = builder.build()
```

## RedisCredentialsConfig

Configuration for Redis connections.

### Building from Application

```python
from fastapi_factory_utilities.core.utils.redis_configs import (
    build_redis_credentials_config,
)

config = build_redis_credentials_config(application=app)
# Uses application.PACKAGE_NAME to load from YAML
```

### YAML Configuration

```yaml
redis:
  host: "localhost"
  port: 6379
  password: ""
  database: 0
  ssl: false
```

### Manual Configuration

```python
from fastapi_factory_utilities.core.utils.redis_configs import (
    RedisCredentialsConfig,
)

config = RedisCredentialsConfig(
    host="localhost",
    port=6379,
    password="secret",
    database=0,
    ssl=False,
)

url = config.url  # "redis://:secret@localhost:6379/0"
```

## RabbitMQCredentialsConfig

Configuration for RabbitMQ connections.

### Building from Package

```python
from fastapi_factory_utilities.core.utils.rabbitmq_configs import (
    build_rabbitmq_credentials_config,
)

config = build_rabbitmq_credentials_config(package_name="my_app")
```

### YAML Configuration

```yaml
rabbitmq:
  host: "localhost"
  port: 5672
  username: "guest"
  password: "guest"
  virtual_host: "/"
  ssl: false
```

### Manual Configuration

```python
from fastapi_factory_utilities.core.utils.rabbitmq_configs import (
    RabbitMQCredentialsConfig,
)

config = RabbitMQCredentialsConfig(
    host="localhost",
    port=5672,
    username="guest",
    password="guest",
    virtual_host="/",
    ssl=False,
)

amqp_url = config.amqp_url  # "amqp://guest:guest@localhost:5672/"
```

## Configuration Hierarchy

```
RootConfig
├── application: BaseApplicationConfig
│   ├── service_namespace: str
│   ├── service_name: str
│   ├── environment: EnvironmentEnum
│   ├── version: str
│   └── audience: str
├── server: ServerConfig
│   ├── host: str
│   ├── port: int
│   └── workers: int
├── cors: CorsConfig
│   ├── allow_origins: list[str]
│   └── ...
├── development: DevelopmentConfig
│   ├── debug: bool
│   └── reload: bool
└── logging: list[LoggingConfig]
```

## Environment Variable Overrides

All configuration values can be overridden with environment variables:

```bash
export APPLICATION__SERVICE_NAME="my-service"
export SERVER__PORT=8080
export REDIS__HOST="redis.example.com"
```

Format: `{SECTION}__{KEY}` (double underscore)

## Error Handling

Configuration utilities can encounter errors during file reading, environment variable injection, and validation.

### File Reading Errors

```python
from pathlib import Path
from fastapi_factory_utilities.core.utils.yaml_reader import YamlFileReader

try:
    reader = YamlFileReader(
        file_path=Path("application.yaml"),
        use_environment_injection=True,
    )
    data = reader.read()
except FileNotFoundError as e:
    # Handle missing configuration file
    logger.error("Configuration file not found", path=e.filename)
    raise
except yaml.YAMLError as e:
    # Handle YAML parsing errors
    logger.error("Invalid YAML format", error=e)
    raise
except Exception as e:
    # Handle other file reading errors
    logger.error("Failed to read configuration file", error=e)
    raise
```

### Environment Variable Injection Errors

```python
# YAML with environment variable
# database:
#   password: ${DB_PASSWORD}  # Required, no default

try:
    reader = YamlFileReader(
        file_path=Path("application.yaml"),
        use_environment_injection=True,
    )
    data = reader.read()
except KeyError as e:
    # Handle missing required environment variable
    logger.error("Missing required environment variable", variable=str(e))
    raise
except Exception as e:
    # Handle other injection errors
    logger.error("Environment variable injection error", error=e)
    raise
```

### Configuration Validation Errors

```python
from fastapi_factory_utilities.core.app.config import GenericConfigBuilder
from pydantic import ValidationError

try:
    builder = GenericConfigBuilder[MyRootConfig](
        package_name="my_app",
        config_class=MyRootConfig,
    )
    config = builder.build()
except ValidationError as e:
    # Handle Pydantic validation errors
    logger.error("Configuration validation failed", errors=e.errors())
    # Print detailed validation errors
    for error in e.errors():
        logger.error(
            "Validation error",
            field=".".join(str(loc) for loc in error["loc"]),
            message=error["msg"],
            type=error["type"],
        )
    raise
except Exception as e:
    # Handle other configuration errors
    logger.error("Configuration building error", error=e)
    raise
```

### Redis Configuration Errors

```python
from fastapi_factory_utilities.core.utils.redis_configs import (
    build_redis_credentials_config,
)

try:
    config = build_redis_credentials_config(application=app)
except FileNotFoundError:
    # Handle missing configuration
    logger.warning("Redis configuration not found, using defaults")
    config = RedisCredentialsConfig()  # Use defaults
except ValidationError as e:
    # Handle invalid Redis configuration
    logger.error("Invalid Redis configuration", errors=e.errors())
    raise
```

### RabbitMQ Configuration Errors

```python
from fastapi_factory_utilities.core.utils.rabbitmq_configs import (
    build_rabbitmq_credentials_config,
)

try:
    config = build_rabbitmq_credentials_config(package_name="my_app")
except FileNotFoundError:
    # Handle missing configuration
    logger.warning("RabbitMQ configuration not found")
    raise
except ValidationError as e:
    # Handle invalid RabbitMQ configuration
    logger.error("Invalid RabbitMQ configuration", errors=e.errors())
    raise
```

## Best Practices

1. **Type Safety**: Use Pydantic models for all configuration
2. **Frozen Configs**: Keep configs immutable (frozen=True)
3. **Environment Variables**: Use for secrets and environment-specific values
4. **Validation**: Let Pydantic handle validation
5. **Defaults**: Provide sensible defaults in models
6. **Documentation**: Document configuration options in model docstrings

## Reference

- `src/fastapi_factory_utilities/core/utils/yaml_reader.py` - YamlFileReader
- `src/fastapi_factory_utilities/core/app/config.py` - GenericConfigBuilder, RootConfig
- `src/fastapi_factory_utilities/core/utils/redis_configs.py` - RedisCredentialsConfig
- `src/fastapi_factory_utilities/core/utils/rabbitmq_configs.py` - RabbitMQCredentialsConfig
