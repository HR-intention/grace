from __future__ import annotations

from pathlib import Path

from grace.pipeline.types import GenerationContext, PspDocs
from grace.quality_rubric import (
    resolve_registered_class,
    composition_findings,
    _score_public_surface_v2,
)

FX = Path(__file__).parent / "fixtures" / "connectors"


def _ctx_for(pkg: Path) -> GenerationContext:
    """Build a minimal GenerationContext for a fixture package.

    Only ``output_dir`` and ``reports_dir`` are read by the static scorers;
    the remaining fields satisfy the frozen dataclass constructor.
    """
    return GenerationContext(
        psp_name="demo",
        rulebook_paths=[],
        psp_docs=PspDocs(source_uri="x", source_kind="local_file"),
        output_dir=pkg,
        target_module="lens.connectors.demo",
        lens_version_constraint="^0.2",
        grace_version="0.6",
        source_version="t",
        reports_dir=pkg,
        domain="all",
    )


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


# ---------------------------------------------------------------------------
# T14 new tests (Parts 1–4)
# ---------------------------------------------------------------------------


def test_missing_register_webhook_docks_public_surface() -> None:
    from grace.quality_rubric import _score_public_surface_v2
    assert _score_public_surface_v2(FX / "missing_register_webhook").score < 20


def test_deprecated_typing_alias_flagged() -> None:
    from grace.quality_rubric import modern_typing_findings
    assert modern_typing_findings(FX / "uses_optional")
    assert not modern_typing_findings(FX / "compliant")


def test_error_handling_checks_root_webhooks_signature() -> None:
    from grace.quality_rubric import _score_error_handling_v2
    assert _score_error_handling_v2(FX / "compliant").score == 20


def test_unmapped_subscription_status_docks() -> None:
    from grace.quality_rubric import _score_public_surface_v2
    assert _score_public_surface_v2(FX / "unmapped_subscription_status").score < 20


# ---------------------------------------------------------------------------
# T15 — prove the domain-modular compliant fixture jointly scores >= 60
# ---------------------------------------------------------------------------


def test_compliant_fixture_jointly_scores_at_least_60() -> None:
    """Score the static compliant fixture through score_rubric with passing
    mypy/coverage reports and confirm total >= 60 with each static dimension
    at max.

    Note: marker_conformance will be 0 (fixture files have no §4 marker —
    expected and fine). Total still >= 60: type 20 + coverage 25 + public 20
    + error 20 + pii 10 = 95 even with marker 0.
    """
    from grace.pipeline.gates import MypyReport, PytestReport
    from grace.quality_rubric import score_rubric

    ctx = _ctx_for(FX / "compliant")
    report = score_rubric(
        ctx=ctx,
        output_dir=FX / "compliant",
        mypy_report=MypyReport(passed=True, stdout="", stderr=""),
        pytest_report=PytestReport(
            passed=True,
            coverage_pct=85.0,
            stdout="",
            stderr="",
            counts={"passed": 10},
        ),
    )
    assert report.total >= 60, report.to_json()
    by = {d.name: d for d in report.dimensions}
    assert by["public_surface"].score == 20, by["public_surface"].detail
    assert by["error_handling"].score == 20, by["error_handling"].detail
    assert by["pii_discipline"].score == 10, by["pii_discipline"].detail
    assert by["type_correctness"].score == 20, by["type_correctness"].detail  # passing mypy + no deprecated aliases
    assert by["test_coverage"].score == 25, by["test_coverage"].detail        # 85% >= 80%


def test_failing_reports_drop_the_total() -> None:
    """Failing mypy and low coverage reduce both dimensions to 0/partial."""
    from grace.pipeline.gates import MypyReport, PytestReport
    from grace.quality_rubric import score_rubric

    ctx = _ctx_for(FX / "compliant")
    report = score_rubric(
        ctx=ctx,
        output_dir=FX / "compliant",
        mypy_report=MypyReport(passed=False, stdout="x.py:1: error: boom", stderr=""),
        pytest_report=PytestReport(
            passed=True,
            coverage_pct=10.0,
            stdout="",
            stderr="",
            counts={"passed": 1},
        ),
    )
    by = {d.name: d for d in report.dimensions}
    assert by["type_correctness"].score == 0, by["type_correctness"].detail      # mypy failed
    assert by["test_coverage"].score < 25, by["test_coverage"].detail            # 10% < 80%


def test_plan_methods_registered_in_rubric(tmp_path: Path) -> None:
    """A subscriptions connector missing create_plan/change_plan must be docked."""
    from grace.quality_rubric import _V2_DOMAIN_METHODS
    assert "create_plan" in _V2_DOMAIN_METHODS["subscriptions"]
    assert "change_plan" in _V2_DOMAIN_METHODS["subscriptions"]
