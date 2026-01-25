# Logging Utilities

Structured logging setup with structlog integration for console and JSON output.

## When to Use

Use logging utilities when:
- Setting up structured logging for FastAPI applications
- Configuring console logging for local development
- Setting up JSON logging for production environments
- Integrating with log aggregation services (Datadog, ELK, etc.)
- Configuring per-module log levels
- Setting up structured logging with automatic context
- Building production-ready logging infrastructure

## setup_log

Configures structured logging with structlog.

### Basic Usage

```python
from fastapi_factory_utilities.core.utils.log import (
    setup_log,
    LogModeEnum,
)

# Console mode (development)
setup_log(mode=LogModeEnum.CONSOLE, log_level="DEBUG")

# JSON mode (production)
setup_log(mode=LogModeEnum.JSON, log_level="INFO")
```

### Logging Modes

#### CONSOLE Mode

Pretty-printed logs for development:

```python
setup_log(mode=LogModeEnum.CONSOLE, log_level="DEBUG")
```

Features:
- Colorized output
- Pretty exception formatting
- Human-readable format

#### JSON Mode

Structured JSON logs for production:

```python
setup_log(mode=LogModeEnum.JSON, log_level="INFO")
```

Features:
- JSON format (Datadog-compatible)
- Exception tracebacks as dictionaries
- `message` field (instead of `event`)

### Log Levels

```python
setup_log(
    mode=LogModeEnum.CONSOLE,
    log_level="DEBUG",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
)
```

### Per-Logger Configuration

```python
from fastapi_factory_utilities.core.utils.log import LoggingConfig

setup_log(
    mode=LogModeEnum.CONSOLE,
    log_level="INFO",
    logging_config=[
        LoggingConfig(name="my_module", level="DEBUG"),
        LoggingConfig(name="uvicorn", level="WARNING"),
    ],
)
```

## LoggingConfig

Configuration for individual loggers.

```python
from fastapi_factory_utilities.core.utils.log import LoggingConfig

config = LoggingConfig(
    name="my_module",
    level="DEBUG",  # Can be int or string
)
```

## Structured Logging

The setup includes automatic structured logging:

```python
import structlog

logger = structlog.get_logger()

# Structured logging
logger.info(
    "User logged in",
    user_id="123",
    ip_address="192.168.1.1",
    timestamp="2024-01-01T00:00:00Z",
)
```

### Automatic Fields

The logger automatically adds:
- `logger` - Logger name
- `level` - Log level
- `timestamp` - ISO format timestamp
- `module` - Module name
- `func_name` - Function name
- `lineno` - Line number

## Exception Handling

Uncaught exceptions are automatically logged:

```python
# Uncaught exceptions are logged automatically
# No need for try/except in every function
```

## Uvicorn Integration

Uvicorn loggers are automatically configured:
- Messages propagate to structlog
- Color messages are cleaned
- Consistent formatting

## Usage in Application

### In Builder

```python
from fastapi_factory_utilities.core.app.builder import ApplicationGenericBuilder
from fastapi_factory_utilities.core.utils.log import LogModeEnum

class MyAppBuilder(ApplicationGenericBuilder[MyApp]):
    def build_and_serve(self):
        # Configure logging before serving
        self.configure_logging(
            mode=LogModeEnum.JSON,
            logging_config=self._root_config.logging,
        )
        super().build_and_serve()
```

### In Configuration

```yaml
logging_mode: "json"  # or "console"
logging:
  - name: "my_module"
    level: "DEBUG"
  - name: "uvicorn"
    level: "WARNING"
```

## Error Handling

Logging utilities can encounter errors during setup and configuration.

### Setup Errors

```python
from fastapi_factory_utilities.core.utils.log import setup_log, LogModeEnum

try:
    setup_log(mode=LogModeEnum.JSON, log_level="INFO")
except Exception as e:
    # Handle logging setup errors
    # Fallback to basic logging
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.error("Failed to setup structured logging", error=e)
```

### Configuration Errors

```python
from fastapi_factory_utilities.core.utils.log import LoggingConfig

try:
    setup_log(
        mode=LogModeEnum.CONSOLE,
        log_level="INFO",
        logging_config=[
            LoggingConfig(name="my_module", level="DEBUG"),
        ],
    )
except ValueError as e:
    # Handle invalid log level
    logger.error("Invalid log level", error=e)
    # Use default level
    setup_log(mode=LogModeEnum.CONSOLE, log_level="INFO")
except Exception as e:
    # Handle other configuration errors
    logger.error("Logging configuration error", error=e)
    raise
```

### Logger Configuration Errors

```python
# Per-logger configuration errors are handled gracefully:
# - Invalid logger names are ignored
# - Invalid log levels fall back to parent logger level
# - Missing loggers are created automatically

try:
    setup_log(
        mode=LogModeEnum.JSON,
        logging_config=[
            LoggingConfig(name="nonexistent_module", level="DEBUG"),
            # Invalid level will be ignored
            LoggingConfig(name="my_module", level="INVALID"),
        ],
    )
except Exception as e:
    # Configuration errors are logged but don't prevent setup
    pass
```

## Best Practices

1. **Development**: Use CONSOLE mode for readability
2. **Production**: Use JSON mode for log aggregation
3. **Log Levels**: Use appropriate levels (DEBUG for dev, INFO for prod)
4. **Structured Data**: Always use keyword arguments for structured logging
5. **Exception Logging**: Let the system handle uncaught exceptions
6. **Per-Module Levels**: Configure specific loggers for fine-grained control

## Reference

- `src/fastapi_factory_utilities/core/utils/log.py` - Logging utilities
