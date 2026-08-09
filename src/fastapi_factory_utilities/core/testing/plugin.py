"""Pytest plugin entry point — registers infra test-double fixtures.

Optional deps (``pymongo-async-mock``, ``fakeredis``, ``moto``) are imported
lazily inside builders so installing the library without the ``testing`` extra
does not break pytest collection for unrelated tests. Fixture registration
requires those extras when the fixtures are used.
"""

# Importing the fixtures module registers them with pytest via the pytest11
# entry point (fixture functions are discovered from this plugin module's
# namespace after star-import).
from fastapi_factory_utilities.core.testing.fixtures import *  # noqa: F403 pylint: disable=wildcard-import,unused-wildcard-import
