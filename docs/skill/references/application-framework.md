# Application Framework

The application framework provides the foundation for building microservices with a plugin-based architecture.

## When to Use

Use the application framework when:
- Building FastAPI microservices that need structured initialization
- Creating plugin-based architectures for extensibility
- Managing application lifecycle (startup, shutdown)
- Loading configuration from YAML files with environment overrides
- Building applications that need to integrate multiple services (database, message broker, etc.)

## ApplicationAbstract

The base class for all applications. Subclasses must implement lifecycle methods and define required class variables.

### Required Class Variables

- `PACKAGE_NAME: ClassVar[str]` - The package name for configuration loading
- `CONFIG_CLASS: ClassVar[type[RootConfig]]` - The configuration class (defaults to `RootConfig`)
- `ODM_DOCUMENT_MODELS: ClassVar[list[type[Document]]]` - List of Beanie document models

### Lifecycle Methods

```python
@abstractmethod
def configure(self) -> None:
    """Configure the application (add routes, middleware, etc.)."""

@abstractmethod
async def on_startup(self) -> None:
    """Custom startup logic."""

@abstractmethod
async def on_shutdown(self) -> None:
    """Custom shutdown logic."""
```

### Application State

Applications can add values to the FastAPI app state:

```python
self.add_to_state(key="my_service", value=my_service_instance)
```

Values are accessible via `request.app.state.my_service` in FastAPI dependencies.

### Plugin Management

Plugins are automatically loaded, started, and shut down:

- `load_plugins()` - Calls `on_load()` on all plugins (sync initialization)
- `startup_plugins()` - Calls `on_startup()` on all plugins (async initialization)
- `shutdown_plugins()` - Calls `on_shutdown()` on all plugins (cleanup)

## ApplicationGenericBuilder

Builder pattern for constructing applications with type safety.

### Usage

```python
class MyAppBuilder(ApplicationGenericBuilder[MyApp]):
    def get_default_plugins(self) -> list[PluginAbstract]:
        return [ODMPlugin(), OpenTelemetryPlugin()]

    def __init__(self, plugins: list[PluginAbstract] | None = None):
        if plugins is None:
            plugins = self.get_default_plugins()
        super().__init__(plugins=plugins)
```

### Builder Methods

- `add_plugin_to_activate(plugin: PluginAbstract) -> Self` - Add a plugin
- `add_config(config: RootConfig) -> Self` - Set custom configuration
- `add_fastapi_builder(fastapi_builder: FastAPIBuilder) -> Self` - Set custom FastAPI builder
- `build(**kwargs) -> T` - Build the application instance
- `build_and_serve() -> None` - Build and start Uvicorn server
- `configure_logging(mode, logging_config) -> None` - Configure logging

### Configuration Loading

If no config is provided, the builder automatically loads configuration from:
- `{PACKAGE_NAME}/application.yaml` - YAML configuration file
- Environment variables - Override YAML values

## PluginAbstract

Base class for all plugins. Plugins extend application functionality.

### Plugin Lifecycle

1. **on_load()** - Synchronous initialization
   - Validate configuration
   - Register dependencies
   - Add to application state

2. **on_startup()** - Asynchronous initialization
   - Connect to external services
   - Initialize async resources
   - Start background tasks

3. **on_shutdown()** - Cleanup
   - Close connections
   - Clean up resources
   - Stop background tasks

### Plugin State

Plugins can add values to the FastAPI app state:

```python
self._add_to_state(key="my_resource", value=my_resource)
```

### Example Plugin

```python
class MyPlugin(PluginAbstract):
    def on_load(self) -> None:
        # Sync initialization
        assert self._application is not None
        config = self._application.get_config()
        # Validate config, register dependencies

    async def on_startup(self) -> None:
        # Async initialization
        # Connect to services, start tasks

    async def on_shutdown(self) -> None:
        # Cleanup
        # Close connections, stop tasks
```

## Complete Example

