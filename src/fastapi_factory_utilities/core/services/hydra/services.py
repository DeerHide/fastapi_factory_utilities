"""Provides a service to interact with the Hydra service."""

import json
from base64 import b64encode
from typing import Annotated, Any, Generic, TypeVar, get_args

import aiohttp
import jwt
from fastapi import Depends
from pydantic import ValidationError

from fastapi_factory_utilities.core.plugins.aiohttp import (
    AioHttpClientResource,
    AioHttpResourceDepends,
)

from .exceptions import HydraOperationError
from .objects import HydraTokenIntrospectObject
from .types import HydraAccessToken, HydraClientId, HydraClientSecret

HydraIntrospectObjectGeneric = TypeVar("HydraIntrospectObjectGeneric", bound=HydraTokenIntrospectObject)


class HydraIntrospectGenericService(Generic[HydraIntrospectObjectGeneric]):
    """Service to interact with the Hydra introspect service with a generic introspect object."""

    INTROSPECT_ENDPOINT: str = "/admin/oauth2/introspect"
    WELLKNOWN_JWKS_ENDPOINT: str = "/.well-known/jwks.json"

    def __init__(
        self,
        hydra_admin_http_resource: AioHttpClientResource,
        hydra_public_http_resource: AioHttpClientResource,
    ) -> None:
        """Instanciate the Hydra introspect service.

        Args:
            hydra_admin_http_resource (AioHttpClientResource): The Hydra admin HTTP resource.
            hydra_public_http_resource (AioHttpClientResource): The Hydra public HTTP resource.
        """
        self._hydra_admin_http_resource: AioHttpClientResource = hydra_admin_http_resource
        self._hydra_public_http_resource: AioHttpClientResource = hydra_public_http_resource
        # Retrieve the concrete introspect object class
        generic_args: tuple[Any, ...] = get_args(self.__orig_bases__[0])  # type: ignore
        self._concreate_introspect_object_class: type[HydraIntrospectObjectGeneric] = generic_args[0]

    async def introspect(self, token: HydraAccessToken) -> HydraIntrospectObjectGeneric:
        """Introspects a token using the Hydra introspect service.

        Args:
            token (str): The token to introspect.
        """
        try:
            async with self._hydra_admin_http_resource.acquire_client_session() as session:
                async with session.post(
                    url=self.INTROSPECT_ENDPOINT,
                    data={"token": token},
                ) as response:
                    response.raise_for_status()
                    instrospect: HydraIntrospectObjectGeneric = self._concreate_introspect_object_class.model_validate(
                        await response.json()
                    )
        except aiohttp.ClientResponseError as error:
            raise HydraOperationError(
                "An error occurred while introspecting the token", status_code=error.status
            ) from error
        except json.JSONDecodeError as error:
            raise HydraOperationError("An error occurred while decoding the introspect response") from error
        except ValidationError as error:
            raise HydraOperationError("An error occurred while validating the introspect response") from error
        except Exception as error:
            raise HydraOperationError("An error occurred while introspecting the token") from error

        return instrospect

    async def get_wellknown_jwks(self) -> jwt.PyJWKSet:
        """Get the JWKS from the Hydra service."""
        try:
            async with self._hydra_public_http_resource.acquire_client_session() as session:
                async with session.get(
                    url=self.WELLKNOWN_JWKS_ENDPOINT,
                ) as response:
                    response.raise_for_status()
                    jwks_data: dict[str, Any] = await response.json()
                    jwks: jwt.PyJWKSet = jwt.PyJWKSet.from_dict(jwks_data)
                    return jwks
        except aiohttp.ClientResponseError as error:
            raise HydraOperationError(
                "Failed to get the JWKS from the Hydra service", status_code=error.status
            ) from error
        except json.JSONDecodeError as error:
            raise HydraOperationError("Failed to decode the JWKS from the Hydra service") from error
        except ValidationError as error:
            raise HydraOperationError("Failed to validate the JWKS from the Hydra service") from error
        except Exception as error:
            raise HydraOperationError("Failed to get the JWKS from the Hydra service") from error


class HydraIntrospectService(HydraIntrospectGenericService[HydraTokenIntrospectObject]):
    """Service to interact with the Hydra introspect service with the default HydraTokenIntrospectObject."""


