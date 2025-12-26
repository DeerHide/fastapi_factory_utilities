"""Provides the KratosService class for handling Kratos operations."""

import datetime
import json
from http import HTTPStatus
from typing import Any, ClassVar, Generic, TypeVar, get_args

import aiohttp
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from structlog.stdlib import BoundLogger, get_logger

from fastapi_factory_utilities.core.plugins.aiohttp import AioHttpClientResource
from fastapi_factory_utilities.core.utils.ory import get_next_page_token_from_link_header

from .enums import AuthenticationMethodEnum, KratosFlowTypeEnum, KratosIdentityPatchOpEnum
from .exceptions import KratosOperationError, KratosSessionInvalidError
from .types import KratosIdentityId, KratosRecoveryCode, KratosRecoveryLink

_logger: BoundLogger = get_logger(__package__)

GenericKratosSessionObject = TypeVar("GenericKratosSessionObject", bound=BaseModel)


class KratosGenericWhoamiService(Generic[GenericKratosSessionObject]):
    """Service class for handling Kratos operations."""

    COOKIE_NAME: str = "ory_kratos_session"

    def __init__(self, kratos_public_http_resource: AioHttpClientResource) -> None:
        """Initialize the KratosService class.

        Args:
            kratos_public_http_resource (AioHttpClientResource): Kratos public HTTP resource.
        """
        self._kratos_public_http_resource: AioHttpClientResource = kratos_public_http_resource
        # Retrieve the concrete introspect object class
        generic_args: tuple[Any, ...] = get_args(self.__orig_bases__[0])  # type: ignore
        self._concreate_session_object_class: type[GenericKratosSessionObject] = generic_args[0]

    async def whoami(self, cookie_value: str) -> GenericKratosSessionObject:
        """Get the current user session.

        Args:
            cookie_value (str): Cookie value.

        Returns:
            GenericKratosSessionObject: Kratos session object.

        Raises:
            KratosOperationError: If the Kratos service returns an error.
            KratosSessionInvalidError: If the Kratos session is invalid.
        """
        cookies: dict[str, str] = {self.COOKIE_NAME: cookie_value}
        async with self._kratos_public_http_resource.acquire_client_session(cookies=cookies) as session:
            async with session.get(
                url="/sessions/whoami",
            ) as response:
                if response.status >= HTTPStatus.INTERNAL_SERVER_ERROR.value:
                    raise KratosOperationError(message=f"Kratos service error: {response.status} - {response.reason}")
                if response.status == HTTPStatus.UNAUTHORIZED:
                    raise KratosSessionInvalidError(
                        message=f"Kratos session invalid: {response.status} - {response.reason}"
                    )
                if response.status != HTTPStatus.OK:
                    raise KratosOperationError(message=f"Kratos service error: {response.status} - {response.reason}")

                try:
                    kratos_session: GenericKratosSessionObject = self._concreate_session_object_class.model_validate(
                        await response.json()
                    )
                except ValidationError as e:
                    raise KratosOperationError(message=f"Kratos service error: {e}") from e

                return kratos_session


GenericKratosIdentityObject = TypeVar("GenericKratosIdentityObject", bound=BaseModel)


