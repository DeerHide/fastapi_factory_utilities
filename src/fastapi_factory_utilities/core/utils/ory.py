"""Provides utility functions for Ory."""

import re
from urllib.parse import parse_qs, urlparse


def get_next_page_token_from_link_header(link_header: str | None) -> str | None:
    """Parse the Link header and extract the next page token.

    Args:
        link_header (str | None): The Link header value from the HTTP response.

    Returns:
        str | None: The next page token if found, None otherwise.

    Example:
        >>> link_header = (
        ...     '</admin/clients?page_size=5&page_token=euKoY1BqY3J8GVax>; rel="first",'
        ...     '</admin/clients?page_size=5&page_token=QLux4Tu5gb8JfW70>; rel="next"'
        ... )
        >>> token = KratosIdentityGenericService._parse_link_header(link_header)
        >>> print(token)
        'QLux4Tu5gb8JfW70'
    """
    if link_header is None:
        return None

    # Parse Link header: <url>; rel="type", <url>; rel="type"
    # Find all links with rel="next"
    pattern: re.Pattern[str] = re.compile(r'<([^>]+)>;\s*rel="next"')
    matches: list[str] = pattern.findall(link_header)

    if not matches:
        return None

    # Get the first match (should only be one "next" link)
    next_url: str = matches[0]

    # Parse the URL to extract query parameters
    parsed_url = urlparse(next_url)
    query_params: dict[str, list[str]] = parse_qs(parsed_url.query)

    # Extract page_token from query parameters
    page_tokens: list[str] | None = query_params.get("page_token")
    if page_tokens and len(page_tokens) > 0:
        return page_tokens[0]

    return None
