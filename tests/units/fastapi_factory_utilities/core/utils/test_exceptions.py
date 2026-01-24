"""Tests for fastapi_factory_utilities.core.utils.exceptions."""
# pylint: disable=unused-argument

import asyncio
from typing import Any

import pytest

from fastapi_factory_utilities.core.exceptions import FastAPIFactoryUtilitiesError
from fastapi_factory_utilities.core.utils.exceptions import (
    ExceptionMapper,
    ExceptionMapping,
    ExceptionMappingContext,
    exception_mapper,
)


# Test exception classes (prefixed with underscore to avoid pytest collection)
class _SourceError(Exception):
    """Source exception for testing."""


class _AnotherSourceError(Exception):
    """Another source exception for testing."""


class _TargetError(FastAPIFactoryUtilitiesError):
    """Target exception for testing."""

    # Exclude internal attributes from context property
    _INTERNAL_ATTRS = frozenset(
        {
            "message",
            "level",
            "args",
            "_INTERNAL_ATTRS",
            "DEFAULT_LOGGING_LEVEL",
            "DEFAULT_MESSAGE",
            "FILTERED_ATTRIBUTES",
        }
    )

    @property
    def context(self) -> dict[str, Any]:
        """Return custom context attributes as a dictionary."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_") and k not in self._INTERNAL_ATTRS}


class _AnotherTargetError(FastAPIFactoryUtilitiesError):
    """Another target exception for testing."""

    # Exclude internal attributes from context property
    _INTERNAL_ATTRS = frozenset(
        {
            "message",
            "level",
            "args",
            "_INTERNAL_ATTRS",
            "DEFAULT_LOGGING_LEVEL",
            "DEFAULT_MESSAGE",
            "FILTERED_ATTRIBUTES",
        }
    )

    @property
    def context(self) -> dict[str, Any]:
        """Return custom context attributes as a dictionary."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_") and k not in self._INTERNAL_ATTRS}


class _ChildSourceError(_SourceError):
    """Child exception of _SourceError for testing inheritance."""


class TestExceptionMapping:
    """Test cases for the ExceptionMapping dataclass."""

    def test_create_mapping_without_hook(self) -> None:
        """Test creating an exception mapping without a context hook."""
        # Arrange & Act
        mapping = ExceptionMapping(
            source=_SourceError,
            target=_TargetError,
        )

        # Assert
        assert mapping.source is _SourceError
        assert mapping.target is _TargetError
        assert mapping.context_hook is None

    def test_create_mapping_with_hook(self) -> None:
        """Test creating an exception mapping with a context hook."""

        # Arrange
        def hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"key": "value"}

        # Act
        mapping = ExceptionMapping(
            source=_SourceError,
            target=_TargetError,
            context_hook=hook,
        )

        # Assert
        assert mapping.source is _SourceError
        assert mapping.target is _TargetError
        assert mapping.context_hook is hook

    def test_mapping_is_frozen(self) -> None:
        """Test that ExceptionMapping is immutable (frozen)."""
        # Arrange
        mapping = ExceptionMapping(
            source=_SourceError,
            target=_TargetError,
        )

        # Act & Assert
        with pytest.raises(AttributeError):
            mapping.source = _AnotherSourceError  # type: ignore[misc]


