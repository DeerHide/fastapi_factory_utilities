"""Hydra types module."""

from typing import NewType

HydraAccessToken = NewType("HydraAccessToken", str)
HydraClientId = NewType("HydraClientId", str)
HydraClientSecret = NewType("HydraClientSecret", str)

__all__: list[str] = [
    "HydraAccessToken",
    "HydraClientId",
    "HydraClientSecret",
]
