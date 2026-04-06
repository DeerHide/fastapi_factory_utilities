"""Unit tests for Aiopika name builders."""

from fastapi_factory_utilities.core.plugins.aiopika.builders import (
    EventRoutingKeyBuilder,
    ExchangeNameBuilder,
    ListenerRoutingKeyBuilder,
    QueueNameBuilder,
)
from fastapi_factory_utilities.core.plugins.aiopika.types import ExchangeName, QueueName, RoutingKey


class TestEventRoutingKeyBuilder:
    """Tests for EventRoutingKeyBuilder."""

    def test_default_segments(self) -> None:
        """Default placeholder segments build a predictable routing key."""
        assert str(EventRoutingKeyBuilder().build()) == "domain.service.entity.functional_event"

    def test_with_prefix(self) -> None:
        """Optional prefix is the first segment."""
        rk = EventRoutingKeyBuilder(prefix="pre").build()
        assert rk == RoutingKey("pre.domain.service.entity.functional_event")

    def test_fluent_overrides(self) -> None:
        """Chained setters override defaults."""
        rk = (
            EventRoutingKeyBuilder()
            .set_domain_name("dom")
            .set_service_name("svc")
            .set_entity_name("ent")
            .set_functional_event_name("evt")
            .build()
        )
        assert rk == RoutingKey("dom.svc.ent.evt")


class TestListenerRoutingKeyBuilder:
    """Tests for ListenerRoutingKeyBuilder."""

    def test_defaults_are_wildcards(self) -> None:
        """Listener builder uses wildcards for bound segments."""
        assert str(ListenerRoutingKeyBuilder().build()) == "*.*.*.*"

    def test_prefix_and_wildcards(self) -> None:
        """Prefix is preserved before wildcard segments."""
        rk = ListenerRoutingKeyBuilder(prefix="pre").build()
        assert rk == RoutingKey("pre.*.*.*.*")


class TestQueueNameBuilder:
    """Tests for QueueNameBuilder."""

    def test_only_prefix(self) -> None:
        """Single-segment queue name from prefix only."""
        qn = QueueNameBuilder(prefix="app").build()
        assert qn == QueueName("app")

    def test_full_chain(self) -> None:
        """All segments appear in order."""
        qn = (
            QueueNameBuilder()
            .set_prefix("pre")
            .set_domain_name("dom")
            .set_service_name("svc")
            .set_entity_name("ent")
            .set_functional_queue_name("jobs")
            .build()
        )
        assert qn == QueueName("pre.dom.svc.ent.jobs")


class TestExchangeNameBuilder:
    """Tests for ExchangeNameBuilder."""

    def test_empty_builds_default(self) -> None:
        """No segments yields default exchange name."""
        en = ExchangeNameBuilder().build()
        assert en == ExchangeName("default")

    def test_prefix_domain_service(self) -> None:
        """Prefix, domain, and service compose the exchange name."""
        en = ExchangeNameBuilder().set_prefix("vel").set_domain_name("orders").set_service_name("billing").build()
        assert en == ExchangeName("vel.orders.billing")