class TestExceptionMapperSync:
    """Test cases for the exception_mapper decorator with synchronous functions."""

    def test_maps_exception_to_target(self) -> None:
        """Test that a source exception is mapped to the target exception."""

        # Arrange
        @exception_mapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )
        def func() -> None:
            raise _SourceError("original message")

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            func()

        assert str(exc_info.value) == "original message"
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, _SourceError)

    def test_maps_exception_with_context_hook(self) -> None:
        """Test that context hook adds context to target exception."""

        # Arrange
        def context_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"user_id": kwargs.get("user_id")}

        @exception_mapper(
            mappings=[
                ExceptionMapping(
                    source=_SourceError,
                    target=_TargetError,
                    context_hook=context_hook,
                ),
            ],
        )
        def func(user_id: str) -> None:
            raise _SourceError("not found")

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            func(user_id="123")

        assert exc_info.value.context == {"user_id": "123"}

    def test_maps_exception_with_generic_context_hook(self) -> None:
        """Test that generic context hook adds context to all mappings."""

        # Arrange
        def generic_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"generic": "context"}

        @exception_mapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
            generic_context_hook=generic_hook,
        )
        def func() -> None:
            raise _SourceError("error")

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            func()

        assert exc_info.value.context == {"generic": "context"}

    def test_context_hooks_are_merged(self) -> None:
        """Test that mapping-specific and generic hooks are merged."""

        # Arrange
        def specific_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"specific": "value"}

        def generic_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"generic": "value"}

        @exception_mapper(
            mappings=[
                ExceptionMapping(
                    source=_SourceError,
                    target=_TargetError,
                    context_hook=specific_hook,
                ),
            ],
            generic_context_hook=generic_hook,
        )
        def func() -> None:
            raise _SourceError("error")

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            func()

        assert exc_info.value.context == {"generic": "value", "specific": "value"}

    def test_specific_hook_overrides_generic(self) -> None:
        """Test that specific hook values override generic hook values."""

        # Arrange
        def specific_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"key": "specific"}

        def generic_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"key": "generic"}

        @exception_mapper(
            mappings=[
                ExceptionMapping(
                    source=_SourceError,
                    target=_TargetError,
                    context_hook=specific_hook,
                ),
            ],
            generic_context_hook=generic_hook,
        )
        def func() -> None:
            raise _SourceError("error")

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            func()

        assert exc_info.value.context["key"] == "specific"

    def test_unmapped_exception_propagates(self) -> None:
        """Test that unmapped exceptions propagate unchanged."""

        # Arrange
        @exception_mapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )
        def func() -> None:
            raise _AnotherSourceError("different error")

        # Act & Assert
        with pytest.raises(_AnotherSourceError) as exc_info:
            func()

        assert str(exc_info.value) == "different error"

    def test_no_exception_returns_normally(self) -> None:
        """Test that function returns normally when no exception is raised."""

        # Arrange
        @exception_mapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )
        def func() -> str:
            return "success"

        # Act
        result = func()

        # Assert
        assert result == "success"

    def test_multiple_mappings(self) -> None:
        """Test that multiple mappings work correctly."""

        # Arrange
        @exception_mapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
                ExceptionMapping(source=_AnotherSourceError, target=_AnotherTargetError),
            ],
        )
        def func(raise_another: bool) -> None:
            if raise_another:
                raise _AnotherSourceError("another error")
            raise _SourceError("source error")

        # Act & Assert - first mapping
        with pytest.raises(_TargetError):
            func(raise_another=False)

        # Act & Assert - second mapping
        with pytest.raises(_AnotherTargetError):
            func(raise_another=True)

    def test_maps_child_exception(self) -> None:
        """Test that child exceptions are mapped via parent mapping."""

        # Arrange
        @exception_mapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )
        def func() -> None:
            raise _ChildSourceError("child error")

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            func()

        assert isinstance(exc_info.value.__cause__, _ChildSourceError)

    def test_preserves_function_metadata(self) -> None:
        """Test that decorated function preserves metadata."""

        # Arrange
        @exception_mapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )
        def func_with_docs() -> str:
            """This is a docstring."""
            return "value"

        # Assert
        assert func_with_docs.__name__ == "func_with_docs"
        assert func_with_docs.__doc__ == "This is a docstring."


