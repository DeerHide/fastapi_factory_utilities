"""Provide utilities for custom exceptions.

This module provides utilities for exception mapping and transformation,
allowing functions to declaratively map raised exceptions to target exception
types with context injection hooks.

Example:
    Basic usage of the exception mapper decorator::

        from fastapi_factory_utilities.core.utils.exceptions import (
            ExceptionMapping,
            exception_mapper,
        )


        @exception_mapper(
            mappings=[
                ExceptionMapping(source=ValueError, target=MyCustomError),
                ExceptionMapping(source=KeyError, target=NotFoundError),
            ],
        )
        def my_function() -> None:
            raise ValueError("Something went wrong")

    Using with instance methods as decorator::

        class UserService:
            def __init__(self, db: Database) -> None:
                self.db = db

            @exception_mapper(
                mappings=[
                    ExceptionMapping(
                        source=KeyError,
                        target=UserNotFoundError,
                        context_hook=lambda exc, target, args, kwargs: {
                            "user_id": kwargs.get("user_id"),
                        },
                    ),
                ],
                generic_context_hook=lambda exc, target, args, kwargs: {
                    "service": args[0].__class__.__name__,  # args[0] is self
                },
            )
            def get_user(self, user_id: str) -> User:
                return self.db.users[user_id]  # KeyError -> UserNotFoundError

    Wrapping inline method calls with ExceptionMapper class::

        from fastapi_factory_utilities.core.utils.exceptions import (
            ExceptionMapper,
            ExceptionMapping,
        )


        class OrderService:
            def __init__(self, repository: Repository) -> None:
                self.repository = repository
                self._mapper = ExceptionMapper(
                    mappings=[
                        ExceptionMapping(source=ValueError, target=OrderError),
                    ],
                )

            def create_order(self, order: Order) -> None:
                # Wrap the repository call with exception mapping
                self._mapper.call(self.repository.save, order)

            async def create_order_async(self, order: Order) -> None:
                # Wrap async repository call
                await self._mapper.call(self.repository.save_async, order)

    Using context managers for one-off exception mapping::

        from fastapi_factory_utilities.core.utils.exceptions import (
            ExceptionMappingContext,
            ExceptionMapping,
        )


        # Sync context manager
        with ExceptionMappingContext(
            mappings=[ExceptionMapping(source=ValueError, target=MyError)],
        ):
            risky_operation()

        # Async context manager
        async with ExceptionMappingContext(
            mappings=[ExceptionMapping(source=ValueError, target=MyError)],
        ):
            await async_risky_operation()

Attributes:
    ExceptionContextHook: Type alias for exception context hooks.
    ExceptionMapping: Dataclass for defining exception mappings.
    ExceptionMapper: Class for wrapping method calls with exception mapping.
    ExceptionMappingContext: Context manager for exception mapping.
    exception_mapper: Decorator for mapping exceptions.
"""

import asyncio
from collections.abc import Awaitable, Callable, Coroutine, Sequence
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Literal, ParamSpec, TypeVar, overload

# Type variables for preserving function signatures
Param = ParamSpec("Param")
RetTypeT = TypeVar("RetTypeT")

# Type alias for exception context hooks
# Hooks can be sync (returning dict) or async (returning Awaitable[dict])
ExceptionContextHook = Callable[
    [Exception, type[Exception], tuple[Any, ...], dict[str, Any]],
    dict[str, Any] | Awaitable[dict[str, Any]],
]
"""Callable type for exception context hooks.

A context hook receives the original exception, target exception type,
and the function's positional and keyword arguments. It returns a dictionary
of context to be passed to the target exception constructor.

Args:
    exception: The original caught exception.
    target_type: The target exception type that will be raised.
    args: The positional arguments passed to the decorated function.
    kwargs: The keyword arguments passed to the decorated function.

Returns:
    A dictionary of context to pass to the target exception constructor.
    Can return an Awaitable[dict] for async hooks.
"""


