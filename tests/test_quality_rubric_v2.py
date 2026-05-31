from __future__ import annotations

from pathlib import Path

from grace.quality_rubric import resolve_registered_class, composition_findings, _score_public_surface_v2

FX = Path(__file__).parent / "fixtures" / "connectors"


def test_resolve_registered_class_from_register_call() -> None:
    cls = resolve_registered_class(FX / "compliant")
    assert cls.name == "DemoConnector"
    assert {"PaymentsConnector", "MandateConnector"} <= set(cls.capability_bases)


def test_bare_connector_flagged() -> None:
    issues = composition_findings(FX / "bare_connector")
    assert any("capability interface" in i for i in issues)


def test_compliant_has_no_composition_issues() -> None:
    assert composition_findings(FX / "compliant") == []


def test_subscriptions_requires_lifecycle_and_introspection() -> None:
    dim = _score_public_surface_v2(FX / "missing_mandate_method")
    assert dim.score < dim.max and "cancel_subscription" in dim.detail


def test_orders_only_not_penalized_for_missing_mandate() -> None:
    dim = _score_public_surface_v2(FX / "orders_only")
    assert dim.score == dim.max


def test_compliant_scores_full_public_surface() -> None:
    dim = _score_public_surface_v2(FX / "compliant")
    assert dim.score == dim.max