class TestExceptionMapperAsync:
    """Test cases for the exception_mapper decorator with async functions."""

    @pytest.mark.asyncio
    async def test_maps_exception_to_target(self) -> None:
        """Test that a source exception is mapped to the target exception."""

        # Arrange
        @exception_mapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )
        async def func() -> None:
            raise _SourceError("original message")

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            await func()

        assert str(exc_info.value) == "original message"
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, _SourceError)

    @pytest.mark.asyncio
    async def test_maps_exception_with_context_hook(self) -> None:
        """Test that context hook adds context to target exception."""

        # Arrange
        def context_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"user_id": kwargs.get("user_id")}

        @exception_mapper(
            mappings=[
                ExceptionMapping(
                    source=_SourceError,
                    target=_TargetError,
                    context_hook=context_hook,
                ),
            ],
        )
        async def func(user_id: str) -> None:
            raise _SourceError("not found")

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            await func(user_id="123")

        assert exc_info.value.context == {"user_id": "123"}

    @pytest.mark.asyncio
    async def test_maps_exception_with_generic_context_hook(self) -> None:
        """Test that generic context hook adds context to all mappings."""

        # Arrange
        def generic_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"generic": "context"}

        @exception_mapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
            generic_context_hook=generic_hook,
        )
        async def func() -> None:
            raise _SourceError("error")

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            await func()

        assert exc_info.value.context == {"generic": "context"}

    @pytest.mark.asyncio
    async def test_context_hooks_are_merged(self) -> None:
        """Test that mapping-specific and generic hooks are merged."""

        # Arrange
        def specific_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"specific": "value"}

        def generic_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"generic": "value"}

        @exception_mapper(
            mappings=[
                ExceptionMapping(
                    source=_SourceError,
                    target=_TargetError,
                    context_hook=specific_hook,
                ),
            ],
            generic_context_hook=generic_hook,
        )
        async def func() -> None:
            raise _SourceError("error")

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            await func()

        assert exc_info.value.context == {"generic": "value", "specific": "value"}

    @pytest.mark.asyncio
    async def test_unmapped_exception_propagates(self) -> None:
        """Test that unmapped exceptions propagate unchanged."""

        # Arrange
        @exception_mapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )
        async def func() -> None:
            raise _AnotherSourceError("different error")

        # Act & Assert
        with pytest.raises(_AnotherSourceError) as exc_info:
            await func()

        assert str(exc_info.value) == "different error"

    @pytest.mark.asyncio
    async def test_no_exception_returns_normally(self) -> None:
        """Test that function returns normally when no exception is raised."""

        # Arrange
        @exception_mapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )
        async def func() -> str:
            return "success"

        # Act
        result = await func()

        # Assert
        assert result == "success"


class TestExceptionMapperClass:
    """Test cases for the ExceptionMapper class."""

    def test_call_maps_exception(self) -> None:
        """Test that call() maps exceptions correctly."""

        # Arrange
        def func() -> None:
            raise _SourceError("error")

        mapper = ExceptionMapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            mapper.call(func)

        assert str(exc_info.value) == "error"

    def test_call_with_args_and_kwargs(self) -> None:
        """Test that call() passes args and kwargs correctly."""

        # Arrange
        def func(a: int, b: str, c: bool = False) -> tuple[int, str, bool]:
            return (a, b, c)

        mapper = ExceptionMapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )

        # Act
        result = mapper.call(func, 1, "test", c=True)

        # Assert
        assert result == (1, "test", True)

    def test_call_with_context_hook(self) -> None:
        """Test that call() applies context hooks correctly."""

        # Arrange
        def context_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"arg": args[0]}

        def func(value: str) -> None:
            raise _SourceError("error")

        mapper = ExceptionMapper(
            mappings=[
                ExceptionMapping(
                    source=_SourceError,
                    target=_TargetError,
                    context_hook=context_hook,
                ),
            ],
        )

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            mapper.call(func, "test_value")

        assert exc_info.value.context == {"arg": "test_value"}

    @pytest.mark.asyncio
    async def test_call_async_maps_exception(self) -> None:
        """Test that call() maps exceptions for async functions."""

        # Arrange
        async def func() -> None:
            raise _SourceError("async error")

        mapper = ExceptionMapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            await mapper.call(func)

        assert str(exc_info.value) == "async error"

    @pytest.mark.asyncio
    async def test_call_async_with_context_hook(self) -> None:
        """Test that call() applies context hooks for async functions."""

        # Arrange
        def context_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"kwarg": kwargs.get("key")}

        async def func(key: str) -> None:
            raise _SourceError("error")

        mapper = ExceptionMapper(
            mappings=[
                ExceptionMapping(
                    source=_SourceError,
                    target=_TargetError,
                    context_hook=context_hook,
                ),
            ],
        )

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            await mapper.call(func, key="value")

        assert exc_info.value.context == {"kwarg": "value"}

    def test_call_unmapped_exception_propagates(self) -> None:
        """Test that unmapped exceptions propagate unchanged."""

        # Arrange
        def func() -> None:
            raise _AnotherSourceError("unmapped")

        mapper = ExceptionMapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )

        # Act & Assert
        with pytest.raises(_AnotherSourceError) as exc_info:
            mapper.call(func)

        assert str(exc_info.value) == "unmapped"

    def test_call_returns_value(self) -> None:
        """Test that call() returns the function's return value."""

        # Arrange
        def func() -> str:
            return "success"

        mapper = ExceptionMapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )

        # Act
        result = mapper.call(func)

        # Assert
        assert result == "success"

    @pytest.mark.asyncio
    async def test_call_async_returns_value(self) -> None:
        """Test that call() returns the async function's return value."""

        # Arrange
        async def func() -> str:
            return "async success"

        mapper = ExceptionMapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )

        # Act
        result = await mapper.call(func)

        # Assert
        assert result == "async success"


