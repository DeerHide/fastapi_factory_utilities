"""Helpers for optional plugin extras."""

from importlib.util import find_spec

from fastapi_factory_utilities.core.exceptions import MissingExtraError

# (extra name, importable module that extra provides)
PLUGIN_BACKENDS: tuple[tuple[str, str], ...] = (
    ("mongo", "beanie"),
    ("amqp", "aio_pika"),
    ("s3", "aioboto3"),
    ("redis", "redis"),
    ("taskiq", "taskiq_redis"),
    ("otel", "opentelemetry.sdk"),
)


def require_extra(extra: str, module: str) -> None:
    """Raise ``MissingExtraError`` when the extra's backend package is absent.

    Args:
        extra: Poetry extra name (``mongo``, ``amqp``, ``s3``, ``redis``, ``taskiq``, ``otel``).
        module: Importable module that extra is expected to provide.

    Raises:
        MissingExtraError: If ``module`` cannot be found.
    """
    if find_spec(module) is None:
        raise MissingExtraError(extra=extra, module=module)
