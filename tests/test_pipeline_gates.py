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


def test_run_pytest_with_cov_passes_test_paths_to_subprocess(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When `test_paths` is provided, pytest is invoked with those paths as
    discovery roots while `--cov` still measures `target` (the package).
    Captured via a subprocess.run stub so we don't depend on the surrounding
    test rig's sys.path."""
    import subprocess as _subprocess
    from grace.pipeline import gates as gates_mod

    pkg = tmp_path / "pkg"
    pkg.mkdir()
    external = tmp_path / "tests" / "connectors" / "demo"
    external.mkdir(parents=True)

    captured: dict[str, list[str]] = {}

    class _FakeProc:
        returncode = 0
        stdout = "1 passed in 0.01s\n"
        stderr = ""

    def fake_run(cmd: list[str], **kwargs: object) -> _FakeProc:
        captured["cmd"] = list(cmd)
        return _FakeProc()

    monkeypatch.setattr(gates_mod.subprocess, "run", fake_run)

    run_pytest_with_cov(target=pkg, test_paths=[external])

    cmd = captured["cmd"]
    # --cov target is the package (coverage measures the right code)
    cov_idx = cmd.index("--cov")
    assert cmd[cov_idx + 1] == str(pkg)
    # The external path is in the positional args
    assert str(external) in cmd
    # And the original package path is NOT used as a discovery root
    # (the trailing positional in the legacy invocation)
    assert cmd[-1] == str(external)


def test_run_pytest_with_cov_defaults_test_paths_to_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When `test_paths` is omitted, pytest discovers tests from `target` —
    the legacy in-package layout."""
    from grace.pipeline import gates as gates_mod

    pkg = tmp_path / "pkg"
    pkg.mkdir()

    captured: dict[str, list[str]] = {}

    class _FakeProc:
        returncode = 0
        stdout = "no tests ran in 0.01s\n"
        stderr = ""

    def fake_run(cmd: list[str], **kwargs: object) -> _FakeProc:
        captured["cmd"] = list(cmd)
        return _FakeProc()

    monkeypatch.setattr(gates_mod.subprocess, "run", fake_run)

    run_pytest_with_cov(target=pkg)
    assert captured["cmd"][-1] == str(pkg)