class TestAsyncContextHooks:
    """Test cases for async context hooks."""

    @pytest.mark.asyncio
    async def test_async_context_hook_with_decorator(self) -> None:
        """Test that async context hooks work with the decorator."""

        # Arrange
        async def async_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"async": True}

        @exception_mapper(
            mappings=[
                ExceptionMapping(
                    source=_SourceError,
                    target=_TargetError,
                    context_hook=async_hook,
                ),
            ],
        )
        async def func() -> None:
            raise _SourceError("error")

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            await func()

        assert exc_info.value.context == {"async": True}

    @pytest.mark.asyncio
    async def test_async_generic_context_hook_with_decorator(self) -> None:
        """Test that async generic context hooks work with the decorator."""

        # Arrange
        async def async_generic_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"generic_async": True}

        @exception_mapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
            generic_context_hook=async_generic_hook,
        )
        async def func() -> None:
            raise _SourceError("error")

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            await func()

        assert exc_info.value.context == {"generic_async": True}

    @pytest.mark.asyncio
    async def test_mixed_sync_async_hooks(self) -> None:
        """Test that sync and async hooks can be mixed."""

        # Arrange
        def sync_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"sync": True}

        async def async_generic_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"async": True}

        @exception_mapper(
            mappings=[
                ExceptionMapping(
                    source=_SourceError,
                    target=_TargetError,
                    context_hook=sync_hook,
                ),
            ],
            generic_context_hook=async_generic_hook,
        )
        async def func() -> None:
            raise _SourceError("error")

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            await func()

        assert exc_info.value.context == {"async": True, "sync": True}

    @pytest.mark.asyncio
    async def test_async_hook_with_mapper_class(self) -> None:
        """Test that async context hooks work with ExceptionMapper class."""

        # Arrange
        async def async_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"from_async_hook": True}

        async def func() -> None:
            raise _SourceError("error")

        mapper = ExceptionMapper(
            mappings=[
                ExceptionMapping(
                    source=_SourceError,
                    target=_TargetError,
                    context_hook=async_hook,
                ),
            ],
        )

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            await mapper.call(func)

        assert exc_info.value.context == {"from_async_hook": True}


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_mappings_list(self) -> None:
        """Test decorator with empty mappings list."""

        # Arrange
        @exception_mapper(mappings=[])
        def func() -> None:
            raise _SourceError("error")

        # Act & Assert - exception should propagate unchanged
        with pytest.raises(_SourceError):
            func()

    def test_hook_returning_none(self) -> None:
        """Test that hook returning None results in empty context."""

        # Arrange
        def hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> None:
            return None

        @exception_mapper(
            mappings=[
                ExceptionMapping(
                    source=_SourceError,
                    target=_TargetError,
                    context_hook=hook,
                ),
            ],
        )
        def func() -> None:
            raise _SourceError("error")

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            func()

        assert exc_info.value.context == {}

    def test_exception_in_sync_context_hook(self) -> None:
        """Test that exceptions in sync context hooks propagate."""

        # Arrange
        def bad_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            raise RuntimeError("hook failed")

        @exception_mapper(
            mappings=[
                ExceptionMapping(
                    source=_SourceError,
                    target=_TargetError,
                    context_hook=bad_hook,
                ),
            ],
        )
        def func() -> None:
            raise _SourceError("error")

        # Act & Assert - the RuntimeError from hook should propagate
        with pytest.raises(RuntimeError) as exc_info:
            func()

        assert str(exc_info.value) == "hook failed"

    @pytest.mark.asyncio
    async def test_exception_in_async_context_hook(self) -> None:
        """Test that exceptions in async context hooks propagate."""

        # Arrange
        async def bad_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            raise RuntimeError("async hook failed")

        @exception_mapper(
            mappings=[
                ExceptionMapping(
                    source=_SourceError,
                    target=_TargetError,
                    context_hook=bad_hook,
                ),
            ],
        )
        async def func() -> None:
            raise _SourceError("error")

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            await func()

        assert str(exc_info.value) == "async hook failed"

    def test_exception_message_preserved(self) -> None:
        """Test that exception message is preserved through mapping."""

        # Arrange
        @exception_mapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )
        def func() -> None:
            raise _SourceError("detailed error message with context")

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            func()

        assert str(exc_info.value) == "detailed error message with context"

    def test_first_matching_mapping_wins(self) -> None:
        """Test that first matching mapping is used when multiple could match."""

        # Arrange
        @exception_mapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
                ExceptionMapping(source=_SourceError, target=_AnotherTargetError),
            ],
        )
        def func() -> None:
            raise _SourceError("error")

        # Act & Assert - first mapping should be used
        with pytest.raises(_TargetError):
            func()

    def test_sync_wrapper_on_sync_function(self) -> None:
        """Test that sync functions stay sync after wrapping."""

        # Arrange
        @exception_mapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )
        def func() -> str:
            return "sync result"

        # Act & Assert
        assert not asyncio.iscoroutinefunction(func)
        assert func() == "sync result"

    @pytest.mark.asyncio
    async def test_async_wrapper_on_async_function(self) -> None:
        """Test that async functions stay async after wrapping."""

        # Arrange
        @exception_mapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )
        async def func() -> str:
            return "async result"

        # Act & Assert
        assert asyncio.iscoroutinefunction(func)
        assert await func() == "async result"


