"""Provides the exceptions for the audit service."""

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError


class AuditServiceError(FastAPIFactoryUtilitiesError):
    """Audit service error."""
