from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from grace.errors import GraceError, GraceErrorReason
from grace.pipeline.types import GenerationContext, GenerationResult


@dataclass(frozen=True)
class MypyReport:
    passed: bool
    stdout: str
    stderr: str


@dataclass(frozen=True)
class PytestReport:
    passed: bool
    coverage_pct: float | None
    stdout: str
    stderr: str


def run_mypy(*, target: Path, strict: bool = True) -> MypyReport:
    """Invoke `mypy --strict <target>` (or non-strict) as a subprocess."""
    cmd = [sys.executable, "-m", "mypy"]
    if strict:
        cmd.append("--strict")
    cmd.append(str(target))
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return MypyReport(passed=proc.returncode == 0, stdout=proc.stdout, stderr=proc.stderr)


def run_pytest_with_cov(*, target: Path) -> PytestReport:
    """Invoke pytest with coverage on the target package; parse the JSON report."""
    json_report = target.parent / "_grace_coverage.json"
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--cov",
        str(target),
        "--cov-report",
        f"json:{json_report}",
        "-q",
        str(target),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    pct: float | None = None
    if json_report.exists():
        try:
            data = json.loads(json_report.read_text())
            pct = float(data.get("totals", {}).get("percent_covered", 0.0))
        except (ValueError, OSError):
            pct = None
    # pytest exits 5 when no tests collected — treat as 0% rather than failure.
    passed = proc.returncode in (0, 5)
    return PytestReport(passed=passed, coverage_pct=pct, stdout=proc.stdout, stderr=proc.stderr)


def run_gates_blocking(*, ctx: GenerationContext, result: GenerationResult) -> None:
    """Run mypy + pytest + rubric. Raise GraceError if any gate fails.

    Three independent gates per constitution §4 (`SUBPROJECT_GRACE_CODEGEN.md`):
      - mypy --strict clean (binary)
      - pytest --cov ≥ 80% (binary hard floor)
      - Rubric ≥ 60/100 (graded, includes coverage as a dimension with
        linear scaling — that's where the "report passed but gate failed"
        drift used to come from)

    The combined `quality_report.json` exposes each gate's decision
    explicitly so the report and the CLI error never disagree again.
    """
    import json as _json

    from grace.quality_rubric import RubricReport, score_rubric

    # The runner is supposed to materialize this directory but defend against the
    # zero-files case (e.g. a stub runner in tests, or a Claude run that wrote nothing).
    result.output_dir.mkdir(parents=True, exist_ok=True)
    mypy_report = run_mypy(target=result.output_dir, strict=True)
    pytest_report = run_pytest_with_cov(target=result.output_dir)
    rubric: RubricReport = score_rubric(
        ctx=ctx,
        output_dir=result.output_dir,
        mypy_report=mypy_report,
        pytest_report=pytest_report,
    )

    coverage_pct = pytest_report.coverage_pct if pytest_report.coverage_pct is not None else 0.0
    mypy_error_count = _count_mypy_errors(mypy_report.stdout)
    gates = {
        "mypy": {
            "passed": mypy_report.passed,
            "threshold": "clean (--strict)",
            "actual": "clean" if mypy_report.passed else f"{mypy_error_count} error(s)",
        },
        "coverage": {
            "passed": coverage_pct >= 80.0,
            "threshold": "≥ 80% line coverage",
            "actual": f"{coverage_pct:.1f}%",
        },
        "rubric": {
            "passed": rubric.total >= 60,
            "threshold": "≥ 60 / 100",
            "actual": rubric.total,
        },
    }
    overall_passed = all(bool(g["passed"]) for g in gates.values())

    rubric_payload = rubric.to_dict()
    # The nested rubric block keeps its own `passed` field (rubric-only ≥ 60).
    # Top-level `passed` reflects ALL gates — no more drift between report and CLI.
    report_payload = {
        "passed": overall_passed,
        "gates": gates,
        "rubric": rubric_payload,
    }
    (result.output_dir / "quality_report.json").write_text(
        _json.dumps(report_payload, indent=2)
    )

    failures: list[str] = []
    if not gates["mypy"]["passed"]:
        last_line = (
            mypy_report.stdout.strip().splitlines()[-1] if mypy_report.stdout else "failed"
        )
        failures.append(f"mypy: {last_line}")
    if not gates["coverage"]["passed"]:
        failures.append(f"coverage: {coverage_pct:.1f}% < 80%")
    if not gates["rubric"]["passed"]:
        failures.append(f"rubric: {rubric.total} < 60")
    if failures:
        raise GraceError(
            reason=GraceErrorReason.QUALITY_GATE_FAILED,
            detail="; ".join(failures),
        )


def _count_mypy_errors(stdout: str) -> int:
    return sum(1 for line in stdout.splitlines() if ": error:" in line)
