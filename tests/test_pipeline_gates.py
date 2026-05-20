from __future__ import annotations

from pathlib import Path

from grace.pipeline.gates import _parse_pytest_counts, run_mypy, run_pytest_with_cov


def test_parse_pytest_counts_mixed() -> None:
    stdout = (
        "tests/test_a.py F.\n"
        "tests/test_b.py FF\n"
        "=========== 3 failed, 1 passed in 0.62s ===========\n"
    )
    counts = _parse_pytest_counts(stdout)
    assert counts == {"failed": 3, "passed": 1}


def test_parse_pytest_counts_all_pass() -> None:
    stdout = "================== 12 passed in 1.34s ==================\n"
    assert _parse_pytest_counts(stdout) == {"passed": 12}


def test_parse_pytest_counts_collection_error() -> None:
    stdout = "ERROR tests/test_a.py - ImportError\n=========== 1 error in 0.10s ===========\n"
    assert _parse_pytest_counts(stdout) == {"error": 1}


def test_parse_pytest_counts_empty() -> None:
    assert _parse_pytest_counts("no summary line here\n") == {}


def _make_clean_pkg(root: Path) -> Path:
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("x: int = 1\n")
    return pkg


def _make_broken_pkg(root: Path) -> Path:
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("x: int = 'oops'\n")
    return pkg


def test_run_mypy_clean(tmp_path: Path) -> None:
    pkg = _make_clean_pkg(tmp_path)
    report = run_mypy(target=pkg, strict=True)
    assert report.passed is True


def test_run_mypy_fails_on_type_error(tmp_path: Path) -> None:
    pkg = _make_broken_pkg(tmp_path)
    report = run_mypy(target=pkg, strict=True)
    assert report.passed is False
    assert "incompatible" in report.stdout.lower() or "error" in report.stdout.lower()


def test_run_pytest_with_cov_no_tests(tmp_path: Path) -> None:
    pkg = _make_clean_pkg(tmp_path)
    report = run_pytest_with_cov(target=pkg)
    assert report.coverage_pct == 0.0 or report.coverage_pct is None