class KratosIdentityPatchObject(BaseModel):
    """Patch object for Kratos identity."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    from_: str = Field(alias="from")
    op: KratosIdentityPatchOpEnum
    path: str
    value: Any


class KratosIdentityGenericService(Generic[GenericKratosIdentityObject, GenericKratosSessionObject]):
    """Service class for handling Kratos identity operations."""

    IDENTITY_ENDPOINT: str = "/admin/identities"
    ADMIN_ENDPOINT: str = "/admin"

    def __init__(self, kratos_admin_http_resource: AioHttpClientResource) -> None:
        """Initialize the KratosIdentityGenericService class.

        Args:
            kratos_admin_http_resource (AioHttpClientResource): Kratos admin HTTP resource.
        """
        self._kratos_admin_http_resource: AioHttpClientResource = kratos_admin_http_resource
        # Retrieve the concrete introspect object class
        generic_args: tuple[Any, ...] = get_args(self.__orig_bases__[0])  # type: ignore
        self._concreate_identity_object_class: type[GenericKratosIdentityObject] = generic_args[0]
        self._concreate_session_object_class: type[GenericKratosSessionObject] = generic_args[1]

    async def get_identity(self, identity_id: KratosIdentityId) -> GenericKratosIdentityObject:
        """Get a Kratos identity by ID.

        Args:
            identity_id (KratosIdentityId): The ID of the identity to get.

        Returns:
            GenericKratosIdentityObject: Kratos identity object.
        """
        try:
            async with self._kratos_admin_http_resource.acquire_client_session() as session:
                async with session.get(url=f"{self.IDENTITY_ENDPOINT}/{identity_id}") as response:
                    response.raise_for_status()
                    return self._concreate_identity_object_class.model_validate(await response.json())
        except (aiohttp.ClientResponseError, json.JSONDecodeError, ValidationError) as e:
            status_code: str | None = getattr(e, "status", None)
            raise KratosOperationError(
                message="Failed to get the Kratos identity",
                identity_id=identity_id,
                status_code=status_code,
            ) from e

    async def create_identity(self, identity: GenericKratosIdentityObject) -> GenericKratosIdentityObject:
        """Create a Kratos identity."""
        raise NotImplementedError("Not implemented")

    async def update_identity(
        self, identity_id: KratosIdentityId, patches: list[KratosIdentityPatchObject]
    ) -> GenericKratosIdentityObject:
        """Update a Kratos identity.

        Raises:
            KratosOperationError: If the Kratos service returns an error.

        Args:
            identity_id (KratosIdentityId): The ID of the identity to update.
            patches (list[KratosIdentityPatchObject]): The patches to apply to the identity.

        Returns:
            GenericKratosIdentityObject: The updated identity.
        """
        try:
            async with self._kratos_admin_http_resource.acquire_client_session() as session:
                async with session.patch(url=f"{self.IDENTITY_ENDPOINT}/{identity_id}", json=patches) as response:
                    response.raise_for_status()
                    identity: GenericKratosIdentityObject = self._concreate_identity_object_class.model_validate(
                        await response.json()
                    )
        except (aiohttp.ClientResponseError, json.JSONDecodeError, ValidationError) as e:
            status_code: str | None = getattr(e, "status", None)
            raise KratosOperationError(
                message="Failed to update the Kratos identity",
                identity_id=identity_id,
                patches=patches,
                status_code=status_code,
            ) from e

        _logger.info(
            "Identity updated successfully",
            identity_id=identity_id,
            patches=patches,
            identity=identity,
        )

        return identity

    async def delete_identity_credentials(
        self,
        identity_id: KratosIdentityId,
        credentials_type: AuthenticationMethodEnum,
        identifier: str | None = None,
    ) -> None:
        """Delete the credentials of a Kratos identity.

        Args:
            identity_id (KratosIdentityId): The ID of the identity to delete the credentials of.
            credentials_type (AuthenticationMethodEnum): The type of credentials to delete.
            identifier (str | None): The identifier of the credentials to delete.
            (Mandatory for OIDC and SAML credentials)

        Returns:
            None: If the credentials are deleted successfully.
        """
        if credentials_type not in [AuthenticationMethodEnum.OIDC, AuthenticationMethodEnum.SAML]:
            if identifier is not None:
                raise ValueError("Identifier is only supported for OIDC and SAML credentials")
        elif identifier is None:
            raise ValueError("Identifier is mandatory for OIDC and SAML credentials")

        query_params: dict[str, str] = {}
        if identifier is not None:
            query_params["identifier"] = identifier

        try:
            async with self._kratos_admin_http_resource.acquire_client_session() as session:
                async with session.delete(
                    url=f"{self.IDENTITY_ENDPOINT}/{identity_id}/credentials", params=query_params
                ) as response:
                    response.raise_for_status()
        except (aiohttp.ClientResponseError, json.JSONDecodeError, ValidationError) as e:
            status_code: str | None = getattr(e, "status", None)
            raise KratosOperationError(
                message="Failed to delete the credentials of the Kratos identity",
                identity_id=identity_id,
                credentials_type=credentials_type,
                identifier=identifier,
                status_code=status_code,
            ) from e

        _logger.info(
            "Credentials deleted successfully",
            identity_id=identity_id,
            credentials_type=credentials_type,
            identifier=identifier,
        )

    async def delete_identity_sessions(self, identity_id: KratosIdentityId) -> None:
        """Delete the sessions of a Kratos identity.

        Args:
            identity_id (KratosIdentityId): The ID of the identity to delete the sessions of.

        Returns:
            None: If the sessions are deleted successfully.
        """
        try:
            async with self._kratos_admin_http_resource.acquire_client_session() as session:
                async with session.delete(url=f"{self.IDENTITY_ENDPOINT}/{identity_id}/sessions") as response:
                    response.raise_for_status()
        except (aiohttp.ClientResponseError, json.JSONDecodeError, ValidationError) as e:
            status_code: str | None = getattr(e, "status", None)
            raise KratosOperationError(
                message="Failed to delete the sessions of the Kratos identity",
                identity_id=identity_id,
                status_code=status_code,
            ) from e

        _logger.info(
            "Sessions deleted successfully",
            identity_id=identity_id,
        )

    async def delete_identity(self, identity_id: KratosIdentityId) -> None:
        """Delete a Kratos identity.

        Args:
            identity_id (KratosIdentityId): The ID of the identity to delete.

        Returns:
            None: If the identity is deleted successfully.
        """
        try:
            async with self._kratos_admin_http_resource.acquire_client_session() as session:
                async with session.delete(url=f"{self.IDENTITY_ENDPOINT}/{identity_id}") as response:
                    response.raise_for_status()
        except (aiohttp.ClientResponseError, json.JSONDecodeError, ValidationError) as e:
            status_code: str | None = getattr(e, "status", None)
            raise KratosOperationError(
                message="Failed to delete the Kratos identity",
                identity_id=identity_id,
                status_code=status_code,
            ) from e

        _logger.info("Identity deleted successfully", identity_id=identity_id)

    async def list_sessions(
        self,
        identity_id: KratosIdentityId,
        active: bool = True,
        page_size: int = 250,
        page_token: str | None = None,
    ) -> tuple[list[GenericKratosSessionObject], str | None]:
        """List the sessions of a Kratos identity.

        Args:
            identity_id (KratosIdentityId): The ID of the identity to list the sessions of.
            active (bool): Whether to filter for active sessions only. Defaults to True.
            page_size (int): The number of sessions to return per page. Defaults to 250.
            page_token (str | None): The page token to use for pagination.

        Returns:
            Tuple[list[GenericKratosSessionObject], str | None]: A tuple containing the list of
                sessions and the next page token.
        """
        query_params: dict[str, str] = {
            "page_size": str(page_size),
            "active": str(active),
        }
        if page_token is not None:
            query_params["page_token"] = page_token

        try:
            async with self._kratos_admin_http_resource.acquire_client_session() as session:
                async with session.get(
                    url=f"{self.IDENTITY_ENDPOINT}/{identity_id}/sessions", params=query_params
                ) as response:
                    response.raise_for_status()
                    sessions: list[GenericKratosSessionObject] = [
                        self._concreate_session_object_class.model_validate(session)
                        for session in await response.json()
                    ]
                    link_header: str | None = response.headers.get("Link", None)
                    next_page_token: str | None = get_next_page_token_from_link_header(link_header=link_header)

                    return sessions, next_page_token
        except (aiohttp.ClientResponseError, json.JSONDecodeError, ValidationError) as e:
            status_code: str | None = getattr(e, "status", None)
            raise KratosOperationError(
                message="Failed to list the sessions of the Kratos identity",
                identity_id=identity_id,
                status_code=status_code,
            ) from e

    async def create_recovery_code(
        self,
        identity_id: KratosIdentityId,
        flow_type: KratosFlowTypeEnum,
        expires_in: datetime.timedelta,
    ) -> KratosRecoveryCode:
        """Create a recovery code for a Kratos identity.

        Args:
            identity_id (KratosIdentityId): The ID of the identity to create the recovery code for.
            flow_type (KratosFlowTypeEnum): The type of flow to create the recovery code for.
            expires_in (datetime.timedelta): The expiration time for the recovery code.

        Raises:
            KratosOperationError: If the Kratos service returns an error.

        Returns:
            KratosRecoveryCode: The recovery code.
        """
        try:
            async with self._kratos_admin_http_resource.acquire_client_session() as session:
                async with session.post(
                    url=f"{self.ADMIN_ENDPOINT}/recovery/code",
                    json={
                        "flow_type": flow_type.value,
                        "expires_in": f"{int(expires_in.total_seconds())}s",
                        "identity_id": str(identity_id),
                    },
                ) as response:
                    response.raise_for_status()
                    code: KratosRecoveryCode = KratosRecoveryCode(await response.json())
        except (aiohttp.ClientResponseError, json.JSONDecodeError, ValidationError) as e:
            status_code: str | None = getattr(e, "status", None)
            raise KratosOperationError(
                message="Failed to create the recovery code for the Kratos identity",
                identity_id=identity_id,
                flow_type=flow_type,
                expires_in=expires_in,
                status_code=status_code,
            ) from e

        _logger.info(
            "Recovery code created successfully",
            identity_id=identity_id,
            flow_type=flow_type,
            expires_in=expires_in,
        )

        return code

    async def create_recovery_link(
        self,
        identity_id: KratosIdentityId,
        expires_in: datetime.timedelta,
    ) -> KratosRecoveryLink:
        """Create a recovery link for a Kratos identity.

        Args:
            identity_id (KratosIdentityId): The ID of the identity to create the recovery link for.
            expires_in (datetime.timedelta): The expiration time for the recovery link.

        Returns:
            KratosRecoveryLink: The recovery link.

        Raises:
            KratosOperationError: If the Kratos service returns an error.
        """
        try:
            async with self._kratos_admin_http_resource.acquire_client_session() as session:
                async with session.post(
                    url=f"{self.ADMIN_ENDPOINT}/recovery/link",
                    json={
                        "expires_in": f"{int(expires_in.total_seconds())}s",
                        "identity_id": str(identity_id),
                    },
                ) as response:
                    response.raise_for_status()
                    link: KratosRecoveryLink = KratosRecoveryLink(await response.json())
        except (aiohttp.ClientResponseError, json.JSONDecodeError, ValidationError) as e:
            status_code: str | None = getattr(e, "status", None)
            raise KratosOperationError(
                message="Failed to create the recovery link for the Kratos identity",
                identity_id=identity_id,
                expires_in=expires_in,
                status_code=status_code,
            ) from e

        _logger.info(
            "Recovery link created successfully",
            identity_id=identity_id,
            expires_in=expires_in,
        )

        return link
