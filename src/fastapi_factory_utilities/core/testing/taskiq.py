"""Taskiq test doubles via ``InMemoryBroker``."""

from typing import Any, cast

from fastapi import FastAPI
from taskiq import InMemoryBroker

from fastapi_factory_utilities.core.plugins.taskiq_plugin.depends import DEPENDS_SCHEDULER_COMPONENT_KEY
from fastapi_factory_utilities.core.plugins.taskiq_plugin.schedulers import SchedulerComponent


def build_in_memory_scheduler_component(
    *,
    name_suffix: str = "test",
    app: FastAPI | None = None,
) -> SchedulerComponent:
    """Build a :class:`SchedulerComponent` wired to ``taskiq.InMemoryBroker``.

    Skips Redis stream / schedule / result backends. Enough for unit tests that
    register tasks and call ``broker``; full scheduler/worker lifecycle stays on
    the Redis testcontainer.

    Args:
        name_suffix: Key prefix (mirrors production ``SchedulerComponent``).
        app: Optional FastAPI app; when set, ``scheduler_component`` is placed on
            ``app.state`` so ``depends_scheduler_component`` resolves.

    Returns:
        A scheduler component with an in-memory broker.
    """
    component = SchedulerComponent(name_suffix=name_suffix)
    broker = InMemoryBroker()
    # ponytail: bypass configure() which hardcodes RedisStreamBroker — ceiling is
    # no schedule source / result backend; upgrade: optional configure_in_memory().
    setattr(component, "_stream_broker", cast(Any, broker))
    if app is not None:
        setattr(app.state, DEPENDS_SCHEDULER_COMPONENT_KEY, component)
    return component
