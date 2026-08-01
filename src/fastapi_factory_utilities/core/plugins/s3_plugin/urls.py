"""Canonical object-URL encode/decode for S3 / MinIO path-style URLs."""

from urllib.parse import quote, unquote, urlparse, urlsplit, urlunsplit

# path-style URL needs at least /{bucket}/{key}
_MIN_PATH_SEGMENTS: int = 2


def build_object_url(*, endpoint_url: str, bucket_name: str, key: str) -> str:
    """Build a path-style object URL with percent-encoded key segments.

    Args:
        endpoint_url: S3 / MinIO endpoint (scheme + host).
        bucket_name: Physical bucket name.
        key: Object key inside the bucket.

    Returns:
        ``{endpoint}/{bucket}/{quoted_key}``.
    """
    base: str = endpoint_url.rstrip("/")
    encoded_key: str = quote(key, safe="/")
    return f"{base}/{bucket_name}/{encoded_key}"


def parse_bucket_and_key(url: str) -> tuple[str, str] | None:
    """Extract ``(bucket, key)`` from a path-style object URL.

    The host is ignored so persisted URLs remain resolvable after endpoint changes.
    Keys are ``unquote``d.

    Args:
        url: Absolute path-style storage URL.

    Returns:
        Tuple of bucket name and object key, or ``None`` when parsing fails.
    """
    segments: list[str] = [segment for segment in unquote(urlparse(url).path).split("/") if segment]
    if len(segments) < _MIN_PATH_SEGMENTS:
        return None
    bucket_name, *key_segments = segments
    return bucket_name, "/".join(key_segments)


def key_from_url(*, url: str, bucket_name: str) -> str | None:
    """Extract the object key for ``bucket_name`` from a stored URL.

    Accepts path-style (``/<bucket>/<key>``) and virtual-host style
    (``<bucket>.host/<key>``). The host is otherwise ignored.

    Args:
        url: Absolute storage URL.
        bucket_name: Expected physical bucket name.

    Returns:
        Object key, or ``None`` if the URL does not reference ``bucket_name``.
    """
    parsed = urlparse(url)
    segments: list[str] = [segment for segment in unquote(parsed.path).split("/") if segment]
    if not segments:
        return None
    if segments[0] == bucket_name:
        return "/".join(segments[1:]) if len(segments) > 1 else None
    if parsed.netloc.startswith(f"{bucket_name}."):
        return "/".join(segments)
    return None


def inject_public_path_prefix(url: str, path_prefix: str | None) -> str:
    """Prefix a signed URL path with the public proxy path segment.

    botocore signs against ``scheme://netloc`` only; Gateways that serve under
    ``/storage/<bucket>/<key>`` need the path re-injected after signing.

    Args:
        url: Presigned URL from the signing client.
        path_prefix: Path prefix such as ``/storage``, or ``None``.

    Returns:
        URL with the public path prefix applied when configured.
    """
    if not path_prefix:
        return url
    prefix: str = path_prefix.rstrip("/")
    if not prefix:
        return url
    parts = urlsplit(url)
    if parts.path.startswith(f"{prefix}/") or parts.path == prefix:
        return url
    return urlunsplit((parts.scheme, parts.netloc, f"{prefix}{parts.path}", parts.query, parts.fragment))