class TestInstanceMethods:
    """Test exception mapper with class instance methods."""

    def test_sync_instance_method(self) -> None:
        """Test decorator on synchronous instance methods."""

        # Arrange
        class Service:
            """Test service class."""

            def __init__(self, name: str) -> None:
                """Initialize the service."""
                self.name = name

            @exception_mapper(
                mappings=[
                    ExceptionMapping(
                        source=_SourceError,
                        target=_TargetError,
                        context_hook=lambda exc, target, args, kwargs: {
                            "service": args[0].name,
                        },
                    ),
                ],
            )
            def method(self) -> None:
                raise _SourceError("error")

        service = Service("TestService")

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            service.method()

        assert exc_info.value.context == {"service": "TestService"}

    @pytest.mark.asyncio
    async def test_async_instance_method(self) -> None:
        """Test decorator on asynchronous instance methods."""

        # Arrange
        class Service:
            """Test service class."""

            def __init__(self, name: str) -> None:
                """Initialize the service."""
                self.name = name

            @exception_mapper(
                mappings=[
                    ExceptionMapping(
                        source=_SourceError,
                        target=_TargetError,
                        context_hook=lambda exc, target, args, kwargs: {
                            "service": args[0].name,
                        },
                    ),
                ],
            )
            async def method(self) -> None:
                raise _SourceError("error")

        service = Service("AsyncService")

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            await service.method()

        assert exc_info.value.context == {"service": "AsyncService"}

    def test_mapper_class_with_instance_method(self) -> None:
        """Test ExceptionMapper class with instance methods."""

        # Arrange
        class Repository:  # pylint: disable=missing-class-docstring
            def save(self, data: str) -> None:
                raise _SourceError("save failed")

        mapper = ExceptionMapper(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )
        repo = Repository()

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            mapper.call(repo.save, "test data")

        assert str(exc_info.value) == "save failed"


