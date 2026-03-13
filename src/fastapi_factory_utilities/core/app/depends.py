"""Provides the dependencies for the application."""

from typing import Generic, TypeVar, cast

from fastapi import Depends, Request
from fastapi.datastructures import State

from .config import AppCsrfConfig, BaseApplicationConfig, RootConfig

GenericRootConfig = TypeVar("GenericRootConfig", bound=RootConfig)
GenericApplicationConfig = TypeVar("GenericApplicationConfig", bound=BaseApplicationConfig)


class DependsRootConfig(Generic[GenericRootConfig]):
    """Dependency for the root config."""

    @classmethod
    def export_from_state(cls, state: State) -> GenericRootConfig:
        """Export the root config from the state."""
        return getattr(state, "config")

    @classmethod
    def import_to_state(cls, state: State, config: GenericRootConfig) -> None:
        """Import the root config to the state."""
        setattr(state, "config", config)

    def __call__(self, request: Request) -> GenericRootConfig:
        """Dependency for the root config."""
        if not hasattr(request.app.state, "config"):
            raise ValueError("Root config not found in the state.")
        return self.export_from_state(state=request.app.state)


depends_root_config = DependsRootConfig[RootConfig]()


class DependsApplicationConfig(Generic[GenericApplicationConfig]):
    """Dependency for the application config."""

    def __call__(self, root_config: RootConfig = Depends(depends_root_config)) -> GenericApplicationConfig:
        """Dependency for the application config."""
        return cast(GenericApplicationConfig, root_config.application)


depends_application_config = DependsApplicationConfig[BaseApplicationConfig]()


def depends_csrf_config(root_config: RootConfig = Depends(depends_root_config)) -> AppCsrfConfig:
    """Dependency for the CSRF config."""
    if root_config.csrf is None:
        raise ValueError("CSRF config not found in the root config.")
    return root_config.csrf