@dataclass(frozen=True, slots=True)
class ExceptionMapping:
    """Define a mapping from a source exception type to a target exception type.

    This dataclass defines how a specific exception type should be transformed
    to another exception type when caught by the exception_mapper decorator.

    Attributes:
        source: The source exception type to catch.
        target: The target exception type to raise.
        context_hook: Optional hook to inject context into the target exception.
            If provided, this hook is called after the generic hook (if any)
            and its result is merged with the generic context (specific overrides).

    Example:
        Creating a basic mapping::

            mapping = ExceptionMapping(
                source=ValueError,
                target=ValidationError,
            )

        Creating a mapping with a custom context hook::

            def add_validation_context(
                exc: Exception,
                target: type[Exception],
                args: tuple[Any, ...],
                kwargs: dict[str, Any],
            ) -> dict[str, Any]:
                return {"validation_field": kwargs.get("field_name")}


            mapping = ExceptionMapping(
                source=ValueError,
                target=ValidationError,
                context_hook=add_validation_context,
            )
    """

    source: type[Exception]
    target: type[Exception]
    context_hook: ExceptionContextHook | None = field(default=None)


async def _resolve_hook_result(  # noqa: PLR0913
    hook: ExceptionContextHook,
    exception: Exception,
    target_type: type[Exception],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    is_async_context: bool,
) -> dict[str, Any]:
    """Resolve the result of a context hook, handling both sync and async hooks.

    Args:
        hook: The context hook to execute.
        exception: The original caught exception.
        target_type: The target exception type.
        args: The positional arguments passed to the decorated function.
        kwargs: The keyword arguments passed to the decorated function.
        is_async_context: Whether we are in an async context.

    Returns:
        The resolved dictionary from the hook.

    Raises:
        TypeError: If an async hook is used in a sync context.
    """
    result = hook(exception, target_type, args, kwargs)

    if asyncio.iscoroutine(result):
        if not is_async_context:
            # Close the coroutine to avoid RuntimeWarning
            result.close()
            raise TypeError(
                f'Async context hook "{hook.__name__ if hasattr(hook, "__name__") else hook}" '
                "cannot be used with a synchronous decorated function. "
                "Use a synchronous hook or decorate an async function."
            )
        return await result

    return result  # type: ignore[return-value]


