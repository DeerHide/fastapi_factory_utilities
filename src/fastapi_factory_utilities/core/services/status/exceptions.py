"""Provides exceptions for the status service."""

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError
from fastapi_factory_utilities.core.services.status.types import ComponentInstanceType


class StatusServiceError(FastAPIFactoryUtilitiesError):
    """Status service error."""


class ComponentRegistrationError(StatusServiceError):
    """Component registration error."""

    def __init__(
        self,
        component_instance: ComponentInstanceType,
    ) -> None:
        """Initialize the component registration error.

        Args:
            component_instance (ComponentInstanceType): The component instance.

        """
        super().__init__(
            message="An error occurred while registering the component instance.",
            component_instance=component_instance,
        )
