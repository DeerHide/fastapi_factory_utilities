# Pagination Utilities

Type-safe pagination types with Pydantic integration for OpenAPI schema generation.

## When to Use

Use pagination utilities when:
- Building REST APIs that need paginated responses
- Validating pagination parameters (size, offset)
- Generating OpenAPI schemas with proper pagination constraints
- Ensuring consistent pagination across endpoints
- Limiting result sets to prevent large queries

## PaginationSize

Validated integer type for pagination size with constraints.

### Properties

- **MIN_VALUE**: 1
- **MAX_VALUE**: 200
- **DEFAULT_VALUE**: 50

### Usage

```python
from fastapi_factory_utilities.core.utils.paginations.types import PaginationSize
from fastapi import Query

@router.get("/items")
async def get_items(
    page_size: PaginationSize = PaginationSize.default(),
):
    # page_size is guaranteed to be between 1 and 200
    return {"page_size": page_size}
```

### With Query Parameter

```python
from fastapi import Query

@router.get("/items")
async def get_items(
    page_size: PaginationSize = Query(
        default=PaginationSize.default(),
        description="Number of items per page",
    ),
):
    return {"page_size": page_size}
```

### Validation

Invalid values raise `ValueError`:

```python
try:
    size = PaginationSize(0)  # Raises ValueError
except ValueError:
    pass

try:
    size = PaginationSize(300)  # Raises ValueError
except ValueError:
    pass
```

## PaginationPageOffset

Validated integer type for pagination page offset.

### Properties

- **MIN_VALUE**: 0
- **DEFAULT_VALUE**: 0

### Usage

```python
from fastapi_factory_utilities.core.utils.paginations.types import (
    PaginationPageOffset,
)

@router.get("/items")
async def get_items(
    page_offset: PaginationPageOffset = PaginationPageOffset.default(),
):
    # page_offset is guaranteed to be >= 0
    return {"page_offset": page_offset}
```

### With Query Parameter

```python
from fastapi import Query

@router.get("/items")
async def get_items(
    page_offset: PaginationPageOffset = Query(
        default=PaginationPageOffset.default(),
        description="Number of items to skip",
    ),
):
    return {"page_offset": page_offset}
```

## Combined Usage

```python
from fastapi_factory_utilities.core.utils.paginations.types import (
    PaginationSize,
    PaginationPageOffset,
)

@router.get("/items")
async def get_items(
    page_size: PaginationSize = PaginationSize.default(),
    page_offset: PaginationPageOffset = PaginationPageOffset.default(),
):
    # Calculate skip and limit for database queries
    skip = page_offset
    limit = page_size

    # Use with repository
    items = await repository.find(
        skip=skip,
        limit=limit,
    )

    return {
        "items": items,
        "page_size": page_size,
        "page_offset": page_offset,
    }
```

## OpenAPI Schema

The types automatically generate OpenAPI schema:

```json
{
  "page_size": {
    "type": "integer",
    "minimum": 1,
    "maximum": 200,
    "default": 50,
    "description": "Pagination size"
  },
  "page_offset": {
    "type": "integer",
    "minimum": 0,
    "default": 0,
    "description": "Pagination page offset"
  }
}
```

## Repository Integration

Use with repository find operations:

```python
@router.get("/books")
async def get_books(
    page_size: PaginationSize = PaginationSize.default(),
    page_offset: PaginationPageOffset = PaginationPageOffset.default(),
    repository: BookRepository = Depends(get_book_repository),
):
    books = await repository.find(
        skip=page_offset,
        limit=page_size,
    )
    return {
        "books": books,
        "pagination": {
            "size": page_size,
            "offset": page_offset,
        },
    }
```

## Error Handling

Pagination types raise validation errors for invalid values.

### Validation Errors

```python
from fastapi_factory_utilities.core.utils.paginations.types import (
    PaginationSize,
    PaginationPageOffset,
)

# Invalid pagination size
try:
    size = PaginationSize(0)  # Raises ValueError
except ValueError as e:
    # Handle validation error
    logger.warning("Invalid pagination size", value=0, error=e)
    size = PaginationSize.default()  # Use default

try:
    size = PaginationSize(300)  # Raises ValueError (max is 200)
except ValueError as e:
    # Handle validation error
    logger.warning("Pagination size exceeds maximum", value=300, max=200)
    size = PaginationSize.default()  # Use default

# Invalid pagination offset
try:
    offset = PaginationPageOffset(-1)  # Raises ValueError
except ValueError as e:
    # Handle validation error
    logger.warning("Invalid pagination offset", value=-1, error=e)
    offset = PaginationPageOffset.default()  # Use default
```

### FastAPI Validation

FastAPI automatically validates pagination parameters:

```python
from fastapi import HTTPException, Query
from fastapi_factory_utilities.core.utils.paginations.types import (
    PaginationSize,
    PaginationPageOffset,
)

@router.get("/items")
async def get_items(
    page_size: PaginationSize = Query(
        default=PaginationSize.default(),
        description="Number of items per page",
    ),
    page_offset: PaginationPageOffset = Query(
        default=PaginationPageOffset.default(),
        description="Number of items to skip",
    ),
):
    # FastAPI automatically validates and returns 422 for invalid values
    # No need for manual validation
    return {
        "items": [],
        "page_size": page_size,
        "page_offset": page_offset,
    }
```

### Pydantic Validation

When using pagination types in Pydantic models:

```python
from pydantic import BaseModel, ValidationError
from fastapi_factory_utilities.core.utils.paginations.types import PaginationSize

class PaginationParams(BaseModel):
    page_size: PaginationSize = PaginationSize.default()
    page_offset: PaginationPageOffset = PaginationPageOffset.default()

try:
    params = PaginationParams(page_size=0)  # Raises ValidationError
except ValidationError as e:
    # Handle validation errors
    logger.error("Invalid pagination parameters", errors=e.errors())
    # Use defaults
    params = PaginationParams()
```

## Best Practices

1. **Default Values**: Use `.default()` for sensible defaults
2. **Validation**: Let Pydantic handle validation automatically
3. **Documentation**: Types include descriptions in OpenAPI schema
4. **Consistency**: Use the same pagination types across endpoints
5. **Database Queries**: Use `skip` and `limit` directly with repositories

## Reference

- `src/fastapi_factory_utilities/core/utils/paginations/types.py` - Pagination types
