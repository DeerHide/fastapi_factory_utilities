# Repository Pattern

The repository pattern provides a type-safe abstraction for data access with MongoDB/Beanie, separating domain entities from persistence concerns.

## When to Use

Use the repository pattern when:
- Implementing data access layer with clean architecture
- Separating domain entities from database documents
- Building testable services with mockable data access
- Performing CRUD operations with type safety
- Managing database sessions and transactions
- Writing unit tests without a real database

## AbstractRepository

Base class for implementing repositories with Document-Entity mapping.

### Implementation

```python
from fastapi_factory_utilities.core.plugins.odm_plugin import AbstractRepository
from my_app.models import BookDocument
from my_app.entities import BookEntity

class BookRepository(AbstractRepository[BookDocument, BookEntity]):
    """Repository for books."""
    pass
```

The repository automatically:
- Maps between Document and Entity types
- Manages database sessions
- Handles timestamps (created_at, updated_at)
- Provides type-safe CRUD operations

### Constructor

```python
from fastapi import Depends
from fastapi_factory_utilities.core.plugins.odm_plugin import depends_odm_database

def get_book_repository(
    database = Depends(depends_odm_database),
) -> BookRepository:
    return BookRepository(database=database)
```

## CRUD Operations

### Insert

```python
from uuid import uuid4

entity = BookEntity(
    id=uuid4(),
    title="Clean Architecture",
    author="Robert C. Martin",
)

created_entity = await repository.insert(entity)
# created_at and updated_at are set automatically
```

### Update

```python
entity.title = "Clean Architecture (Updated)"
updated_entity = await repository.update(entity)
# updated_at is refreshed automatically
```

### Get by ID

```python
from uuid import UUID

entity_id = UUID("...")
entity = await repository.get_one_by_id(entity_id)

if entity is None:
    raise HTTPException(status_code=404, detail="Not found")
```

### Delete

```python
# Silent delete (no error if not found)
await repository.delete_one_by_id(entity_id)

# Raise error if not found
await repository.delete_one_by_id(entity_id, raise_if_not_found=True)
```

### Find with Filters

```python
from beanie import SortDirection

# Find all
entities = await repository.find()

# Find with pagination
entities = await repository.find(
    skip=0,
    limit=10,
)

# Find with sorting
entities = await repository.find(
    sort=[("created_at", SortDirection.DESCENDING)],
)

# Find with filters (using document fields)
entities = await repository.find(
    {"author": "Robert C. Martin"},
    skip=0,
    limit=10,
)

# Find with Beanie query expressions
entities = await repository.find(
    BookDocument.author == "Robert C. Martin",
    BookDocument.published_year >= 2000,
)
```

## Session Management

### Automatic Sessions

The `@managed_session()` decorator automatically creates sessions:

```python
# Session is created automatically
entity = await repository.insert(my_entity)
```

### Manual Sessions

```python
async with repository.get_session() as session:
    # Multiple operations in same session
    entity1 = await repository.insert(entity1, session=session)
    entity2 = await repository.insert(entity2, session=session)
```

## Testing with AbstractRepositoryInMemory

The library provides an in-memory repository implementation for testing.

### Implementation

```python
from fastapi_factory_utilities.core.plugins.odm_plugin import AbstractRepositoryInMemory
from my_app.models import BookDocument
from my_app.entities import BookEntity

class BookRepositoryInMemory(AbstractRepositoryInMemory[BookDocument, BookEntity]):
    """In-memory repository for testing."""
    pass
```

### Basic Usage

```python
import pytest
from my_app.services import BookService

@pytest.fixture
def book_repository() -> BookRepositoryInMemory:
    return BookRepositoryInMemory()

@pytest.fixture
def book_service(book_repository: BookRepositoryInMemory) -> BookService:
    return BookService(repository=book_repository)

async def test_create_book(book_service: BookService):
    book = await book_service.create_book(
        title="Test Book",
        author="Test Author",
    )
    assert book.title == "Test Book"
```

### Pre-populated Data

```python
@pytest.fixture
def book_repository() -> BookRepositoryInMemory:
    existing_books = [
        BookEntity(
            id=uuid4(),
            title="Existing Book",
            author="Existing Author",
        ),
    ]
    return BookRepositoryInMemory(entities=existing_books)
```

### Query Support

The in-memory repository supports MongoDB-style queries:

```python
# Equality
entities = await repository.find({"author": "John"})

# Comparison operators
entities = await repository.find({"year": {"$gt": 2000}})
entities = await repository.find({"year": {"$gte": 2000}})
entities = await repository.find({"year": {"$lt": 2020}})
entities = await repository.find({"year": {"$lte": 2020}})
entities = await repository.find({"author": {"$ne": "Unknown"}})

# In/Not In
entities = await repository.find({"status": {"$in": ["active", "pending"]}})
entities = await repository.find({"status": {"$nin": ["deleted"]}})

# Regex
entities = await repository.find({"title": {"$regex": "^Clean", "$options": "i"}})

# Exists
entities = await repository.find({"deleted_at": {"$exists": False}})

# Array operators
entities = await repository.find({"tags": {"$all": ["python", "fastapi"]}})
entities = await repository.find({"tags": {"$size": 3}})
```

