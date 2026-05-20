from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
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
    passed: bool                            # exit code 0 or 5 (no tests collected)
    coverage_pct: float | None
    stdout: str
    stderr: str
    counts: dict[str, int] = field(default_factory=dict)
    """Parsed from the pytest summary line: keys may include `passed`,
    `failed`, `error`, `skipped`. Empty if the run aborted before pytest
    printed its summary."""


def run_mypy(*, target: Path, strict: bool = True) -> MypyReport:
    """Invoke `mypy --strict <target>` (or non-strict) as a subprocess."""
    cmd = [sys.executable, "-m", "mypy"]
    if strict:
        cmd.append("--strict")
    cmd.append(str(target))
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return MypyReport(passed=proc.returncode == 0, stdout=proc.stdout, stderr=proc.stderr)


_PYTEST_SUMMARY_LINE_RE = re.compile(r"in [\d.]+s")
_PYTEST_COUNT_RE = re.compile(r"(\d+) (passed|failed|error|errors|skipped|warnings)\b")


def _parse_pytest_counts(stdout: str) -> dict[str, int]:
    """Extract `{passed, failed, error, skipped}` counts from pytest's
    terminal summary line ("10 failed, 2 passed in 0.62s"). Returns an
    empty dict if no summary line is present (e.g., collection aborted)."""
    for line in reversed(stdout.splitlines()):
        if _PYTEST_SUMMARY_LINE_RE.search(line) and (
            "passed" in line or "failed" in line or "error" in line
        ):
            out: dict[str, int] = {}
            for m in _PYTEST_COUNT_RE.finditer(line):
                key = m.group(2).rstrip("s")  # "errors" → "error"
                out[key] = int(m.group(1))
            return out
    return {}


def run_pytest_with_cov(*, target: Path) -> PytestReport:
    """Invoke pytest with coverage on the target package; parse the JSON report.

    NOTE: we deliberately do NOT pass `-q`. Quiet mode suppresses pytest's
    bottom summary line ("6 failed, 6 passed in 0.58s") when running under
    pytest-cov with a configured fail_under threshold — making it impossible
    to extract per-status counts from stdout. Without -q the summary is
    always present and `_parse_pytest_counts` can do its job.
    """
    json_report = target.parent / "_grace_coverage.json"
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--cov",
        str(target),
        "--cov-report",
        f"json:{json_report}",
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
    counts = _parse_pytest_counts(proc.stdout)
    return PytestReport(
        passed=passed,
        coverage_pct=pct,
        stdout=proc.stdout,
        stderr=proc.stderr,
        counts=counts,
    )


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

    # The pytest gate has TWO conditions: all tests must pass (exit 0) AND
    # coverage must be ≥ 80%. A run with 80% coverage but failing tests is
    # NOT a green run — Claude has been writing tests that fail (wrong path
    # assertions, wrong response-id assertions, HMAC mismatches) while still
    # exercising enough lines for the coverage figure to look respectable.
    failed_count = pytest_report.counts.get("failed", 0)
    error_count = pytest_report.counts.get("error", 0)
    passed_count = pytest_report.counts.get("passed", 0)
    tests_all_green = pytest_report.passed and failed_count == 0 and error_count == 0
    coverage_meets_threshold = coverage_pct >= 80.0

    tests_summary_parts: list[str] = []
    if passed_count or failed_count or error_count:
        tests_summary_parts.append(f"{passed_count} passed")
        if failed_count:
            tests_summary_parts.append(f"{failed_count} failed")
        if error_count:
            tests_summary_parts.append(f"{error_count} error(s)")
    else:
        tests_summary_parts.append("0 tests collected")
    tests_summary_parts.append(f"{coverage_pct:.1f}% coverage")
    tests_actual = ", ".join(tests_summary_parts)

    gates = {
        "mypy": {
            "passed": mypy_report.passed,
            "threshold": "clean (--strict)",
            "actual": "clean" if mypy_report.passed else f"{mypy_error_count} error(s)",
        },
        "tests": {
            "passed": tests_all_green and coverage_meets_threshold,
            "threshold": "all tests pass + ≥ 80% line coverage",
            "actual": tests_actual,
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
    run_stats: dict[str, float | int | None] = {}
    if result.cost_usd is not None:
        run_stats["cost_usd"] = round(result.cost_usd, 4)
    if result.duration_ms is not None:
        run_stats["duration_s"] = round(result.duration_ms / 1000.0, 1)
    report_payload: dict[str, object] = {
        "passed": overall_passed,
        "gates": gates,
        "rubric": rubric_payload,
    }
    if run_stats:
        report_payload["run"] = run_stats
    (result.output_dir / "quality_report.json").write_text(
        _json.dumps(report_payload, indent=2)
    )

    failures: list[str] = []
    if not gates["mypy"]["passed"]:
        last_line = (
            mypy_report.stdout.strip().splitlines()[-1] if mypy_report.stdout else "failed"
        )
        failures.append(f"mypy: {last_line}")
    if not gates["tests"]["passed"]:
        if not tests_all_green:
            failures.append(f"tests: {failed_count + error_count} failing")
        if not coverage_meets_threshold:
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
