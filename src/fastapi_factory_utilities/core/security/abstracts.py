"""Provides the security authentication abstract classes."""

from abc import ABC, abstractmethod

from fastapi import Request


class AuthenticationAbstract(ABC):
    """Authentication abstract class."""

    def __init__(self, raise_exception: bool = True) -> None:
        """Initialize the authentication abstract class.

        Args:
            raise_exception (bool): Whether to raise an exception or return None.
        """
        self._raise_exception: bool = raise_exception
        self._errors: list[Exception] = []

    def has_errors(self) -> bool:
        """Check if the authentication has errors.

        Returns:
            bool: True if the authentication has errors, False otherwise.
        """
        return len(self._errors) > 0

    def raise_exception(self, exception: Exception) -> None:
        """Raise the exception if the authentication has errors.

        Args:
            exception (Exception): The exception to raise.
        """
        if self._raise_exception:
            raise exception
        else:
            self._errors.append(exception)

    @abstractmethod
    async def authenticate(self, request: Request) -> None:
        """Authenticate the request."""
        raise NotImplementedError()
