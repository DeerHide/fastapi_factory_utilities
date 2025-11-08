"""Provides a service to interact with the Hydra service."""

import json
from base64 import b64encode
from http import HTTPStatus
from typing import Annotated, Any, Generic, TypeVar, get_args

import aiohttp
from fastapi import Depends
from pydantic import ValidationError

from fastapi_factory_utilities.core.app import (
    DependencyConfig,
    HttpServiceDependencyConfig,
    depends_dependency_config,
)

from .exceptions import HydraOperationError
from .objects import HydraTokenIntrospectObject

HydraIntrospectObjectGeneric = TypeVar("HydraIntrospectObjectGeneric", bound=HydraTokenIntrospectObject)


class HydraIntrospectGenericService(Generic[HydraIntrospectObjectGeneric]):
    """Service to interact with the Hydra introspect service with a generic introspect object."""

    INTROSPECT_ENDPOINT: str = "/admin/oauth2/introspect"

    def __init__(self, hydra_admin_http_config: HttpServiceDependencyConfig) -> None:
        """Instanciate the Hydra introspect service.

        Args:
            hydra_admin_http_config (HttpServiceDependencyConfig): The Hydra admin HTTP configuration.
        """
        self._hydra_admin_http_config: HttpServiceDependencyConfig = hydra_admin_http_config
        # Retrieve the concrete introspect object class
        generic_args: tuple[Any, ...] = get_args(self.__orig_bases__[0])  # type: ignore
        self._concreate_introspect_object_class: type[HydraIntrospectObjectGeneric] = generic_args[0]

    async def introspect(self, token: str) -> HydraIntrospectObjectGeneric:
        """Introspects a token using the Hydra introspect service.

        Args:
            token (str): The token to introspect.
        """
        async with aiohttp.ClientSession(
            base_url=str(self._hydra_admin_http_config.url),
        ) as session:
            async with session.post(
                url=self.INTROSPECT_ENDPOINT,
                data={"token": token},
            ) as response:
                try:
                    response.raise_for_status()
                    instrospect: HydraIntrospectObjectGeneric = self._concreate_introspect_object_class.model_validate(
                        await response.json()
                    )
                except aiohttp.ClientResponseError as error:
                    raise HydraOperationError("Failed to introspect the token", status_code=error.status) from error
                except json.JSONDecodeError as error:
                    raise HydraOperationError("Failed to decode the introspect response") from error
                except ValidationError as error:
                    raise HydraOperationError("Failed to validate the introspect response") from error

                return instrospect


class HydraIntrospectService(HydraIntrospectGenericService[HydraTokenIntrospectObject]):
    """Service to interact with the Hydra introspect service with the default HydraTokenIntrospectObject."""


class HydraOAuth2ClientCredentialsService:
    """Service to interact with the Hydra service."""

    INTROSPECT_ENDPOINT: str = "/admin/oauth2/introspect"
    CLIENT_CREDENTIALS_ENDPOINT: str = "/oauth2/token"

    def __init__(
        self,
        hydra_public_http_config: HttpServiceDependencyConfig,
    ) -> None:
        """Instanciate the Hydra service.

        Args:
            hydra_admin_http_config (HttpServiceDependencyConfig): The Hydra admin HTTP configuration.
            hydra_public_http_config (HttpServiceDependencyConfig): The Hydra public HTTP configuration.
        """
        self._hydra_public_http_config: HttpServiceDependencyConfig = hydra_public_http_config

    async def oauth2_client_credentials(self, client_id: str, client_secret: str, scope: str) -> str:
        """Get the OAuth2 client credentials.

        Args:
            client_id (str): The client ID.
            client_secret (str): The client secret.
            scope (str): The scope.

        Returns:
            str: The access token.

        Raises:
            HydraOperationError: If the client credentials request fails.
        """
        # Create base64 encoded Basic Auth header
        auth_string = f"{client_id}:{client_secret}"
        auth_bytes = auth_string.encode("utf-8")
        auth_b64 = b64encode(auth_bytes).decode("utf-8")

        async with aiohttp.ClientSession(
            base_url=str(self._hydra_public_http_config.url),
        ) as session:
            async with session.post(
                url=self.CLIENT_CREDENTIALS_ENDPOINT,
                headers={"Authorization": f"Basic {auth_b64}"},
                data={"grant_type": "client_credentials", "scope": scope},
            ) as response:
                response_data = await response.json()
                if response.status != HTTPStatus.OK:
                    raise HydraOperationError(f"Failed to get client credentials: {response_data}")

                return response_data["access_token"]


def depends_hydra_oauth2_client_credentials_service(
    dependency_config: Annotated[DependencyConfig, Depends(depends_dependency_config)],
) -> HydraOAuth2ClientCredentialsService:
    """Dependency injection for the Hydra OAuth2 client credentials service.

    Args:
        dependency_config (DependencyConfig): The dependency configuration.

    Returns:
        HydraOAuth2ClientCredentialsService: The Hydra OAuth2 client credentials service instance.

    Raises:
        HydraOperationError: If the Hydra public dependency is not configured.
    """
    if dependency_config.hydra_public is None:
        raise HydraOperationError(message="Hydra public dependency not configured")

    return HydraOAuth2ClientCredentialsService(
        hydra_public_http_config=dependency_config.hydra_public,
    )


def depends_hydra_introspect_service(
    dependency_config: Annotated[DependencyConfig, Depends(depends_dependency_config)],
) -> HydraIntrospectService:
    """Dependency injection for the Hydra introspect service.

    Args:
        dependency_config (DependencyConfig): The dependency configuration.

    Returns:
        HydraIntrospectService: The Hydra introspect service instance.

    Raises:
        HydraOperationError: If the Hydra admin dependency is not configured.
    """
    if dependency_config.hydra_admin is None:
        raise HydraOperationError(message="Hydra admin dependency not configured")

    return HydraIntrospectService(
        hydra_admin_http_config=dependency_config.hydra_admin,
    )