class TestExceptionMappingContextSync:
    """Test cases for ExceptionMappingContext as a sync context manager."""

    def test_maps_exception_to_target(self) -> None:
        """Test that context manager maps source to target exception."""
        # Arrange & Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(source=_SourceError, target=_TargetError),
                ],
            ):
                raise _SourceError("original message")

        assert str(exc_info.value) == "original message"
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, _SourceError)

    def test_maps_exception_with_context_hook(self) -> None:
        """Test that context hook adds context to target exception."""
        # Arrange
        user_id_value = "123"

        def context_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"user_id": user_id_value}

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(
                        source=_SourceError,
                        target=_TargetError,
                        context_hook=context_hook,
                    ),
                ],
            ):
                raise _SourceError("not found")

        assert exc_info.value.context == {"user_id": "123"}

    def test_maps_exception_with_generic_context_hook(self) -> None:
        """Test that generic context hook adds context to all mappings."""

        # Arrange
        def generic_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"generic": "context"}

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(source=_SourceError, target=_TargetError),
                ],
                generic_context_hook=generic_hook,
            ):
                raise _SourceError("error")

        assert exc_info.value.context == {"generic": "context"}

    def test_context_hooks_are_merged(self) -> None:
        """Test that mapping-specific and generic hooks are merged."""

        # Arrange
        def specific_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"specific": "value"}

        def generic_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"generic": "value"}

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(
                        source=_SourceError,
                        target=_TargetError,
                        context_hook=specific_hook,
                    ),
                ],
                generic_context_hook=generic_hook,
            ):
                raise _SourceError("error")

        assert exc_info.value.context == {"generic": "value", "specific": "value"}

    def test_unmapped_exception_propagates(self) -> None:
        """Test that unmapped exceptions propagate unchanged."""
        # Act & Assert
        with pytest.raises(_AnotherSourceError) as exc_info:
            with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(source=_SourceError, target=_TargetError),
                ],
            ):
                raise _AnotherSourceError("different error")

        assert str(exc_info.value) == "different error"

    def test_no_exception_exits_normally(self) -> None:
        """Test that context exits normally when no exception is raised."""
        # Arrange
        result = None

        # Act
        with ExceptionMappingContext(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        ):
            result = "success"

        # Assert
        assert result == "success"

    def test_multiple_mappings(self) -> None:
        """Test that multiple mappings work correctly."""
        # Act & Assert - first mapping
        with pytest.raises(_TargetError):
            with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(source=_SourceError, target=_TargetError),
                    ExceptionMapping(source=_AnotherSourceError, target=_AnotherTargetError),
                ],
            ):
                raise _SourceError("source error")

        # Act & Assert - second mapping
        with pytest.raises(_AnotherTargetError):
            with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(source=_SourceError, target=_TargetError),
                    ExceptionMapping(source=_AnotherSourceError, target=_AnotherTargetError),
                ],
            ):
                raise _AnotherSourceError("another error")

    def test_maps_child_exception(self) -> None:
        """Test that child exceptions are mapped via parent mapping."""
        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(source=_SourceError, target=_TargetError),
                ],
            ):
                raise _ChildSourceError("child error")

        assert isinstance(exc_info.value.__cause__, _ChildSourceError)


class TestExceptionMappingContextAsync:
    """Test cases for ExceptionMappingContext as an async context manager."""

    @pytest.mark.asyncio
    async def test_maps_exception_to_target(self) -> None:
        """Test that async context manager maps source to target exception."""
        # Arrange & Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            async with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(source=_SourceError, target=_TargetError),
                ],
            ):
                raise _SourceError("original message")

        assert str(exc_info.value) == "original message"
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, _SourceError)

    @pytest.mark.asyncio
    async def test_maps_exception_with_context_hook(self) -> None:
        """Test that context hook adds context to target exception."""
        # Arrange
        user_id_value = "456"

        def context_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"user_id": user_id_value}

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            async with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(
                        source=_SourceError,
                        target=_TargetError,
                        context_hook=context_hook,
                    ),
                ],
            ):
                raise _SourceError("not found")

        assert exc_info.value.context == {"user_id": "456"}

    @pytest.mark.asyncio
    async def test_maps_exception_with_async_context_hook(self) -> None:
        """Test that async context hooks work with async context manager."""

        # Arrange
        async def async_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"async_hook": True}

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            async with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(
                        source=_SourceError,
                        target=_TargetError,
                        context_hook=async_hook,
                    ),
                ],
            ):
                raise _SourceError("error")

        assert exc_info.value.context == {"async_hook": True}

    @pytest.mark.asyncio
    async def test_maps_exception_with_generic_context_hook(self) -> None:
        """Test that generic context hook adds context to all mappings."""

        # Arrange
        def generic_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"generic": "async_context"}

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            async with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(source=_SourceError, target=_TargetError),
                ],
                generic_context_hook=generic_hook,
            ):
                raise _SourceError("error")

        assert exc_info.value.context == {"generic": "async_context"}

    @pytest.mark.asyncio
    async def test_context_hooks_are_merged(self) -> None:
        """Test that mapping-specific and generic hooks are merged."""

        # Arrange
        async def specific_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"specific": "async_value"}

        async def generic_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            return {"generic": "async_value"}

        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            async with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(
                        source=_SourceError,
                        target=_TargetError,
                        context_hook=specific_hook,
                    ),
                ],
                generic_context_hook=generic_hook,
            ):
                raise _SourceError("error")

        assert exc_info.value.context == {
            "generic": "async_value",
            "specific": "async_value",
        }

    @pytest.mark.asyncio
    async def test_unmapped_exception_propagates(self) -> None:
        """Test that unmapped exceptions propagate unchanged."""
        # Act & Assert
        with pytest.raises(_AnotherSourceError) as exc_info:
            async with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(source=_SourceError, target=_TargetError),
                ],
            ):
                raise _AnotherSourceError("different error")

        assert str(exc_info.value) == "different error"

    @pytest.mark.asyncio
    async def test_no_exception_exits_normally(self) -> None:
        """Test that async context exits normally when no exception is raised."""
        # Arrange
        result = None

        # Act
        async with ExceptionMappingContext(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        ):
            result = "async success"

        # Assert
        assert result == "async success"

    @pytest.mark.asyncio
    async def test_multiple_mappings(self) -> None:
        """Test that multiple mappings work correctly."""
        # Act & Assert - first mapping
        with pytest.raises(_TargetError):
            async with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(source=_SourceError, target=_TargetError),
                    ExceptionMapping(source=_AnotherSourceError, target=_AnotherTargetError),
                ],
            ):
                raise _SourceError("source error")

        # Act & Assert - second mapping
        with pytest.raises(_AnotherTargetError):
            async with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(source=_SourceError, target=_TargetError),
                    ExceptionMapping(source=_AnotherSourceError, target=_AnotherTargetError),
                ],
            ):
                raise _AnotherSourceError("another error")

    @pytest.mark.asyncio
    async def test_maps_child_exception(self) -> None:
        """Test that child exceptions are mapped via parent mapping."""
        # Act & Assert
        with pytest.raises(_TargetError) as exc_info:
            async with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(source=_SourceError, target=_TargetError),
                ],
            ):
                raise _ChildSourceError("child error")

        assert isinstance(exc_info.value.__cause__, _ChildSourceError)


