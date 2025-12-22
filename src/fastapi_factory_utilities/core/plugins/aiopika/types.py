"""Provides the types for the Aiopika plugin."""

from typing import NewType

RoutingKey = NewType("RoutingKey", str)
ExchangeName = NewType("ExchangeName", str)
QueueName = NewType("QueueName", str)
