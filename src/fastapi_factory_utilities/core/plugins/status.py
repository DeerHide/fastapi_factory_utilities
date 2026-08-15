"""Shared StatusService registration for plugins with an external system."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from reactivex import Subject

from fastapi_factory_utilities.core.plugins.state import PluginNotBoundError
from fastapi_factory_utilities.core.services.status.enums import (
    ComponentTypeEnum,
    HealthStatusEnum,
    ReadinessStatusEnum,
)
from fastapi_factory_utilities.core.services.status.types import (
    ComponentInstanceType,
    Status,
)

if TYPE_CHECKING:
    from fastapi_factory_utilities.core.protocols import ApplicationAbstractProtocol
    from fastapi_factory_utilities.core.services.status.services import StatusService


def register_status_component(
    application: ApplicationAbstractProtocol,
    *,
    component_type: ComponentTypeEnum,
    identifier: str,
) -> Subject[Status]:
    """Register one StatusService component and return its monitoring subject."""
    status_service: StatusService = application.get_status_service()
    component_instance: ComponentInstanceType = ComponentInstanceType(
        component_type=component_type,
        identifier=identifier,
    )
    return status_service.register_component_instance(component_instance=component_instance)


def report_status(subject: Subject[Status], *, healthy: bool) -> None:
    """Publish healthy/ready or unhealthy/not-ready on ``subject``."""
    subject.on_next(
        value=Status(
            health=HealthStatusEnum.HEALTHY if healthy else HealthStatusEnum.UNHEALTHY,
            readiness=ReadinessStatusEnum.READY if healthy else ReadinessStatusEnum.NOT_READY,
        )
    )


class PluginStatusMixin:
    """Register and drive one StatusService component.

    Mix into ``PluginAbstract`` subclasses. ``_application`` comes from
    ``PluginAbstract``. Disconnects arm not-ready after ``DISCONNECT_GRACE_S``
    so a single reconnect does not flap readiness.
    """

    # ponytail: 15s ≈ three aio_pika default reconnect_interval (5s) attempts.
    DISCONNECT_GRACE_S: float = 15.0

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize status fields; ``PluginAbstract`` still owns ``_application``."""
        super().__init__(*args, **kwargs)
        self._component_instance: ComponentInstanceType | None = None
        self._monitoring_subject: Subject[Status] | None = None
        self._unhealthy_handle: asyncio.TimerHandle | None = None
        self._shutting_down: bool = False

    def _setup_status(self, *, component_type: ComponentTypeEnum, identifier: str) -> None:
        """Register this plugin's StatusService component."""
        application: ApplicationAbstractProtocol | None = getattr(self, "_application", None)
        if application is None:
            raise PluginNotBoundError("Plugin used before set_application.")
        self._component_instance = ComponentInstanceType(
            component_type=component_type,
            identifier=identifier,
        )
        self._monitoring_subject = application.get_status_service().register_component_instance(
            component_instance=self._component_instance
        )

    def _report_healthy(self) -> None:
        """Mark the component healthy and ready."""
        self._disarm_unhealthy()
        if self._monitoring_subject is not None:
            report_status(self._monitoring_subject, healthy=True)

    def _report_unhealthy(self) -> None:
        """Mark the component unhealthy and not-ready."""
        if self._monitoring_subject is not None:
            report_status(self._monitoring_subject, healthy=False)

    def _arm_unhealthy(self) -> None:
        """Schedule not-ready after ``DISCONNECT_GRACE_S`` unless recovered."""
        if self._shutting_down:
            return
        self._disarm_unhealthy()
        try:
            loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        except RuntimeError:
            self._report_unhealthy()
            return
        self._unhealthy_handle = loop.call_later(self.DISCONNECT_GRACE_S, self._report_unhealthy)

    def _disarm_unhealthy(self) -> None:
        """Cancel a pending not-ready report."""
        if self._unhealthy_handle is not None:
            self._unhealthy_handle.cancel()
            self._unhealthy_handle = None
