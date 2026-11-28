"""Http service dependency config."""

from pydantic import BaseModel, Field, HttpUrl


class HttpServiceDependencyConfig(BaseModel):
    """Http service dependency config."""

    url: HttpUrl | None = Field(default=None, description="Base Url used to build the client session")
    # Pool configuration
    limit: int = Field(default=10, description="Limit of connections")
    limit_per_host: int = Field(default=10, description="Limit of connections per host")
    # DNS cache configuration
    use_dns_cache: bool = Field(default=True, description="Use DNS cache")
    ttl_dns_cache: int = Field(default=300, description="TTL DNS cache in seconds")
    # Connection and request timeouts
    keepalive_timeout: float = Field(
        default=15.0,
        gt=0,
        description="Seconds an idle pooled connection is kept before being closed (aiohttp default: 15).",
    )
    request_timeout: float | None = Field(
        default=None,
        gt=0,
        description=(
            "Default total timeout per request in seconds, applied to every acquired client session. "
            "None keeps aiohttp's default (300 seconds). A per-call `timeout=` still takes precedence."
        ),
    )
    verify_ssl: bool = Field(default=True, description="Verify SSL")
    # SSL configuration to verify the server certificate
    ssl_ca_path: str | None = Field(default=None, description="SSL CA path")
    # SSL configuration for the client use certificate authentication
    ssl_certfile: str | None = Field(default=None, description="SSL certificate file")
    ssl_keyfile: str | None = Field(default=None, description="SSL key file")
    ssl_keyfile_password: str | None = Field(default=None, description="SSL key file password")
    # Application Graceful shutdown configuration
    graceful_shutdown_timeout: int = Field(default=10, description="Graceful shutdown timeout in seconds")
    # Opt-in: a downed third-party API should not fail the pod by default.
    affects_readiness: bool = Field(
        default=False,
        description="If true, register a StatusService component for this HTTP dependency.",
    )
