from __future__ import annotations

from pathlib import Path

from grace.quality_rubric import resolve_registered_class, composition_findings

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
