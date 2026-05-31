"""T16 — docs_build composed-connector discovery tests.

Verifies that ``introspect_connector`` correctly resolves a domain-modular
(composed) connector class and surfaces mandate flows on the summary.
"""

from __future__ import annotations

from pathlib import Path

from grace.docs_build import introspect_connector


_COMPLIANT = Path(__file__).parent / "fixtures" / "connectors" / "compliant"


def test_docs_build_finds_composed_class() -> None:
    """introspect_connector must resolve the composed DemoConnector class,
    not fall back to 'Unknown' from the old class Foo(Connector) search.
    """
    s = introspect_connector(_COMPLIANT)
    assert s.class_name == "DemoConnector"
    # mandate capability discovered (either as a flow or a recorded domain)
    assert "create_subscription" in s.flows or "subscriptions" in getattr(s, "domains", [])


def test_docs_build_includes_payment_flows() -> None:
    """Payment flows must still be surfaced from the MRO."""
    s = introspect_connector(_COMPLIANT)
    for flow in ("create_order", "sync_payment", "refund", "sync_refund"):
        assert flow in s.flows, f"missing payment flow: {flow}"


def test_docs_build_mandate_flows_in_summary() -> None:
    """Mandate lifecycle flows must be surfaced from the MRO."""
    s = introspect_connector(_COMPLIANT)
    for flow in (
        "create_subscription",
        "sync_subscription",
        "cancel_subscription",
        "pause_subscription",
        "resume_subscription",
    ):
        assert flow in s.flows, f"missing mandate flow: {flow}"


def test_docs_build_no_handle_webhook_in_flows() -> None:
    """handle_webhook must NOT appear in LOCKED_FLOWS (dropped in T16)."""
    s = introspect_connector(_COMPLIANT)
    assert "handle_webhook" not in s.flows


def test_docs_build_per_domain_status_terms() -> None:
    """Status terms must be collected from per-domain status_map.py files."""
    # The compliant fixture has empty STATUS_MAPs, so nothing to assert on
    # content, but the call must succeed without raising.
    s = introspect_connector(_COMPLIANT)
    assert isinstance(s.psp_status_terms, list)