class TestExceptionMappingContextEdgeCases:
    """Test edge cases for ExceptionMappingContext."""

    def test_reusable_context_manager(self) -> None:
        """Test that the same context instance can be reused."""
        # Arrange
        context = ExceptionMappingContext(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )

        # Act & Assert - first use
        with pytest.raises(_TargetError):
            with context:
                raise _SourceError("first")

        # Act & Assert - second use
        with pytest.raises(_TargetError):
            with context:
                raise _SourceError("second")

    @pytest.mark.asyncio
    async def test_reusable_async_context_manager(self) -> None:
        """Test that the same context instance can be reused in async."""
        # Arrange
        context = ExceptionMappingContext(
            mappings=[
                ExceptionMapping(source=_SourceError, target=_TargetError),
            ],
        )

        # Act & Assert - first use
        with pytest.raises(_TargetError):
            async with context:
                raise _SourceError("first")

        # Act & Assert - second use
        with pytest.raises(_TargetError):
            async with context:
                raise _SourceError("second")

    def test_empty_mappings_list(self) -> None:
        """Test context manager with empty mappings list."""
        # Act & Assert - exception should propagate unchanged
        with pytest.raises(_SourceError):
            with ExceptionMappingContext(mappings=[]):
                raise _SourceError("error")

    def test_exception_in_sync_context_hook(self) -> None:
        """Test that exceptions in sync context hooks propagate."""

        # Arrange
        def bad_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            raise RuntimeError("hook failed")

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(
                        source=_SourceError,
                        target=_TargetError,
                        context_hook=bad_hook,
                    ),
                ],
            ):
                raise _SourceError("error")

        assert str(exc_info.value) == "hook failed"

    @pytest.mark.asyncio
    async def test_exception_in_async_context_hook(self) -> None:
        """Test that exceptions in async context hooks propagate."""

        # Arrange
        async def bad_hook(
            exc: Exception,
            target: type[Exception],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> dict[str, Any]:
            raise RuntimeError("async hook failed")

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            async with ExceptionMappingContext(
                mappings=[
                    ExceptionMapping(
                        source=_SourceError,
                        target=_TargetError,
                        context_hook=bad_hook,
                    ),
                ],
            ):
                raise _SourceError("error")

        assert str(exc_info.value) == "async hook failed"
