"""Provide Kratos Session and Identity classes."""

from http import HTTPStatus

from fastapi import HTTPException, Request

from fastapi_factory_utilities.core.security.abstracts import AuthenticationAbstract
from fastapi_factory_utilities.core.services.kratos import (
    KratosOperationError,
    KratosService,
    KratosSessionInvalidError,
    KratosSessionObject,
)


class KratosSessionAuthenticationService(AuthenticationAbstract):
    """Kratos Session class."""

    DEFAULT_COOKIE_NAME: str = "ory_kratos_session"

    def __init__(
        self, kratos_service: KratosService, cookie_name: str = DEFAULT_COOKIE_NAME, raise_exception: bool = True
    ) -> None:
        """Initialize the KratosSessionAuthentication class.

        Args:
            kratos_service (KratosService): Kratos service object.
            cookie_name (str): Name of the cookie to extract the session.
            raise_exception (bool): Whether to raise an exception or return None.
        """
        self._kratos_service: KratosService = kratos_service
        self._cookie_name: str = cookie_name
        self._session: KratosSessionObject
        super().__init__(raise_exception=raise_exception)

    def _extract_cookie(self, request: Request) -> str | None:
        """Extract the cookie from the request.

        Args:
            request (Request): FastAPI request object.

        Returns:
            str | None: Cookie value or None if not found.

        Raises:
            HTTPException: If the cookie is missing.
        """
        return request.cookies.get(self._cookie_name, None)

    @property
    def session(self) -> KratosSessionObject:
        """Get the Kratos session.

        Returns:
            KratosSessionObject: Kratos session object.
        """
        return self._session

    async def authenticate(self, request: Request) -> None:
        """Extract the Kratos session from the request.

        Args:
            request (Request): FastAPI request object.
            kratos_service (KratosService): Kratos service object.

        Returns:
            None: If the authentication is successful or not raise_exception is False.

        Raises:
            HTTPException: If the session is invalid and raise_exception is True.
        """
        cookie: str | None = self._extract_cookie(request)
        if not cookie:
            return self.raise_exception(
                HTTPException(
                    status_code=HTTPStatus.UNAUTHORIZED,
                    detail="Missing Credentials",
                )
            )

        try:
            self._session = await self._kratos_service.whoami(cookie_value=cookie)
        except KratosSessionInvalidError:
            return self.raise_exception(
                HTTPException(
                    status_code=HTTPStatus.UNAUTHORIZED,
                    detail="Invalid Credentials",
                )
            )
        except KratosOperationError:
            return self.raise_exception(
                HTTPException(
                    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                    detail="Internal Server Error",
                )
            )

        return
