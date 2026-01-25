# Kratos Service

The Kratos service provides identity management operations with Ory Kratos.

## When to Use

Use the Kratos service when:
- Managing user identities and profiles
- Validating user sessions from cookies
- Retrieving user information from identity IDs
- Updating user identity attributes
- Implementing user authentication flows
- Building user management APIs
- Integrating with Ory Kratos identity provider
- Validating session cookies for protected endpoints

## KratosIdentityGenericService

Generic service for identity management with type-safe identity and session objects.

### Implementation

```python
from fastapi_factory_utilities.core.services.kratos import (
    KratosIdentityGenericService,
    KratosIdentityObject,
    KratosSessionObject,
    KratosIdentityId,
)
from fastapi_factory_utilities.core.plugins.aiohttp import AioHttpClientResource

class CustomIdentityObject(KratosIdentityObject):
    # Custom identity fields
    pass

class CustomSessionObject(KratosSessionObject):
    # Custom session fields
    pass

class CustomKratosService(KratosIdentityGenericService[CustomIdentityObject, CustomSessionObject]):
    pass

# Usage
service = CustomKratosService(kratos_admin_http_resource=admin_client)
```

### Get Identity

```python
identity = await service.get_identity(
    identity_id=KratosIdentityId(uuid.UUID("...")),
)
```

### Update Identity

```python
from fastapi_factory_utilities.core.services.kratos import (
    KratosIdentityPatchObject,
    KratosIdentityPatchOpEnum,
)

patches = [
    KratosIdentityPatchObject(
        op=KratosIdentityPatchOpEnum.REPLACE,
        path="/traits/email",
        value="newemail@example.com",
    ),
]

updated_identity = await service.update_identity(
    identity_id=identity_id,
    patches=patches,
)
```

### Delete Credentials

```python
from fastapi_factory_utilities.core.services.kratos.enums import AuthenticationMethodEnum

await service.delete_identity_credentials(
    identity_id=identity_id,
    credentials_type=AuthenticationMethodEnum.PASSWORD,
    identifier="user@example.com",  # Optional
)
```

## KratosGenericWhoamiService

Service for session validation and user information retrieval.

### Implementation

```python
from fastapi_factory_utilities.core.services.kratos import (
    KratosGenericWhoamiService,
    KratosSessionObject,
)

class CustomWhoamiService(KratosGenericWhoamiService[CustomSessionObject]):
    pass

service = CustomWhoamiService(kratos_public_http_resource=public_client)
```

### Session Validation

```python
# Validate session from cookie
session = await service.whoami(cookie_value="ory_kratos_session_cookie_value")

# Access session information
user_id = session.identity.id
traits = session.identity.traits
```

### Usage in FastAPI

```python
from fastapi import Request, Depends, HTTPException
from fastapi_factory_utilities.core.services.kratos import (
    KratosGenericWhoamiService,
    KratosSessionInvalidError,
)

@router.get("/me")
async def get_current_user(
    request: Request,
    service: KratosGenericWhoamiService = Depends(get_whoami_service),
):
    cookie = request.cookies.get("ory_kratos_session")
    if not cookie:
        raise HTTPException(status_code=401, detail="No session cookie")

    try:
        session = await service.whoami(cookie)
        return {"user_id": session.identity.id}
    except KratosSessionInvalidError:
        raise HTTPException(status_code=401, detail="Invalid session")
```

## KratosIdentityObject

Base class for Kratos identity objects.

### Structure

```python
class KratosIdentityObject(BaseModel, Generic[...]):
    id: KratosIdentityId
    state: KratosIdentityStateEnum
    state_changed_at: datetime.datetime
    traits: GenericTraitsObject
    created_at: datetime.datetime
    updated_at: datetime.datetime
    schema_id: KratosSchemaId
    schema_url: str
    # ... other fields
```

## KratosSessionObject

Base class for Kratos session objects.

### Structure

```python
class KratosSessionObject(BaseModel):
    id: UUID
    active: bool
    authenticated_at: datetime.datetime
    expires_at: datetime.datetime
    identity: KratosIdentityObject
    # ... other fields
```

## Identity States

### KratosIdentityStateEnum

- `ACTIVE` - Identity is active
- `INACTIVE` - Identity is inactive

## Authentication Methods

### AuthenticationMethodEnum

- `PASSWORD` - Password authentication
- `OIDC` - OpenID Connect
- `TOTP` - Time-based one-time password
- `WEBAUTHN` - WebAuthn

## Error Handling

The service raises specific exceptions:

```python
from fastapi_factory_utilities.core.services.kratos.exceptions import (
    KratosOperationError,
    KratosIdentityNotFoundError,
    KratosSessionInvalidError,
)

try:
    identity = await service.get_identity(identity_id)
except KratosIdentityNotFoundError:
    # Identity not found
    raise HTTPException(status_code=404, detail="Identity not found")
except KratosOperationError as e:
    # Other Kratos error
    logger.error("Kratos operation failed", error=e, status_code=e.status_code)
```

## Best Practices

1. **Session Validation**: Always validate sessions before trusting user identity
2. **Error Handling**: Handle `KratosSessionInvalidError` for authentication failures
3. **Identity Updates**: Use patch operations for partial updates
4. **State Management**: Check identity state before operations
5. **Schema Validation**: Ensure identity traits match schema

## Reference

- `src/fastapi_factory_utilities/core/services/kratos/` - Kratos service implementation
- `src/fastapi_factory_utilities/core/services/kratos/services.py` - Service classes
- `src/fastapi_factory_utilities/core/services/kratos/objects.py` - Identity and session objects
- `src/fastapi_factory_utilities/core/services/kratos/enums.py` - Enums
