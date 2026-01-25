# Ory Utilities

Helper utilities for working with Ory Kratos and Hydra services.

## When to Use

Use Ory utilities when:
- Paginating through Ory Kratos identity lists
- Paginating through Ory Hydra OAuth2 client lists
- Parsing Link headers from Ory API responses
- Implementing cursor-based pagination with Ory services
- Building pagination loops for Ory API endpoints
- Extracting page tokens from RFC 5988 Link headers

## get_next_page_token_from_link_header

Parses Link headers from Ory API responses to extract pagination tokens.

### Usage

```python
from fastapi_factory_utilities.core.utils.ory import (
    get_next_page_token_from_link_header,
)

# Parse Link header from HTTP response
link_header = (
    '</admin/clients?page_size=5&page_token=euKoY1BqY3J8GVax>; rel="first",'
    '</admin/clients?page_size=5&page_token=QLux4Tu5gb8JfW70>; rel="next"'
)

next_token = get_next_page_token_from_link_header(link_header)
# Returns: "QLux4Tu5gb8JfW70"
```

### Link Header Format

Ory APIs return Link headers in RFC 5988 format:

```
<url>; rel="type", <url>; rel="type"
```

The function extracts the `page_token` query parameter from the `rel="next"` link.

### Integration with Kratos

```python
from fastapi_factory_utilities.core.services.kratos import (
    KratosIdentityGenericService,
)
from fastapi_factory_utilities.core.utils.ory import (
    get_next_page_token_from_link_header,
)

async def list_all_identities(service: KratosIdentityGenericService):
    all_identities = []
    page_token = None

    while True:
        # Make request with page_token
        async with service._kratos_admin_http_resource.acquire_client_session() as session:
            params = {"page_size": 100}
            if page_token:
                params["page_token"] = page_token

            async with session.get("/admin/identities", params=params) as response:
                identities = await response.json()
                all_identities.extend(identities.get("items", []))

                # Get next page token from Link header
                link_header = response.headers.get("Link")
                page_token = get_next_page_token_from_link_header(link_header)

                if not page_token:
                    break

    return all_identities
```

### Integration with Hydra

```python
from fastapi_factory_utilities.core.utils.ory import (
    get_next_page_token_from_link_header,
)

async def list_all_clients(hydra_admin_client):
    all_clients = []
    page_token = None

    while True:
        async with hydra_admin_client.acquire_client_session() as session:
            params = {"page_size": 100}
            if page_token:
                params["page_token"] = page_token

            async with session.get("/admin/oauth2/clients", params=params) as response:
                clients = await response.json()
                all_clients.extend(clients.get("items", []))

                link_header = response.headers.get("Link")
                page_token = get_next_page_token_from_link_header(link_header)

                if not page_token:
                    break

    return all_clients
```

## Link Header Parsing

The function uses regex to parse Link headers:

```python
# Pattern matches: <url>; rel="next"
pattern = re.compile(r'<([^>]+)>;\s*rel="next"')
```

Then extracts `page_token` from the URL query parameters.

## Error Handling

```python
link_header = response.headers.get("Link")
next_token = get_next_page_token_from_link_header(link_header)

if next_token:
    # Continue pagination
    pass
else:
    # No more pages
    break
```

## Best Practices

1. **Pagination**: Always check for next token before making additional requests
2. **Error Handling**: Handle None return value (no next page)
3. **Page Size**: Use appropriate page sizes (typically 100)
4. **Rate Limiting**: Be mindful of API rate limits when paginating
5. **Memory**: Consider streaming for large result sets

## Reference

- `src/fastapi_factory_utilities/core/utils/ory.py` - Ory utilities