```python
from fastapi_factory_utilities.core.app import (
    ApplicationAbstract,
    ApplicationGenericBuilder,
    RootConfig,
)
from fastapi_factory_utilities.core.plugins.odm_plugin import ODMPlugin
from fastapi_factory_utilities.core.plugins.opentelemetry_plugin import OpenTelemetryPlugin

class MyAppConfig(RootConfig):
    pass

class MyApp(ApplicationAbstract):
    CONFIG_CLASS = MyAppConfig
    PACKAGE_NAME = "my_app"
    ODM_DOCUMENT_MODELS = []

    def configure(self) -> None:
        # Add routes, middleware
        from fastapi import APIRouter
        router = APIRouter()
        self.fastapi_builder.add_api_router(router)

    async def on_startup(self) -> None:
        # Custom startup logic
        pass

    async def on_shutdown(self) -> None:
        # Custom shutdown logic
        pass

class MyAppBuilder(ApplicationGenericBuilder[MyApp]):
    def get_default_plugins(self):
        return [ODMPlugin(), OpenTelemetryPlugin()]

    def __init__(self, plugins=None):
        if plugins is None:
            plugins = self.get_default_plugins()
        super().__init__(plugins=plugins)

# Build and run
if __name__ == "__main__":
    MyAppBuilder().build_and_serve()
```

## Error Handling

The application framework can encounter errors during initialization, plugin loading, and lifecycle management.

### Plugin Initialization Errors

```python
class MyPlugin(PluginAbstract):
    def on_load(self) -> None:
        try:
            # Validate configuration
            config = self._application.get_config()
            if not config.my_setting:
                raise ValueError("my_setting is required")
        except ValueError as e:
            # Handle configuration errors
            logger.error("Plugin configuration error", error=e)
            raise

    async def on_startup(self) -> None:
        try:
            # Connect to external service
            await self.connect_to_service()
        except ConnectionError as e:
            # Handle connection failures
            logger.error("Failed to connect to service", error=e)
            # Optionally raise to prevent application startup
            raise
        except Exception as e:
            # Handle other startup errors
            logger.error("Plugin startup error", error=e)
            raise
```

### Configuration Loading Errors

```python
from fastapi_factory_utilities.core.app.config import GenericConfigBuilder
from pydantic import ValidationError

try:
    builder = GenericConfigBuilder[MyRootConfig](
        package_name="my_app",
        config_class=MyRootConfig,
    )
    config = builder.build()
except FileNotFoundError as e:
    # Handle missing configuration file
    logger.error("Configuration file not found", error=e)
    raise
except ValidationError as e:
    # Handle configuration validation errors
    logger.error("Invalid configuration", errors=e.errors())
    raise
except Exception as e:
    # Handle other configuration errors
    logger.error("Configuration loading error", error=e)
    raise
```

### Application Startup Errors

```python
class MyApp(ApplicationAbstract):
    async def on_startup(self) -> None:
        try:
            # Custom startup logic
            await self.initialize_services()
        except Exception as e:
            # Log and handle startup errors
            logger.error("Application startup error", error=e)
            # Consider whether to raise (fail fast) or continue
            raise
```

### Plugin Loading Errors

```python
class MyAppBuilder(ApplicationGenericBuilder[MyApp]):
    def get_default_plugins(self):
        plugins = []
        try:
            plugins.append(ODMPlugin())
            plugins.append(OpenTelemetryPlugin())
        except Exception as e:
            # Handle plugin creation errors
            logger.error("Failed to create plugin", error=e)
            raise
        return plugins
```

### Shutdown Errors

```python
class MyPlugin(PluginAbstract):
    async def on_shutdown(self) -> None:
        try:
            # Cleanup resources
            await self.close_connections()
        except Exception as e:
            # Log shutdown errors but don't raise
            # Application is shutting down anyway
            logger.warning("Plugin shutdown error", error=e)
```

## Best Practices

1. **Plugin Order**: Load plugins in dependency order (e.g., ODM before repositories)
2. **State Management**: Use `add_to_state()` for resources needed across the application
3. **Lifecycle Methods**: Keep `configure()` lightweight, use `on_startup()` for heavy initialization
4. **Error Handling**: Handle plugin initialization failures gracefully
5. **Configuration**: Use YAML files with environment variable overrides for flexibility
6. **Type Safety**: Leverage generic types for builder and application classes
7. **Plugin Design**: Keep plugins focused and composable
8. **Shutdown Cleanup**: Always clean up resources in `on_shutdown()` methods

## Reference

- `src/fastapi_factory_utilities/core/app/application.py` - ApplicationAbstract
- `src/fastapi_factory_utilities/core/app/builder.py` - ApplicationGenericBuilder
- `src/fastapi_factory_utilities/core/plugins/abstracts.py` - PluginAbstract
