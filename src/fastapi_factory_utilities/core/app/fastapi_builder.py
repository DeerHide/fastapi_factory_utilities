"""Provides the FastAPIBuilder class."""

from typing import Any, NamedTuple, Self

from fastapi import APIRouter, FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware

from fastapi_factory_utilities.core.app.config import RootConfig


class MiddlewareArgs(NamedTuple):
    """Middleware arguments."""

    middleware_class: type[Middleware]
    kwargs: dict[str, Any]


class FastAPIBuilder:
    """FastAPI builder."""

    def __init__(self, root_config: RootConfig) -> None:
        """Instantiate the FastAPIBuilder."""
        self._root_config: RootConfig = root_config
        self._base_router: APIRouter = APIRouter()
        self._middleware_list: list[MiddlewareArgs] = []

    def add_api_router(self, router: APIRouter, without_resource_path: bool = False) -> Self:
        """Add the API router to the FastAPI application.

        Args:
            router: The API router.
            without_resource_path: If True, the resource path will not be added to the router.

        Returns:
            Self: The FastAPI builder.
        """
        self._base_router.include_router(
            router=router, prefix=self._root_config.application.root_path if not without_resource_path else ""
        )
        return self

    def add_middleware(self, middleware_class: type[Middleware], **kwargs: Any) -> Self:
        """Add a middleware to the FastAPI application.

        Args:
            middleware_class: The middleware class.
            *args: The middleware arguments.
            **kwargs: The middleware keyword arguments.

        Returns:
            Self: The FastAPI builder.
        """
        self._middleware_list.append(MiddlewareArgs(middleware_class=middleware_class, kwargs=kwargs))
        return self

    def build(self, lifespan: Any) -> FastAPI:
        """Build the FastAPI application.

        Returns:
            FastAPI: The FastAPI application.
        """
        fastapi = FastAPI(
            title=self._root_config.application.service_name,
            description="",
            version=self._root_config.application.version,
            lifespan=lifespan,
        )

        # Opt-in CORS: empty allow_origins (the default) skips middleware entirely.
        if self._root_config.cors.allow_origins:
            fastapi.add_middleware(
                middleware_class=CORSMiddleware,
                allow_origins=self._root_config.cors.allow_origins,
                allow_credentials=self._root_config.cors.allow_credentials,
                allow_methods=self._root_config.cors.allow_methods,
                allow_headers=self._root_config.cors.allow_headers,
            )

        for middleware_args in self._middleware_list:
            fastapi.add_middleware(
                middleware_class=middleware_args.middleware_class,  # type: ignore
                **middleware_args.kwargs,  # pyright: ignore
            )

        fastapi.include_router(router=self._base_router)

        return fastapi
