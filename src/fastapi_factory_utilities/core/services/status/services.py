"""Provides status services."""

import datetime

from fastapi import Request
from reactivex import Subject
from structlog.stdlib import BoundLogger, get_logger

from .enums import ComponentTypeEnum, HealthStatusEnum, ReadinessStatusEnum
from .exceptions import ComponentRegistrationError
from .health_calculator_strategies import (
    HealthCalculatorStrategy,
    HealthSimpleCalculatorStrategy,
)
from .readiness_calculator_strategies import (
    ReadinessCalculatorStrategy,
    ReadinessSimpleCalculatorStrategy,
)
from .types import (
    ComponentInstanceKey,
    ComponentInstanceType,
    Status,
    StatusUpdateEvent,
)

logger: BoundLogger = get_logger(__package__)


class StatusService:
    """Status service.

    It's responsible for managing the status of the components and determine the health and readiness status of the
    application.
    """

    def __init__(
        self,
        health_calculator_strategy: type[HealthCalculatorStrategy] = HealthSimpleCalculatorStrategy,
        readiness_calculator_strategy: type[ReadinessCalculatorStrategy] = ReadinessSimpleCalculatorStrategy,
    ) -> None:
        """Initialize the status service."""
        # Status
        self._health_status: HealthStatusEnum = HealthStatusEnum.HEALTHY
        self._health_calculator_strategy: type[HealthCalculatorStrategy] = health_calculator_strategy
        self._readiness_status: ReadinessStatusEnum = ReadinessStatusEnum.NOT_READY
        self._readiness_calculator_strategy: type[ReadinessCalculatorStrategy] = readiness_calculator_strategy
        # Components
        self._components: dict[str, ComponentInstanceType] = {}
        self._components_status: dict[ComponentInstanceKey, Status] = {}
        self._components_subjects: dict[ComponentInstanceKey, Subject[Status]] = {}
        # Observers
        self._status_subject: Subject[StatusUpdateEvent] = Subject()

    def _compute_status(self) -> None:
        """Compute the status."""
        # Health
        previous_health: HealthStatusEnum = self._health_status
        new_health: HealthStatusEnum = self._health_calculator_strategy(
            components_status=self._components_status
        ).calculate()
        # Readiness
        previous_readiness: ReadinessStatusEnum = self._readiness_status
        new_readiness: ReadinessStatusEnum = self._readiness_calculator_strategy(
            components_status=self._components_status
        ).calculate()
        # Update the status if needed
        if previous_health != new_health or previous_readiness != new_readiness:
            logger.info(
                "Status updated: health=%s, readiness=%s",
                new_health,
                new_readiness,
            )
            self._health_status = new_health
            self._readiness_status = new_readiness
            self._status_subject.on_next(
                StatusUpdateEvent(
                    health_status=new_health,
                    previous_health_status=previous_health,
                    readiness_status=new_readiness,
                    previous_readiness_status=previous_readiness,
                    triggered_at=datetime.datetime.now(),
                )
            )

    def get_status(self) -> Status:
        """Get the status.

        Returns:
            Status: The status.
        """
        return Status(
            health=self._health_status,
            readiness=self._readiness_status,
        )

    def get_components_status_by_type(self) -> dict[ComponentTypeEnum, dict[ComponentInstanceKey, Status]]:
        """Get the components status.

        Returns:
            dict[str, dict[str, Status]]: The components status.
        """
        result: dict[ComponentTypeEnum, dict[ComponentInstanceKey, Status]] = {}
        for component_instance in self._components.values():
            component_type: ComponentTypeEnum = component_instance.component_type
            if component_type not in result:
                result[component_type] = {}
            result[component_type][component_instance.key] = self._components_status[component_instance.key]
        return result

    def _on_next_for_component_instance(self, component_instance: ComponentInstanceType, event: Status) -> None:
        """On next subscribe for all component instances updates.

        Args:
            component_instance (ComponentInstanceType): The component instance.
            event (Status): The status event.

        Raises:
            ComponentRegistrationError: If the component instance is not registered.
        """
        # Check if the component instance is registered
        if component_instance.key not in self._components_status:
            raise ComponentRegistrationError(component_instance=component_instance)

        # Update the component instance status
        self._components_status[component_instance.key] = Status(
            health=event["health"],
            readiness=event["readiness"],
        )

        # Compute the status
        self._compute_status()

    def _register_component_instance_internaly(self, component_instance: ComponentInstanceType) -> None:
        """Register the component instance internally.

        Args:
            component_instance (ComponentInstanceType): The component instance.

        Raises:
            ComponentRegistrationError: If the component instance is already registered.
        """
        # Check if the component instance is already registered
        if component_instance.key in self._components:
            raise ComponentRegistrationError(component_instance=component_instance)
        # Register the component instance
        self._components[component_instance.key] = component_instance
        # Register the component instance status
        self._components_status[component_instance.key] = Status(
            health=HealthStatusEnum.HEALTHY,
            readiness=ReadinessStatusEnum.NOT_READY,
        )

    def _create_and_subscribe_to_component_instance_subject(
        self, component_instance: ComponentInstanceType
    ) -> Subject[Status]:
        """Create and subscribe to the component instance subject.

        Args:
            component_instance (ComponentInstanceType): The component instance.

        Returns:
            Subject[Status]: The observer.

        Raises:
            ComponentRegistrationError: If the component instance is already registered.
        """

        # Setup the subject and subscribe to the subject
        def on_next(event: Status) -> None:
            """Currying the on_next method for the component instance and delegate to the service method."""
            self._on_next_for_component_instance(
                component_instance=component_instance,
                event=event,
            )

        subject: Subject[Status] = Subject()
        # Check if the component instance is already registered
        if component_instance.key in self._components_subjects:
            raise ComponentRegistrationError(component_instance=component_instance)
        # Register the component instance subject
        self._components_subjects[component_instance.key] = subject
        subject.subscribe(on_next=on_next)

        return subject

    def register_component_instance(
        self,
        component_instance: ComponentInstanceType,
    ) -> Subject[Status]:
        """Register the component instance to the status service.

        It will create a subject for the component instance to share status update and
        the status service will subscribe automatically to it.

        Args:
            component_instance (ComponentInstanceType): The component instance.

        Returns:
            Subject[Status]: The observer.

        Raises:
            ComponentRegistrationError: If the component instance is already registered.
        """
        self._register_component_instance_internaly(component_instance=component_instance)
        subject: Subject[Status] = self._create_and_subscribe_to_component_instance_subject(
            component_instance=component_instance
        )
        logger.debug(
            "Component instance registered to the status service key=%s",
            component_instance.key,
            component_instance=component_instance,
        )
        return subject


async def depends_status_service(request: Request) -> StatusService:
    """Get the status service, through fastapi depends."""
    return request.app.state.status_service
