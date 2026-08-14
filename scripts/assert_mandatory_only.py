"""Fail if optional backends leaked into a no-extras install.

Used by the CI ``mandatory-only`` job (task 4.6).
"""

from __future__ import annotations

import importlib.util
import sys

FORBIDDEN_MODULES: tuple[str, ...] = (
    "aio_pika",
    "aioboto3",
    "beanie",
    "redis",
    "taskiq_redis",
    "opentelemetry.sdk",
    "granian",
    "hypercorn",
)
REQUIRED_MODULES: tuple[str, ...] = (
    "uvicorn",
    "fastapi",
)


def main() -> int:
    """Return 1 when the mandatory-only environment is wrong."""
    failures: list[str] = []
    for name in FORBIDDEN_MODULES:
        if importlib.util.find_spec(name) is not None:
            failures.append(f"optional backend present: {name}")
    for name in REQUIRED_MODULES:
        if importlib.util.find_spec(name) is None:
            failures.append(f"mandatory package missing: {name}")

    try:
        from fastapi_factory_utilities.core.app import (  # noqa: PLC0415  # pylint: disable=import-outside-toplevel
            ApplicationAbstract,
            ApplicationGenericBuilder,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        failures.append(f"core.app import failed: {exc}")
    else:
        _ = (ApplicationAbstract, ApplicationGenericBuilder)

    if failures:
        print("mandatory-only install is wrong:", file=sys.stderr)
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print("mandatory-only install is clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
