"""Provides helper functions for the OpenTelemetry plugin."""

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.trace import SpanKind
from opentelemetry.util import types

Param = ParamSpec("Param")
RetType = TypeVar("RetType")


def trace_span(
    name: str | None = None,
    context: Context | None = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: types.Attributes = None,
) -> Callable[[Callable[Param, RetType]], Callable[Param, RetType]]:
    """Decorator to trace a function using OpenTelemetry."""

    def decorator(func: Callable[Param, RetType]) -> Callable[Param, RetType]:
        @wraps(wrapped=func)
        def wrapper(*args: Param.args, **kwargs: Param.kwargs) -> RetType:
            # Get Tracer from the instrumented function's module
            tracer: trace.Tracer = trace.get_tracer(instrumenting_module_name=func.__module__)
            # Use the function's name as the span name if no name is provided
            trace_name: str = name if name is not None else func.__name__
            # Start a span with the provided name
            with tracer.start_as_current_span(
                name=trace_name,
                kind=kind,
                context=context,
                attributes=attributes,
            ):
                return func(*args, **kwargs)

        return wrapper

    return decorator
