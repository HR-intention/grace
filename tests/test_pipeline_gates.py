from __future__ import annotations

from pathlib import Path

from grace.pipeline.gates import run_mypy, run_pytest_with_cov


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
