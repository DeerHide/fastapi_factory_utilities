"""Redis test doubles via fakeredis."""

from redis.asyncio import Redis


def build_fakeredis() -> Redis:
    """Build a ``fakeredis`` async client (API-compatible with ``redis.asyncio.Redis``).

    Returns:
        An in-memory async Redis client.

    Raises:
        ImportError: When ``fakeredis`` is not installed.
    """
    try:
        from fakeredis import FakeAsyncRedis  # pylint: disable=import-outside-toplevel  # noqa: PLC0415
    except ImportError as error:
        raise ImportError(
            "fakeredis is required for Redis test doubles. "
            "Install with: pip install 'fastapi_factory_utilities[testing]'",
        ) from error
    return FakeAsyncRedis(decode_responses=True)
