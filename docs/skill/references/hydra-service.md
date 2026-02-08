# Hydra Service

The Hydra service provides OAuth2 and OpenID Connect operations with Ory Hydra.

## When to Use

Use the Hydra service when:
- Validating OAuth2 access tokens
- Implementing token introspection for API authentication
- Obtaining JWKS for JWT verification
- Implementing OAuth2 client credentials flow
- Building service-to-service authentication
- Integrating OAuth2/OIDC providers with Ory Hydra
- Verifying token scopes and audiences

## HydraIntrospectGenericService

Generic service for token introspection with type-safe introspect objects.

### Implementation

```python
from fastapi_factory_utilities.core.services.hydra import (
    HydraIntrospectGenericService,
    HydraTokenIntrospectObject,
    HydraAccessToken,
)
from fastapi_factory_utilities.core.plugins.aiohttp import AioHttpClientResource

class CustomIntrospectObject(HydraTokenIntrospectObject):
    # Add custom fields
    custom_field: str

class CustomHydraService(HydraIntrospectGenericService[CustomIntrospectObject]):
    pass

# Usage
service = CustomHydraService(
    hydra_admin_http_resource=admin_client,
    hydra_public_http_resource=public_client,
)

# Introspect token
introspect = await service.introspect(token="access_token_here")
```

### Token Introspection

```python
async def validate_token(token: str, service: HydraIntrospectGenericService):
    try:
        introspect = await service.introspect(token=HydraAccessToken(token))

        if not introspect.active:
            raise ValueError("Token is not active")

        return introspect
    except HydraOperationError as e:
        # Handle introspection error
        raise
```

### JWKS Access

```python
# Get JWKS for JWT verification
jwks = await service.get_wellknown_jwks()

# Use with PyJWT
import jwt
decoded = jwt.decode(
    token,
    jwks,
    algorithms=["RS256"],
    audience="your-audience",
)
```

## HydraOAuth2ClientCredentialsService

Service for OAuth2 client credentials grant flow.

### Usage

```python
from fastapi_factory_utilities.core.services.hydra import (
    HydraOAuth2ClientCredentialsService,
    HydraClientId,
    HydraClientSecret,
    HydraAccessToken,
)

service = HydraOAuth2ClientCredentialsService(
    hydra_public_http_resource=public_client,
    application_config=app_config,
)

# Get access token
token = await service.oauth2_client_credentials(
    client_id=HydraClientId("client-id"),
    client_secret=HydraClientSecret("client-secret"),
    scopes=["read", "write"],
    audience="your-audience",  # Optional, uses config default if not provided
)
```

### Client Credentials Flow

```python
async def get_service_token(service: HydraOAuth2ClientCredentialsService):
    token = await service.oauth2_client_credentials(
        client_id=HydraClientId("my-service"),
        client_secret=HydraClientSecret("secret"),
        scopes=["api:read", "api:write"],
    )
    return token
```

## HydraTokenIntrospectObject

Base class for token introspection responses.

### Default Implementation

```python
from fastapi_factory_utilities.core.services.hydra import (
    HydraIntrospectService,  # Uses default HydraTokenIntrospectObject
)

service = HydraIntrospectService(
    hydra_admin_http_resource=admin_client,
    hydra_public_http_resource=public_client,
)

introspect = await service.introspect(token)
# introspect.active - bool
# introspect.scope - str
# introspect.client_id - str
# etc.
```

## Error Handling

The service raises `HydraOperationError` on failures:

```python
from fastapi_factory_utilities.core.services.hydra.exceptions import (
    HydraOperationError,
    HydraTokenInvalidError,
)

try:
    introspect = await service.introspect(token)
except HydraTokenInvalidError:
    # Token is invalid
    pass
except HydraOperationError as e:
    # Other Hydra operation error
    logger.error("Hydra operation failed", error=e, status_code=e.status_code)
```

## Integration with AioHttp

The service uses AioHttp client resources:

```python
from fastapi_factory_utilities.core.plugins.aiohttp import (
    AioHttpClientPlugin,
    AioHttpResourceDepends,
)

# Configure plugin
plugin = AioHttpClientPlugin(keys=["hydra_admin", "hydra_public"])

# Use in dependencies
@router.post("/introspect")
async def introspect_token(
    token: str,
    admin_client = Depends(AioHttpResourceDepends("hydra_admin")),
    public_client = Depends(AioHttpResourceDepends("hydra_public")),
):
    service = HydraIntrospectService(
        hydra_admin_http_resource=admin_client,
        hydra_public_http_resource=public_client,
    )
    return await service.introspect(token)
```

## Best Practices

1. **Token Validation**: Always check `active` status after introspection
2. **Error Handling**: Handle `HydraTokenInvalidError` separately
3. **JWKS Caching**: Cache JWKS for JWT verification
4. **Scope Validation**: Validate scopes after introspection
5. **Audience Validation**: Always validate audience matches expected value

## See Also

- [JWT Authentication](jwt-authentication.md) - Local JWT verification with JWKS (e.g., using Hydra's JWKS endpoint as key source)
- [AioHttp HTTP Client](aiohttp.md) - HTTP client used by Hydra services and integration patterns

## Reference

- `src/fastapi_factory_utilities/core/services/hydra/` - Hydra service implementation
- `src/fastapi_factory_utilities/core/services/hydra/services.py` - Service classes
- `src/fastapi_factory_utilities/core/services/hydra/objects.py` - Introspect objects
