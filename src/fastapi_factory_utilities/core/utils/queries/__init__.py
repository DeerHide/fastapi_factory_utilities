"""Provides utilities for queries.

Examples:
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

from .abstracts import QueryAbstract
from .enums import QueryFieldOperatorEnum, QuerySortDirectionEnum
from .resolvers import QueryResolver
from .types import QueryField, QueryFieldName, QueryFieldOperation, QuerySort, RawQueryFieldName, RawQuerySort

__all__: list[str] = [
    "QueryAbstract",
    "QueryField",
    "QueryFieldName",
    "QueryFieldOperation",
    "QueryFieldOperatorEnum",
    "QueryResolver",
    "QuerySort",
    "QuerySortDirectionEnum",
    "RawQueryFieldName",
    "RawQuerySort",
]
