"""Deprecation warnings for public symbols scheduled for 7.0.0."""

from unittest.mock import MagicMock

import pytest

from fastapi_factory_utilities.core.services.status import (
    ComponentInstanceType,
    ComponentTypeEnum,
    StatusService,
)
from fastapi_factory_utilities.core.utils.exceptions import ExceptionMapper, ExceptionMapping, exception_mapper
from fastapi_factory_utilities.core.utils.status import MonitoredAbstract


def test_exception_mapper_decorator_warns() -> None:
    """``exception_mapper`` names ExceptionMappingContext and 7.0.0."""
    with pytest.warns(DeprecationWarning, match="7.0.0"):

        @exception_mapper(mappings=[])
        def _noop() -> None:
            return None

        _noop()


def test_exception_mapper_class_warns() -> None:
    """``ExceptionMapper`` names ExceptionMappingContext and 7.0.0."""
    with pytest.warns(DeprecationWarning, match="ExceptionMapper"):
        ExceptionMapper(mappings=[ExceptionMapping(source=ValueError, target=RuntimeError)])


def test_monitored_abstract_warns() -> None:
    """``MonitoredAbstract`` names StatusService and 7.0.0."""
    status_service = MagicMock(spec=StatusService)
    with pytest.warns(DeprecationWarning, match="MonitoredAbstract"):
        MonitoredAbstract(
            component_instance=ComponentInstanceType(
                component_type=ComponentTypeEnum.SERVICE,
                identifier="deprecated",
            ),
            status_service=status_service,
        )