def _resolve_hook_result_sync(
    hook: ExceptionContextHook,
    exception: Exception,
    target_type: type[Exception],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Resolve the result of a context hook synchronously.

    Args:
        hook: The context hook to execute.
        exception: The original caught exception.
        target_type: The target exception type.
        args: The positional arguments passed to the decorated function.
        kwargs: The keyword arguments passed to the decorated function.

    Returns:
        The resolved dictionary from the hook.

    Raises:
        TypeError: If an async hook is used in a sync context.
    """
    result = hook(exception, target_type, args, kwargs)

    if asyncio.iscoroutine(result):
        # Close the coroutine to avoid RuntimeWarning
        result.close()
        raise TypeError(
            f'Async context hook "{hook.__name__ if hasattr(hook, "__name__") else hook}" '
            "cannot be used with a synchronous decorated function. "
            "Use a synchronous hook or decorate an async function."
        )

    return result  # type: ignore[return-value]


def _build_context_sync(
    exception: Exception,
    mapping: ExceptionMapping,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    generic_hook: ExceptionContextHook | None,
) -> dict[str, Any]:
    """Build the context dictionary for the target exception synchronously.

    Executes the generic hook first (if provided), then the mapping-specific
    hook (if provided). The specific hook's result is merged on top of the
    generic result (specific values override generic).

    Args:
        exception: The original caught exception.
        mapping: The exception mapping being applied.
        args: The positional arguments passed to the decorated function.
        kwargs: The keyword arguments passed to the decorated function.
        generic_hook: Optional generic context hook.

    Returns:
        The merged context dictionary.
    """
    context: dict[str, Any] = {}

    # Execute generic hook first
    if generic_hook is not None:
        generic_context = _resolve_hook_result_sync(
            hook=generic_hook,
            exception=exception,
            target_type=mapping.target,
            args=args,
            kwargs=kwargs,
        )
        if generic_context is not None:
            context.update(generic_context)

    # Execute mapping-specific hook and merge (specific overrides generic)
    if mapping.context_hook is not None:
        specific_context = _resolve_hook_result_sync(
            hook=mapping.context_hook,
            exception=exception,
            target_type=mapping.target,
            args=args,
            kwargs=kwargs,
        )
        if specific_context is not None:
            context.update(specific_context)

    return context


async def _build_context_async(
    exception: Exception,
    mapping: ExceptionMapping,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    generic_hook: ExceptionContextHook | None,
) -> dict[str, Any]:
    """Build the context dictionary for the target exception asynchronously.

    Executes the generic hook first (if provided), then the mapping-specific
    hook (if provided). The specific hook's result is merged on top of the
    generic result (specific values override generic).

    Args:
        exception: The original caught exception.
        mapping: The exception mapping being applied.
        args: The positional arguments passed to the decorated function.
        kwargs: The keyword arguments passed to the decorated function.
        generic_hook: Optional generic context hook.

    Returns:
        The merged context dictionary.
    """
    context: dict[str, Any] = {}

    # Execute generic hook first
    if generic_hook is not None:
        generic_context = await _resolve_hook_result(
            hook=generic_hook,
            exception=exception,
            target_type=mapping.target,
            args=args,
            kwargs=kwargs,
            is_async_context=True,
        )
        if generic_context is not None:
            context.update(generic_context)

    # Execute mapping-specific hook and merge (specific overrides generic)
    if mapping.context_hook is not None:
        specific_context = await _resolve_hook_result(
            hook=mapping.context_hook,
            exception=exception,
            target_type=mapping.target,
            args=args,
            kwargs=kwargs,
            is_async_context=True,
        )
        if specific_context is not None:
            context.update(specific_context)

    return context


def exception_mapper(
    mappings: Sequence[ExceptionMapping],
    *,
    generic_context_hook: ExceptionContextHook | None = None,
) -> Callable[[Callable[Param, RetTypeT]], Callable[Param, RetTypeT]]:
    """Decorate a function to map raised exceptions to target exception types.

    This decorator catches exceptions matching the source types defined in the
    mappings and re-raises them as the corresponding target exception types.
    The original exception is preserved via exception chaining (``raise ... from``).

    Mappings are evaluated in order - the first matching mapping wins. Place
    more specific exception types before more general ones to ensure correct
    matching (e.g., ``KeyError`` before ``LookupError``).

    Unmapped exceptions propagate unchanged.

    Args:
        mappings: Sequence of ExceptionMapping defining source-to-target mappings.
            Order matters - first match wins.
        generic_context_hook: Optional hook called for all mapped exceptions.
            Executed before mapping-specific hooks. Result is merged with
            specific hook result (specific values override generic).

    Returns:
        A decorator that wraps the function with exception mapping logic.

    Raises:
        TypeError: If an async context hook is used with a sync decorated function.

    Example:
        Basic exception mapping::

            @exception_mapper(
                mappings=[
                    ExceptionMapping(source=KeyError, target=NotFoundError),
                    ExceptionMapping(source=ValueError, target=ValidationError),
                ],
            )
            def get_item(key: str) -> Item:
                return items[key]  # KeyError -> NotFoundError

        With context hooks::

            def generic_hook(
                exc: Exception,
                target: type[Exception],
                args: tuple[Any, ...],
                kwargs: dict[str, Any],
            ) -> dict[str, Any]:
                return {"original_message": str(exc)}


            def specific_hook(
                exc: Exception,
                target: type[Exception],
                args: tuple[Any, ...],
                kwargs: dict[str, Any],
            ) -> dict[str, Any]:
                return {"key": kwargs.get("key")}


            @exception_mapper(
                mappings=[
                    ExceptionMapping(
                        source=KeyError,
                        target=NotFoundError,
                        context_hook=specific_hook,
                    ),
                ],
                generic_context_hook=generic_hook,
            )
            def get_item(key: str) -> Item:
                return items[key]

        Async function with async hooks::

            async def async_hook(
                exc: Exception,
                target: type[Exception],
                args: tuple[Any, ...],
                kwargs: dict[str, Any],
            ) -> dict[str, Any]:
                context = await fetch_context()
                return {"context": context}


            @exception_mapper(
                mappings=[
                    ExceptionMapping(source=ValueError, target=CustomError),
                ],
                generic_context_hook=async_hook,
            )
            async def async_operation() -> None: ...
    """

    def decorator(func: Callable[Param, RetTypeT]) -> Callable[Param, RetTypeT]:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Param.args, **kwargs: Param.kwargs) -> RetTypeT:
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    # Iterate mappings in order - first match wins
                    for mapping in mappings:
                        if isinstance(exc, mapping.source):
                            # Build context from hooks
                            context = await _build_context_async(
                                exception=exc,
                                mapping=mapping,
                                args=args,
                                kwargs=kwargs,
                                generic_hook=generic_context_hook,
                            )
                            # Raise target exception with message and context, chained from original
                            raise mapping.target(str(exc), **context) from exc
                    # Unmapped exceptions propagate unchanged
                    raise

            return async_wrapper  # type: ignore[return-value]

        else:

            @wraps(func)
            def sync_wrapper(*args: Param.args, **kwargs: Param.kwargs) -> RetTypeT:
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    # Iterate mappings in order - first match wins
                    for mapping in mappings:
                        if isinstance(exc, mapping.source):
                            # Build context from hooks
                            context = _build_context_sync(
                                exception=exc,
                                mapping=mapping,
                                args=args,
                                kwargs=kwargs,
                                generic_hook=generic_context_hook,
                            )
                            # Raise target exception with message and context, chained from original
                            raise mapping.target(str(exc), **context) from exc
                    # Unmapped exceptions propagate unchanged
                    raise

            return sync_wrapper

    return decorator


class ExceptionMapper:
    """Wrap method calls with exception mapping logic.

    This class provides a reusable way to wrap arbitrary method or function calls
    with exception mapping, without requiring decoration at definition time.
    Useful when you want to map exceptions from calls to external code or
    repository methods.

    Attributes:
        mappings: Sequence of ExceptionMapping defining source-to-target mappings.
        generic_context_hook: Optional hook called for all mapped exceptions.

    Example:
        Basic usage wrapping repository calls::

            class OrderService:
                def __init__(self, repository: Repository) -> None:
                    self.repository = repository
                    self._mapper = ExceptionMapper(
                        mappings=[
                            ExceptionMapping(source=ValueError, target=OrderError),
                            ExceptionMapping(source=KeyError, target=NotFoundError),
                        ],
                    )

                def save_order(self, order: Order) -> None:
                    self._mapper.call(self.repository.save, order)

                def get_order(self, order_id: str) -> Order:
                    return self._mapper.call(self.repository.get, order_id)

                async def fetch_order_async(self, order_id: str) -> Order:
                    # Same call() method works for async - just await the result
                    return await self._mapper.call(self.repository.fetch_async, order_id)

        With context hooks::

            def add_context(
                exc: Exception,
                target: type[Exception],
                args: tuple[Any, ...],
                kwargs: dict[str, Any],
            ) -> dict[str, Any]:
                return {"original_error": str(exc)}


            mapper = ExceptionMapper(
                mappings=[ExceptionMapping(source=ValueError, target=MyError)],
                generic_context_hook=add_context,
            )
            mapper.call(some_function, arg1, arg2, kwarg1=value)
    """

    def __init__(
        self,
        mappings: Sequence[ExceptionMapping],
        *,
        generic_context_hook: ExceptionContextHook | None = None,
    ) -> None:
        """Initialize the ExceptionMapper.

        Args:
            mappings: Sequence of ExceptionMapping defining source-to-target mappings.
                Order matters - first match wins.
            generic_context_hook: Optional hook called for all mapped exceptions.
                Executed before mapping-specific hooks. Result is merged with
                specific hook result (specific values override generic).
        """
        self._mappings = mappings
        self._generic_context_hook = generic_context_hook

    @overload
    def call(
        self,
        func: Callable[..., Coroutine[Any, Any, RetTypeT]],
        *args: Any,
        **kwargs: Any,
    ) -> Coroutine[Any, Any, RetTypeT]: ...

    @overload
    def call(
        self,
        func: Callable[..., RetTypeT],
        *args: Any,
        **kwargs: Any,
    ) -> RetTypeT: ...

    def call(  # type: ignore[misc]
        self,
        func: Callable[..., RetTypeT] | Callable[..., Coroutine[Any, Any, RetTypeT]],
        *args: Any,
        **kwargs: Any,
    ) -> RetTypeT | Coroutine[Any, Any, RetTypeT]:
        """Call a function with exception mapping applied.

        Automatically detects whether the function is async or sync and handles
        it appropriately. For async functions, returns a coroutine that must be
        awaited.

        Args:
            func: The function or method to call (sync or async).
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            For sync functions: The return value directly.
            For async functions: A coroutine that must be awaited.

        Raises:
            The mapped target exception if a source exception is caught.
            TypeError: If an async hook is used with a sync function.

        Example:
            Sync function::

                result = mapper.call(sync_func, arg1, arg2)

            Async function::

                result = await mapper.call(async_func, arg1, arg2)
        """
        if asyncio.iscoroutinefunction(func):
            return self._call_async(func, *args, **kwargs)
        return self._call_sync(func, *args, **kwargs)  # type: ignore[return-value]

    def _call_sync(
        self,
        func: Callable[..., RetTypeT],
        *args: Any,
        **kwargs: Any,
    ) -> RetTypeT:
        """Call a sync function with exception mapping applied.

        Args:
            func: The sync function or method to call.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            The return value of the called function.

        Raises:
            The mapped target exception if a source exception is caught.
            TypeError: If an async hook is used.
        """
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            for mapping in self._mappings:
                if isinstance(exc, mapping.source):
                    context = _build_context_sync(
                        exception=exc,
                        mapping=mapping,
                        args=args,
                        kwargs=kwargs,
                        generic_hook=self._generic_context_hook,
                    )
                    raise mapping.target(str(exc), **context) from exc
            raise

    async def _call_async(
        self,
        func: Callable[..., Coroutine[Any, Any, RetTypeT]],
        *args: Any,
        **kwargs: Any,
    ) -> RetTypeT:
        """Call an async function with exception mapping applied.

        Args:
            func: The async function or method to call.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            The return value of the called async function.

        Raises:
            The mapped target exception if a source exception is caught.
        """
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            for mapping in self._mappings:
                if isinstance(exc, mapping.source):
                    context = await _build_context_async(
                        exception=exc,
                        mapping=mapping,
                        args=args,
                        kwargs=kwargs,
                        generic_hook=self._generic_context_hook,
                    )
                    raise mapping.target(str(exc), **context) from exc
            raise


class ExceptionMappingContext:
    """Context manager for exception mapping.

    This class provides a context manager interface for wrapping code blocks
    with exception mapping logic. Supports both sync and async context managers.

    For sync hooks in sync context, use the regular `with` statement.
    For async hooks or async code blocks, use `async with`.

    Attributes:
        mappings: Sequence of ExceptionMapping defining source-to-target mappings.
        generic_context_hook: Optional hook called for all mapped exceptions.

    Example:
        Sync context manager::

            with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(source=ValueError, target=ValidationError),
                    ExceptionMapping(source=KeyError, target=NotFoundError),
                ],
            ):
                risky_operation()  # ValueError -> ValidationError

        Async context manager::

            async with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(source=ValueError, target=ValidationError),
                ],
            ):
                await async_risky_operation()

        With context hooks::

            def add_context(
                exc: Exception,
                target: type[Exception],
                args: tuple[Any, ...],
                kwargs: dict[str, Any],
            ) -> dict[str, Any]:
                return {"original_error": str(exc)}


            with ExceptionMappingContext(
                mappings=[ExceptionMapping(source=ValueError, target=MyError)],
                generic_context_hook=add_context,
            ):
                risky_operation()
    """

    def __init__(
        self,
        mappings: Sequence[ExceptionMapping],
        *,
        generic_context_hook: ExceptionContextHook | None = None,
    ) -> None:
        """Initialize the ExceptionMappingContext.

        Args:
            mappings: Sequence of ExceptionMapping defining source-to-target mappings.
                Order matters - first match wins.
            generic_context_hook: Optional hook called for all mapped exceptions.
                Executed before mapping-specific hooks. Result is merged with
                specific hook result (specific values override generic).
        """
        self._mappings = mappings
        self._generic_context_hook = generic_context_hook

    def __enter__(self) -> "ExceptionMappingContext":
        """Enter the sync context manager.

        Returns:
            Self for potential chaining or access to mappings.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> Literal[False]:
        """Exit the sync context manager, mapping exceptions if necessary.

        Args:
            exc_type: The exception type, if an exception was raised.
            exc_val: The exception instance, if an exception was raised.
            exc_tb: The traceback, if an exception was raised.

        Returns:
            False to propagate exceptions (mapped or unmapped).
            We re-raise mapped exceptions, so we always return False.

        Raises:
            The mapped target exception if a source exception is caught.
            TypeError: If an async hook is used in sync context.
        """
        if exc_val is None or exc_type is None:
            return False

        # Only handle Exception subclasses, not BaseException (e.g., KeyboardInterrupt)
        if not isinstance(exc_val, Exception):
            return False

        for mapping in self._mappings:
            if isinstance(exc_val, mapping.source):
                context = _build_context_sync(
                    exception=exc_val,
                    mapping=mapping,
                    args=(),
                    kwargs={},
                    generic_hook=self._generic_context_hook,
                )
                raise mapping.target(str(exc_val), **context) from exc_val

        # Unmapped exceptions propagate unchanged
        return False

    async def __aenter__(self) -> "ExceptionMappingContext":
        """Enter the async context manager.

        Returns:
            Self for potential chaining or access to mappings.
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> Literal[False]:
        """Exit the async context manager, mapping exceptions if necessary.

        Args:
            exc_type: The exception type, if an exception was raised.
            exc_val: The exception instance, if an exception was raised.
            exc_tb: The traceback, if an exception was raised.

        Returns:
            False to propagate exceptions (mapped or unmapped).
            We re-raise mapped exceptions, so we always return False.

        Raises:
            The mapped target exception if a source exception is caught.
        """
        if exc_val is None or exc_type is None:
            return False

        # Only handle Exception subclasses, not BaseException (e.g., KeyboardInterrupt)
        if not isinstance(exc_val, Exception):
            return False

        for mapping in self._mappings:
            if isinstance(exc_val, mapping.source):
                context = await _build_context_async(
                    exception=exc_val,
                    mapping=mapping,
                    args=(),
                    kwargs={},
                    generic_hook=self._generic_context_hook,
                )
                raise mapping.target(str(exc_val), **context) from exc_val

        # Unmapped exceptions propagate unchanged
        return False


__all__: list[str] = [
    "ExceptionContextHook",
    "ExceptionMapper",
    "ExceptionMapping",
    "ExceptionMappingContext",
    "exception_mapper",
]
