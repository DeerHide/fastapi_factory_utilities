# ODM Plugin (MongoDB)

The ODM plugin provides MongoDB integration using Beanie ODM with automatic connection management and status monitoring.

## When to Use

Use the ODM plugin when:
- Building applications that need MongoDB persistence
- Using Beanie ODM for document modeling
- Managing MongoDB connections with automatic lifecycle
- Implementing the repository pattern with MongoDB
- Needing automatic health/readiness status for database connections

## ODMPlugin

The plugin manages MongoDB connections, Beanie initialization, and status monitoring.

### Configuration

```python
from fastapi_factory_utilities.core.plugins.odm_plugin import ODMPlugin

# With automatic config from application
plugin = ODMPlugin()

# With custom document models
plugin = ODMPlugin(document_models=[BookDocument, UserDocument])

# With custom ODM config
from fastapi_factory_utilities.core.plugins.odm_plugin.configs import ODMConfig

odm_config = ODMConfig(
    uri="mongodb://localhost:27017",
    database="my_database",
    connection_timeout_ms=4000,
)
plugin = ODMPlugin(odm_config=odm_config)
```

### YAML Configuration

```yaml
odm:
  uri: "${MONGODB_URI:mongodb://localhost:27017}"
  database: "${MONGODB_DATABASE:my_database}"
  connection_timeout_ms: 4000
```

### Application Setup

```python
from fastapi_factory_utilities.core.app import ApplicationAbstract
from fastapi_factory_utilities.core.plugins.odm_plugin import ODMPlugin

class MyApp(ApplicationAbstract):
    PACKAGE_NAME = "my_app"
    ODM_DOCUMENT_MODELS = [BookDocument, UserDocument]  # Register document models

    def configure(self) -> None:
        pass

    async def on_startup(self) -> None:
        pass

    async def on_shutdown(self) -> None:
        pass

class MyAppBuilder(ApplicationGenericBuilder[MyApp]):
    def get_default_plugins(self) -> list:
        return [ODMPlugin()]
```

## BaseDocument

Base class for all Beanie document models with common fields.

### Structure

```python
from fastapi_factory_utilities.core.plugins.odm_plugin import BaseDocument

class BaseDocument(Document):
    id: UUID  # UUID instead of ObjectId for database agnosticism
    revision_id: UUID | None  # For optimistic locking
    created_at: datetime.datetime  # Indexed, auto-set on insert
    updated_at: datetime.datetime  # Indexed, auto-set on insert/update
```

### Creating Documents

```python
from typing import Annotated
from beanie import Indexed
from fastapi_factory_utilities.core.plugins.odm_plugin import BaseDocument

class BookDocument(BaseDocument):
    title: Annotated[str, Indexed(unique=True)]
    author: str
    published_year: int

    class Settings(BaseDocument.Settings):
        collection: str = "books"
```

### Document Settings

```python
class Settings(BaseDocument.Settings):
    collection: str = "my_collection"  # MongoDB collection name
    use_revision = True  # Enable optimistic locking (inherited)
```

## PersistedEntity

Base class for domain entities that map to documents.

### Structure

```python
from fastapi_factory_utilities.core.plugins.odm_plugin import PersistedEntity

class PersistedEntity(BaseModel):
    id: UUID  # Entity identifier
    revision_id: UUID | None  # For optimistic locking
    created_at: datetime.datetime  # Creation timestamp
    updated_at: datetime.datetime  # Last update timestamp
```

### Creating Entities

```python
from pydantic import Field
from fastapi_factory_utilities.core.plugins.odm_plugin import PersistedEntity

class BookEntity(PersistedEntity):
    title: str = Field(title="Title of the book")
    author: str = Field(title="Author name")
    published_year: int = Field(title="Year published")
```

## Dependencies

### Access Database

```python
from fastapi import Depends
from fastapi_factory_utilities.core.plugins.odm_plugin import (
    depends_odm_database,
    depends_odm_client,
)

@router.get("/stats")
async def get_stats(
    database = Depends(depends_odm_database),
):
    # Access MongoDB database directly
    stats = await database.command("dbStats")
    return stats

@router.get("/health")
async def health(
    client = Depends(depends_odm_client),
):
    # Access MongoDB client
    return {"connected": client is not None}
```

## Status Monitoring

The plugin automatically registers with the StatusService:
- Reports `HEALTHY`/`READY` on successful connection
- Reports `UNHEALTHY`/`NOT_READY` on connection failure
- Component type: `DATABASE`
- Identifier: `MongoDB`

## Error Handling

The plugin can encounter errors during connection and operations.

### Connection Errors

```python
# Connection errors are handled during plugin startup:
# - Plugin reports UNHEALTHY/NOT_READY status
# - Error is logged
# - Application continues (allows graceful degradation)

# To handle connection failures in your code:
from fastapi_factory_utilities.core.plugins.odm_plugin.exceptions import (
    OperationError,
)

try:
    result = await repository.insert(entity)
except OperationError as e:
    logger.error("Database operation failed", error=e)
    raise
```

### Duplicate Key Errors

```python
from fastapi_factory_utilities.core.plugins.odm_plugin.exceptions import (
    UnableToCreateEntityDueToDuplicateKeyError,
)

try:
    await repository.insert(entity)
except UnableToCreateEntityDueToDuplicateKeyError:
    # Handle duplicate key (e.g., unique constraint violation)
    raise HTTPException(status_code=409, detail="Entity already exists")
```

## Best Practices

1. **Document Models**: Register all document models in `ODM_DOCUMENT_MODELS`
2. **UUID IDs**: Use UUID for entity IDs for database agnosticism
3. **Indexes**: Define indexes using Beanie's `Indexed` annotation
4. **Settings**: Always define `collection` in document Settings
5. **Plugin Order**: Load ODMPlugin before repository-dependent plugins
6. **Environment Variables**: Use environment variables for connection strings

## Reference

- `src/fastapi_factory_utilities/core/plugins/odm_plugin/plugins.py` - ODMPlugin
- `src/fastapi_factory_utilities/core/plugins/odm_plugin/documents.py` - BaseDocument
- `src/fastapi_factory_utilities/core/plugins/odm_plugin/helpers.py` - PersistedEntity
- `src/fastapi_factory_utilities/core/plugins/odm_plugin/configs.py` - ODMConfig
- `src/fastapi_factory_utilities/core/plugins/odm_plugin/depends.py` - Dependencies