class HydraOAuth2ClientCredentialsService:
    """Service to interact with the Hydra service."""

    INTROSPECT_ENDPOINT: str = "/admin/oauth2/introspect"
    CLIENT_CREDENTIALS_ENDPOINT: str = "/oauth2/token"

    def __init__(
        self,
        hydra_public_http_resource: AioHttpClientResource,
    ) -> None:
        """Instanciate the Hydra service.

        Args:
            hydra_public_http_resource (AioHttpClientResource): The Hydra public HTTP resource.
        """
        self._hydra_public_http_resource: AioHttpClientResource = hydra_public_http_resource

    @classmethod
    def build_bearer_header(cls, client_id: HydraClientId, client_secret: HydraClientSecret) -> str:
        """Build the bearer header.

        Args:
            client_id (str): The client ID.
            client_secret (str): The client secret.

        Returns:
            str: The bearer header.
        """
        auth_string: str = f"{client_id}:{client_secret}"
        auth_bytes: bytes = auth_string.encode("utf-8")
        auth_b64: str = b64encode(auth_bytes).decode("utf-8")
        return f"Basic {auth_b64}"

    async def oauth2_client_credentials(
        self, client_id: HydraClientId, client_secret: HydraClientSecret, scopes: list[str]
    ) -> HydraAccessToken:
        """Get the OAuth2 client credentials.

        Args:
            client_id (str): The client ID.
            client_secret (str): The client secret.
            scopes (list[str]): The scopes

        Returns:
            str: The access token.

        Raises:
            HydraOperationError: If the client credentials request fails.
        """
        try:
            async with self._hydra_public_http_resource.acquire_client_session() as session:
                async with session.post(
                    url=self.CLIENT_CREDENTIALS_ENDPOINT,
                    headers={"Authorization": self.build_bearer_header(client_id, client_secret)},
                    data={"grant_type": "client_credentials", "scope": " ".join(scopes)},
                ) as response:
                    response.raise_for_status()
                    response_data = await response.json()
                    return response_data["access_token"]
        except aiohttp.ClientResponseError as error:
            raise HydraOperationError(
                "An error occurred while getting the client credentials", status_code=error.status
            ) from error
        except json.JSONDecodeError as error:
            raise HydraOperationError(
                "An error occurred while getting the client credentials, invalid JSON response"
            ) from error
        except ValidationError as error:
            raise HydraOperationError(
                "An error occurred while getting the client credentials, invalid response"
            ) from error
        except Exception as error:
            raise HydraOperationError(
                "An error occurred while getting the client credentials, unknown error"
            ) from error


def depends_hydra_oauth2_client_credentials_service(
    hydra_public_http_resource: Annotated[AioHttpClientResource, Depends(AioHttpResourceDepends("hydra_public"))],
) -> HydraOAuth2ClientCredentialsService:
    """Dependency injection for the Hydra OAuth2 client credentials service.

    Args:
        hydra_public_http_resource (AioHttpClientResource): The Hydra public HTTP resource.

    Returns:
        HydraOAuth2ClientCredentialsService: The Hydra OAuth2 client credentials service instance.

    Raises:
        HydraOperationError: If the Hydra public dependency is not configured.
    """
    return HydraOAuth2ClientCredentialsService(
        hydra_public_http_resource=hydra_public_http_resource,
    )


def depends_hydra_introspect_service(
    hydra_admin_http_resource: Annotated[AioHttpClientResource, Depends(AioHttpResourceDepends("hydra_admin"))],
    hydra_public_http_resource: Annotated[AioHttpClientResource, Depends(AioHttpResourceDepends("hydra_public"))],
) -> HydraIntrospectService:
    """Dependency injection for the Hydra introspect service.

    Args:
        hydra_admin_http_resource (AioHttpClientResource): The Hydra admin HTTP resource.
        hydra_public_http_resource (AioHttpClientResource): The Hydra public HTTP resource.

    Returns:
        HydraIntrospectService: The Hydra introspect service instance.

    Raises:
        HydraOperationError: If the Hydra admin dependency is not configured.
    """
    return HydraIntrospectService(
        hydra_admin_http_resource=hydra_admin_http_resource,
        hydra_public_http_resource=hydra_public_http_resource,
    )
