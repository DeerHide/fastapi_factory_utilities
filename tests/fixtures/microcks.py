"""Configuration for Microcks tests.

This module provides a custom Microcks container wrapper for integration testing
using testcontainers. Microcks is used for API mocking based on OpenAPI specifications.
"""

import urllib.parse
from collections.abc import Generator
from pathlib import Path
from typing import Any, ClassVar

import pytest
import requests
from pydantic import BaseModel, ConfigDict
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

# pylint: disable=invalid-name
microcks_image: str = "quay.io/microcks/microcks-uber:1.10.1"
microcks_http_port: int = 8080
microcks_grpc_port: int = 9090


class MicrocksContainer(DockerContainer):
    """Microcks container for API mocking.

    This container runs Microcks in standalone mode (uber image) for mocking
    HTTP APIs based on OpenAPI specifications.

    Attributes:
        MICROCKS_IMAGE: The Docker image to use for Microcks.
        MICROCKS_HTTP_PORT: The HTTP port exposed by Microcks.
        MICROCKS_GRPC_PORT: The gRPC port exposed by Microcks.
    """

    MICROCKS_IMAGE: str = microcks_image
    MICROCKS_HTTP_PORT: int = microcks_http_port
    MICROCKS_GRPC_PORT: int = microcks_grpc_port

    def __init__(self, image: str = microcks_image) -> None:
        """Initialize the Microcks container.

        Args:
            image: The Docker image to use for Microcks.
        """
        super().__init__(image=image)
        self.with_exposed_ports(self.MICROCKS_HTTP_PORT, self.MICROCKS_GRPC_PORT)

    def start(self) -> "MicrocksContainer":
        """Start the Microcks container.

        Returns:
            MicrocksContainer: The started container instance.
        """
        super().start()
        # Wait for Microcks to be ready by checking logs
        wait_for_logs(self, "Started MicrocksApplication", timeout=120)
        return self

    def get_http_endpoint(self) -> str:
        """Get the HTTP endpoint URL for Microcks API.

        Returns:
            str: The HTTP endpoint URL.
        """
        host = self.get_container_host_ip()
        port = self.get_exposed_port(self.MICROCKS_HTTP_PORT)
        return f"http://{host}:{port}"

    def get_mock_endpoint(self, service_name: str, version: str) -> str:
        """Get the base mock endpoint URL for a service.

        Args:
            service_name: The name of the service (from OpenAPI info.title).
            version: The version of the service (from OpenAPI info.version).

        Returns:
            str: The base mock endpoint URL for the service.
        """
        encoded_name = urllib.parse.quote(service_name, safe="")
        encoded_version = urllib.parse.quote(version, safe="")
        return f"{self.get_http_endpoint()}/rest/{encoded_name}/{encoded_version}"

    def get_mock_url(self, service_name: str, version: str, path: str) -> str:
        """Get the full mock URL for a specific endpoint.

        Args:
            service_name: The name of the service (from OpenAPI info.title).
            version: The version of the service (from OpenAPI info.version).
            path: The path to the endpoint (e.g., /api/users/1).

        Returns:
            str: The full mock URL for the endpoint.
        """
        base_url = self.get_mock_endpoint(service_name, version)
        # Ensure path starts with /
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{base_url}{path}"

    def upload_artifact(self, artifact_path: Path, main_artifact: bool = True) -> str:
        """Upload an OpenAPI artifact to Microcks.

        Args:
            artifact_path: Path to the OpenAPI specification file.
            main_artifact: Whether this is the main artifact (True) or secondary (False).

        Returns:
            str: The response text from Microcks API (service name and version).

        Raises:
            requests.HTTPError: If the upload fails.
            FileNotFoundError: If the artifact file does not exist.
        """
        if not artifact_path.exists():
            raise FileNotFoundError(f"Artifact file not found: {artifact_path}")

        endpoint = f"{self.get_http_endpoint()}/api/artifact/upload"
        with open(artifact_path, "rb") as artifact_file:
            files = {"file": (artifact_path.name, artifact_file, "application/x-yaml")}
            data = {"mainArtifact": "true" if main_artifact else "false"}
            response = requests.post(endpoint, files=files, data=data, timeout=30)
            response.raise_for_status()
            return response.text

    def upload_artifact_content(self, content: str, filename: str = "artifact.yaml", main_artifact: bool = True) -> str:
        """Upload an OpenAPI artifact content directly to Microcks.

        Args:
            content: The OpenAPI specification content as a string.
            filename: The filename to use for the upload.
            main_artifact: Whether this is the main artifact (True) or secondary (False).

        Returns:
            str: The response text from Microcks API (service name and version).

        Raises:
            requests.HTTPError: If the upload fails.
        """
        endpoint = f"{self.get_http_endpoint()}/api/artifact/upload"
        files = {"file": (filename, content.encode("utf-8"), "application/x-yaml")}
        data = {"mainArtifact": "true" if main_artifact else "false"}
        response = requests.post(endpoint, files=files, data=data, timeout=30)
        response.raise_for_status()
        return response.text

    def get_services(self) -> list[dict[str, Any]]:
        """Get all services registered in Microcks.

        Returns:
            list[dict[str, Any]]: List of services.
        """
        endpoint = f"{self.get_http_endpoint()}/api/services"
        response = requests.get(endpoint, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_service_invocations_count(self, service_name: str, version: str) -> int:
        """Get the invocation count for a service.

        Args:
            service_name: The name of the service.
            version: The version of the service.

        Returns:
            int: The number of invocations.
        """
        services = self.get_services()
        for service in services:
            if service.get("name") == service_name and service.get("version") == version:
                return service.get("invocationsCount", 0)
        return 0


class MicrocksFixture(BaseModel):
    """Microcks fixture model.

    This model holds the Microcks container and provides utility methods
    for interacting with the Microcks API.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    container: MicrocksContainer

    def get_http_endpoint(self) -> str:
        """Get the HTTP endpoint URL for Microcks API.

        Returns:
            str: The HTTP endpoint URL.
        """
        return self.container.get_http_endpoint()

    def get_mock_url(self, service_name: str, version: str, path: str) -> str:
        """Get the full mock URL for a specific endpoint.

        Args:
            service_name: The name of the service.
            version: The version of the service.
            path: The path to the endpoint.

        Returns:
            str: The full mock URL.
        """
        return self.container.get_mock_url(service_name, version, path)

    def upload_artifact(self, artifact_path: Path, main_artifact: bool = True) -> str:
        """Upload an OpenAPI artifact to Microcks.

        Args:
            artifact_path: Path to the OpenAPI specification file.
            main_artifact: Whether this is the main artifact.

        Returns:
            str: The response text from Microcks API (service name and version).
        """
        return self.container.upload_artifact(artifact_path, main_artifact)

    def upload_artifact_content(self, content: str, filename: str = "artifact.yaml", main_artifact: bool = True) -> str:
        """Upload an OpenAPI artifact content directly to Microcks.

        Args:
            content: The OpenAPI specification content.
            filename: The filename to use for the upload.
            main_artifact: Whether this is the main artifact.

        Returns:
            str: The response text from Microcks API (service name and version).
        """
        return self.container.upload_artifact_content(content, filename, main_artifact)


@pytest.fixture(scope="session", name="microcks_container")
def fixture_microcks_container() -> Generator[MicrocksFixture, None, None]:
    """Create and start a Microcks container for testing.

    Yields:
        MicrocksFixture: The Microcks fixture with the running container.
    """
    container = MicrocksContainer()
    container.start()
    try:
        yield MicrocksFixture(container=container)
    finally:
        container.stop()
