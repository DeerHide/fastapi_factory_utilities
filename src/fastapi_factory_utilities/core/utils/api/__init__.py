"""Unified API utilities: response/update schemas, queries, pagination, and search markers.

This package consolidates what used to live in
``fastapi_factory_utilities.core.utils.api``,
``fastapi_factory_utilities.core.utils.queries``, and
``fastapi_factory_utilities.core.utils.paginations``. A single
:class:`ApiField` marker now drives response, updateable, and searchable
behaviors via boolean flags. The convenience instances :data:`ApiResponseField`,
:data:`UpdateableField`, and :data:`SearchableField` cover the most common
combinations.

HTTP query examples:

- Filtering:
    - GET /api/v1/resources?field1=value1
    - GET /api/v1/resources?object1.field1=value1
      (dotted keys: use a nested ``BaseModel`` field on your :class:`QueryAbstract`, or a leaf
      ``Field(validation_alias=...)``, or :meth:`QueryResolver.add_authorized_field`.)
    - GET /api/v1/resources?field1[gt]=value1
    - GET /api/v1/resources?field1[lt]=value1
    - GET /api/v1/resources?field1[gte]=value1
    - GET /api/v1/resources?field1[lte]=value1
    - GET /api/v1/resources?field1[eq]=value1
    - GET /api/v1/resources?field1[neq]=value1
    - GET /api/v1/resources?field1[in]=value1&field1[in]=value2&field1[in]=value3
    - GET /api/v1/resources?field1[nin]=value1&field1[nin]=value2&field1[nin]=value3
    - GET /api/v1/resources?field1[contains]=value1
    - GET /api/v1/resources?field1[not_contains]=value1
    - GET /api/v1/resources?field1[starts_with]=value1
    - GET /api/v1/resources?field1[ends_with]=value1
- Sorting (ascending order if no prefix is provided):
    - GET /api/v1/users?sort=name
    - GET /api/v1/users?sort=-name&sort=+age
"""

from .markers import (
    ApiField,
    ApiResponseField,
    SearchableField,
    UpdateableField,
    has_response_flag,
    has_searchable_flag,
    has_updateable_flag,
)
from .pagination import PaginationPageOffset, PaginationSize, resolve_offset
from .query_abstract import QueryAbstract, QueryFilterNestedAbstract
from .query_resolver import QueryResolver
from .query_types import (
    QueryField,
    QueryFieldName,
    QueryFieldOperation,
    QueryFieldOperatorEnum,
    QuerySort,
    QuerySortDirectionEnum,
    RawQueryFieldName,
    RawQuerySort,
)
from .response_model import (
    ApiResponseModelAbstract,
    ApiResponseSchemaBase,
    FieldChange,
    ReconcileResult,
)
from .searchable_entity import SearchableEntity

QueryFilterAbstract = QueryAbstract
"""Backward-compatible alias for :class:`QueryAbstract`."""

__all__: list[str] = [
    "ApiField",
    "ApiResponseField",
    "ApiResponseModelAbstract",
    "ApiResponseSchemaBase",
    "FieldChange",
    "PaginationPageOffset",
    "PaginationSize",
    "QueryAbstract",
    "QueryField",
    "QueryFieldName",
    "QueryFieldOperation",
    "QueryFieldOperatorEnum",
    "QueryFilterAbstract",
    "QueryFilterNestedAbstract",
    "QueryResolver",
    "QuerySort",
    "QuerySortDirectionEnum",
    "RawQueryFieldName",
    "RawQuerySort",
    "ReconcileResult",
    "SearchableEntity",
    "SearchableField",
    "UpdateableField",
    "has_response_flag",
    "has_searchable_flag",
    "has_updateable_flag",
    "resolve_offset",
]
