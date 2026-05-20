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
    """Run mypy + pytest + rubric. Raise GraceError if any gate fails."""
    from grace.quality_rubric import RubricReport, score_rubric

    mypy_report = run_mypy(target=result.output_dir, strict=True)
    pytest_report = run_pytest_with_cov(target=result.output_dir)
    rubric: RubricReport = score_rubric(
        ctx=ctx,
        output_dir=result.output_dir,
        mypy_report=mypy_report,
        pytest_report=pytest_report,
    )
    # Always write the report next to the package.
    (result.output_dir / "quality_report.json").write_text(rubric.to_json())

    failures: list[str] = []
    if not mypy_report.passed:
        last_line = (
            mypy_report.stdout.strip().splitlines()[-1] if mypy_report.stdout else "failed"
        )
        failures.append(f"mypy: {last_line}")
    if pytest_report.coverage_pct is not None and pytest_report.coverage_pct < 80.0:
        failures.append(f"coverage: {pytest_report.coverage_pct:.1f}% < 80%")
    if rubric.total < 60:
        failures.append(f"rubric: {rubric.total} < 60")
    if failures:
        raise GraceError(
            reason=GraceErrorReason.QUALITY_GATE_FAILED,
            detail="; ".join(failures),
        )
