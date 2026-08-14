"""Backward-compatible aliases for aiohttp plugin state keys."""

from fastapi_factory_utilities.core.plugins.state import AIOHTTP_RESOURCE_PREFIX

STATE_PREFIX_KEY: str = AIOHTTP_RESOURCE_PREFIX.attr
