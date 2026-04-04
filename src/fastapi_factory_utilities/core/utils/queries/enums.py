"""Provides the enums for the query utilities."""

from enum import StrEnum


class QuerySortDirectionEnum(StrEnum):
    """Query sort direction enum."""

    ASCENDING = "+"
    DESCENDING = "-"


class QueryFieldOperatorEnum(StrEnum):
    """Query field operator enum."""

    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    EQ = "eq"
    NEQ = "neq"
    IN = "in"
    NIN = "nin"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