### MockQueryField for Document Fields

The in-memory repository supports Beanie-style query expressions:

```python
# These work in both real and in-memory repositories
entities = await repository.find(
    BookDocument.author == "John",
    BookDocument.year >= 2000,
)
```

## Error Handling

### Operation Errors

```python
from fastapi_factory_utilities.core.plugins.odm_plugin.exceptions import (
    OperationError,
    UnableToCreateEntityDueToDuplicateKeyError,
)

try:
    await repository.insert(entity)
except UnableToCreateEntityDueToDuplicateKeyError:
    # Handle duplicate key (unique constraint violation)
    raise HTTPException(status_code=409, detail="Already exists")
except OperationError as e:
    # Handle other database errors
    logger.error("Database operation failed", error=e)
    raise HTTPException(status_code=500, detail="Database error")
```

### Not Found Handling

```python
entity = await repository.get_one_by_id(entity_id)
if entity is None:
    raise HTTPException(status_code=404, detail="Entity not found")

# Or use delete with raise_if_not_found
try:
    await repository.delete_one_by_id(entity_id, raise_if_not_found=True)
except ValueError:
    raise HTTPException(status_code=404, detail="Entity not found")
```

## Complete Example

### Document

```python
# models/book/document.py
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

### Entity

```python
# entities/book.py
from pydantic import Field
from fastapi_factory_utilities.core.plugins.odm_plugin import PersistedEntity

class BookEntity(PersistedEntity):
    title: str = Field(title="Book title")
    author: str = Field(title="Author name")
    published_year: int = Field(title="Year published")
```

### Repository

```python
# repositories/book.py
from fastapi_factory_utilities.core.plugins.odm_plugin import AbstractRepository
from my_app.models.book import BookDocument
from my_app.entities.book import BookEntity

class BookRepository(AbstractRepository[BookDocument, BookEntity]):
    pass
```

### Service

```python
# services/book.py
from uuid import UUID
from my_app.repositories.book import BookRepository
from my_app.entities.book import BookEntity

class BookService:
    def __init__(self, repository: BookRepository) -> None:
        self._repository = repository

    async def create_book(self, title: str, author: str, year: int) -> BookEntity:
        entity = BookEntity(title=title, author=author, published_year=year)
        return await self._repository.insert(entity)

    async def get_book(self, book_id: UUID) -> BookEntity | None:
        return await self._repository.get_one_by_id(book_id)

    async def list_books(self, skip: int = 0, limit: int = 10) -> list[BookEntity]:
        return await self._repository.find(skip=skip, limit=limit)
```

### Test with In-Memory Repository

```python
# tests/test_book_service.py
import pytest
from fastapi_factory_utilities.core.plugins.odm_plugin import AbstractRepositoryInMemory
from my_app.models.book import BookDocument
from my_app.entities.book import BookEntity
from my_app.services.book import BookService

class BookRepositoryInMemory(AbstractRepositoryInMemory[BookDocument, BookEntity]):
    pass

@pytest.fixture
def repository() -> BookRepositoryInMemory:
    return BookRepositoryInMemory()

@pytest.fixture
def service(repository: BookRepositoryInMemory) -> BookService:
    return BookService(repository=repository)

async def test_create_and_get_book(service: BookService):
    created = await service.create_book(
        title="Test Book",
        author="Test Author",
        year=2024,
    )

    retrieved = await service.get_book(created.id)

    assert retrieved is not None
    assert retrieved.title == "Test Book"
    assert retrieved.author == "Test Author"
```

## Best Practices

1. **One Repository Per Aggregate**: Create one repository per domain aggregate
2. **Type Safety**: Always specify Document and Entity generic types
3. **Dependency Injection**: Use FastAPI `Depends` for repository injection
4. **Session Management**: Let the decorator manage sessions for simple operations
5. **Testing**: Use `AbstractRepositoryInMemory` for unit tests
6. **Error Handling**: Handle `OperationError` and `UnableToCreateEntityDueToDuplicateKeyError`
7. **Separation**: Keep entities independent of documents (no Beanie imports in entities)

## Reference

- `src/fastapi_factory_utilities/core/plugins/odm_plugin/repositories.py` - AbstractRepository
- `src/fastapi_factory_utilities/core/plugins/odm_plugin/mockers.py` - AbstractRepositoryInMemory
- `src/fastapi_factory_utilities/core/plugins/odm_plugin/helpers.py` - PersistedEntity
- `src/fastapi_factory_utilities/core/plugins/odm_plugin/exceptions.py` - Exceptions
