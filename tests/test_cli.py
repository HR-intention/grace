from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from grace.cli import main
from grace.config import set_config_value  # noqa: F401  (used implicitly via CLI)
from grace.errors import GraceError, GraceErrorReason


def test_version_flag() -> None:
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "grace" in result.output.lower()


def test_doctor_reports_status(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_is_available(self: object) -> tuple[bool, str]:
        return (True, "Claude Code v0.1.0")

    monkeypatch.setattr(
        "grace.pipeline.runner.ClaudeCodeRunner.is_available", fake_is_available
    )
    result = CliRunner().invoke(main, ["doctor"])
    assert result.exit_code == 0
    assert "healthy" in result.output.lower() or "ok" in result.output.lower()


def test_doctor_reports_unhealthy(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_is_available(self: object) -> tuple[bool, str]:
        return (False, "binary not found")

    monkeypatch.setattr(
        "grace.pipeline.runner.ClaudeCodeRunner.is_available", fake_is_available
    )
    result = CliRunner().invoke(main, ["doctor"])
    assert result.exit_code == 1
    assert "binary not found" in result.output


def test_generate_calls_pipeline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    called: dict[str, object] = {}

    async def fake_run_pipeline(*, ctx: object, runner: object, hooks: object) -> None:
        called["psp"] = ctx.psp_name  # type: ignore[attr-defined]
        called["target"] = ctx.target_module  # type: ignore[attr-defined]
        return None

    monkeypatch.setattr("grace.cli._run_pipeline", fake_run_pipeline)

    spec = tmp_path / "openapi.yaml"
    spec.write_text("openapi: 3.0.0")
    out = tmp_path / "out"
    result = CliRunner().invoke(
        main, ["generate", "cashfree", "--from", str(spec), "--output", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert called["psp"] == "cashfree"
    assert called["target"] == "lens.connectors.cashfree"


def test_generate_defaults_to_connector_docs_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When --from is omitted, generate falls back to <repo>/connector_docs/<psp>/."""
    fake_repo = tmp_path / "repo"
    docs = fake_repo / "connector_docs" / "demo"
    docs.mkdir(parents=True)
    (docs / "00_overview.md").write_text("# overview")
    # The Grace rulebook needs to exist under fake_repo too; cheaper to point
    # _repo_root at the real repo and just shim _default_docs_dir.
    real_repo = Path(__file__).resolve().parents[1]
    monkeypatch.setattr("grace.cli._default_docs_dir", lambda _psp, _cfg=None: docs)
    monkeypatch.setattr("grace.cli._repo_root", lambda: real_repo)

    captured: dict[str, str] = {}

    async def fake_run_pipeline(*, ctx: object, runner: object, hooks: object) -> None:
        captured["source"] = ctx.psp_docs.source_uri  # type: ignore[attr-defined]
        return None

    monkeypatch.setattr("grace.cli._run_pipeline", fake_run_pipeline)

    out = tmp_path / "out"
    result = CliRunner().invoke(main, ["generate", "demo", "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert captured["source"] == str(docs)


def test_generate_missing_docs_dir_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No --from + empty connector_docs/<psp>/ → ClickException with a hint."""
    empty = tmp_path / "connector_docs" / "empty"
    empty.mkdir(parents=True)
    monkeypatch.setattr("grace.cli._default_docs_dir", lambda _psp, _cfg=None: empty)
    result = CliRunner().invoke(main, ["generate", "empty"])
    assert result.exit_code != 0
    assert "fetch-docs" in result.output


def test_fetch_docs_cli_writes_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_fetch_docs(
        *,
        psp_name: str,
        source: str,
        output_dir: Path,
        include: object,
        exclude: object,
        domain: object = "all",
    ) -> object:
        captured["psp_name"] = psp_name
        captured["source"] = source
        captured["output_dir"] = output_dir
        captured["include"] = include
        captured["exclude"] = exclude

        out_dir = output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "01_x.md").write_text("# x")

        class _Result:
            output_dir = out_dir
            files_written = [out_dir / "01_x.md"]
            skipped_count = 3

        return _Result()

    monkeypatch.setattr("grace.cli.fetch_docs", fake_fetch_docs)

    out = tmp_path / "connector_docs" / "cashfree"
    result = CliRunner().invoke(
        main,
        [
            "fetch-docs",
            "cashfree",
            "--from",
            "https://example.com/llms.txt",
            "--include",
            "*/orders/*",
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "1 files" in result.output
    assert captured["psp_name"] == "cashfree"
    assert captured["include"] == ["*/orders/*"]


def test_generate_prints_actionable_hint_on_401(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A CLAUDE_CODE_NOT_AUTHENTICATED from the pipeline surfaces with the
    `claude setup-token` hint, not a bare reason code."""

    async def fake_run_pipeline(*, ctx: object, runner: object, hooks: object) -> None:
        raise GraceError(
            reason=GraceErrorReason.CLAUDE_CODE_NOT_AUTHENTICATED,
            detail='API Error: 401 {"type":"authentication_error"}',
        )

    monkeypatch.setattr("grace.cli._run_pipeline", fake_run_pipeline)

    spec = tmp_path / "docs"
    spec.mkdir()
    (spec / "x.md").write_text("# x")
    result = CliRunner().invoke(
        main,
        ["generate", "cashfree", "--from", str(spec), "--output", str(tmp_path / "out")],
    )
    assert result.exit_code != 0
    out = result.output
    assert "CLAUDE_CODE_NOT_AUTHENTICATED" in out
    assert "claude setup-token" in out
    assert "CLAUDE_CODE_OAUTH_TOKEN" in out
    # The underlying detail is preserved alongside the hint.
    assert "API Error: 401" in out
    # The README pointer / GitHub issue tag is mentioned for further reading.
    assert "anthropics/claude-code" in out


def test_config_show_with_no_file_lists_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["config", "show"])
    assert result.exit_code == 0, result.output
    assert "defaults" in result.output
    assert "connector_docs" in result.output     # docs_dir default
    assert "lens/connectors" in result.output    # output_dir default


def test_config_set_then_show_reflects_change(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    set_result = CliRunner().invoke(
        main, ["config", "set", "paths.output_dir", "src/lens/connectors"]
    )
    assert set_result.exit_code == 0, set_result.output
    show_result = CliRunner().invoke(main, ["config", "show"])
    assert "src/lens/connectors" in show_result.output
    # And the file actually exists on disk.
    assert (tmp_path / ".grace" / "config.yaml").is_file()


def test_config_get_returns_single_value(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    CliRunner().invoke(main, ["config", "set", "paths.docs_dir", "my_docs"])
    result = CliRunner().invoke(main, ["config", "get", "paths.docs_dir"])
    assert result.exit_code == 0, result.output
    assert "my_docs" in result.output


def test_generate_uses_configured_output_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A `grace config set paths.output_dir src/lens/connectors` makes the
    next `grace generate <psp>` (with no --output) land there."""
    monkeypatch.chdir(tmp_path)
    CliRunner().invoke(main, ["config", "set", "paths.output_dir", "src/lens/connectors"])

    captured: dict[str, object] = {}

    async def fake_run_pipeline(*, ctx: object, runner: object, hooks: object) -> None:
        captured["output_dir"] = ctx.output_dir  # type: ignore[attr-defined]

    monkeypatch.setattr("grace.cli._run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(
        "grace.cli.build_docs",
        lambda lens_root, connectors_subpath="lens/connectors": type("R", (), {
            "output_root": tmp_path / "docs-generated", "connectors": []
        })(),
    )

    spec = tmp_path / "docs"
    spec.mkdir()
    (spec / "x.md").write_text("# x")
    result = CliRunner().invoke(main, ["generate", "cashfree", "--from", str(spec)])
    assert result.exit_code == 0, result.output
    expected = (tmp_path / "src" / "lens" / "connectors" / "cashfree").resolve()
    assert Path(str(captured["output_dir"])).resolve() == expected


def test_generate_records_last_run_even_when_pipeline_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A pipeline that raises (e.g., QUALITY_GATE_FAILED) must still leave
    a recoverable last_run.json so `grace regenerate` can replay the args.
    The record lives under <cwd>/.grace/ so per-project state stays
    per-project."""
    project_root = tmp_path / "consumer_repo"
    project_root.mkdir()
    monkeypatch.chdir(project_root)

    async def fake_run_pipeline(*, ctx: object, runner: object, hooks: object) -> None:
        raise GraceError(reason=GraceErrorReason.QUALITY_GATE_FAILED, detail="55 < 60")

    monkeypatch.setattr("grace.cli._run_pipeline", fake_run_pipeline)

    spec = tmp_path / "docs"
    spec.mkdir()
    (spec / "x.md").write_text("# x")

    result = CliRunner().invoke(
        main,
        ["generate", "cashfree", "--from", str(spec), "--output", str(tmp_path / "out")],
    )
    # Pipeline failed → non-zero exit, but the last-run record IS written.
    assert result.exit_code != 0
    last_run = project_root / ".grace" / "last_run.json"
    assert last_run.is_file()
    data = json.loads(last_run.read_text())
    assert data["psp"] == "cashfree"
    assert data["source"] == str(spec)


def test_generate_last_run_isolated_per_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Two different cwds → two independent last_run records. The whole
    point of moving the file from ~/.grace to <cwd>/.grace."""

    async def noop_pipeline(*, ctx: object, runner: object, hooks: object) -> None:
        return None

    monkeypatch.setattr("grace.cli._run_pipeline", noop_pipeline)

    spec_a = tmp_path / "docs_a"
    spec_a.mkdir()
    (spec_a / "a.md").write_text("# a")
    spec_b = tmp_path / "docs_b"
    spec_b.mkdir()
    (spec_b / "b.md").write_text("# b")

    project_a = tmp_path / "project_a"
    project_a.mkdir()
    project_b = tmp_path / "project_b"
    project_b.mkdir()

    # Project A generates first.
    monkeypatch.chdir(project_a)
    res_a = CliRunner().invoke(
        main,
        ["generate", "cashfree", "--from", str(spec_a), "--output", str(tmp_path / "out_a")],
    )
    assert res_a.exit_code == 0, res_a.output

    # Project B generates next — must not see project A's args.
    monkeypatch.chdir(project_b)
    res_b = CliRunner().invoke(
        main,
        ["generate", "cashfree", "--from", str(spec_b), "--output", str(tmp_path / "out_b")],
    )
    assert res_b.exit_code == 0, res_b.output

    data_a = json.loads((project_a / ".grace" / "last_run.json").read_text())
    data_b = json.loads((project_b / ".grace" / "last_run.json").read_text())
    assert data_a["source"] == str(spec_a)
    assert data_b["source"] == str(spec_b)
    # Project A's record didn't get clobbered by project B's run.
    assert data_a != data_b


def test_generate_prints_hint_on_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    async def fake_run_pipeline(*, ctx: object, runner: object, hooks: object) -> None:
        raise GraceError(
            reason=GraceErrorReason.CLAUDE_CODE_TIMEOUT,
            detail="claude did not finish within 6000.0s",
        )

    monkeypatch.setattr("grace.cli._run_pipeline", fake_run_pipeline)

    spec = tmp_path / "docs"
    spec.mkdir()
    (spec / "x.md").write_text("# x")
    result = CliRunner().invoke(
        main,
        ["generate", "cashfree", "--from", str(spec), "--output", str(tmp_path / "out")],
    )
    assert result.exit_code != 0
    assert "CLAUDE_CODE_TIMEOUT" in result.output
    assert "timeout_s" in result.output
    assert "did not finish within 6000.0s" in result.output


def test_docs_cli_writes_under_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`grace docs` runs build_docs against Path.cwd() and prints a success line."""
    fake_root = tmp_path / "lens-checkout"
    pkg = fake_root / "lens" / "connectors" / "demo"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(
        'requires_lens = "^0.1"\n'
        "from .connector import Demo\n"
        "from lens.factory import ConnectorFactory\n"
        'ConnectorFactory.register("demo", Demo)\n'
    )
    (pkg / "connector.py").write_text(
        "from lens.connector import Connector\n"
        "class Demo(Connector):\n"
        "    async def create_order(self, request): ...\n"
        "    async def sync_payment(self, request): ...\n"
        "    async def refund(self, request): ...\n"
        "    async def sync_refund(self, request): ...\n"
        "    async def handle_webhook(self, raw_payload, headers): ...\n"
        "    async def close(self): ...\n"
    )
    (pkg / "status_map.py").write_text("STATUS_MAP = {}\n")

    monkeypatch.chdir(fake_root)
    result = CliRunner().invoke(main, ["docs"])
    assert result.exit_code == 0, result.output
    assert "1 connectors discovered" in result.output
    assert (fake_root / "docs-generated" / "llms.txt").is_file()
    assert (fake_root / "docs-generated" / "connectors" / "demo.md").is_file()


def test_skills_list_cli_prints_add_connector() -> None:
    result = CliRunner().invoke(main, ["skills", "list"])
    assert result.exit_code == 0, result.output
    assert "add-connector" in result.output


def test_skills_install_cli_writes_to_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["skills", "install"])
    assert result.exit_code == 0, result.output
    assert "add-connector" in result.output
    assert (tmp_path / ".skills" / "add-connector" / "SKILL.md").is_file()


def test_skills_install_cli_force_overrides_existing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    # First install — clean.
    CliRunner().invoke(main, ["skills", "install"])
    # Second install — should refuse without --force.
    second = CliRunner().invoke(main, ["skills", "install"])
    assert second.exit_code != 0
    assert "force" in second.output.lower()
    # Third install with --force succeeds.
    third = CliRunner().invoke(main, ["skills", "install", "--force"])
    assert third.exit_code == 0


def test_docs_cli_errors_when_no_connectors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["docs"])
    assert result.exit_code != 0
    assert "CONTEXT_BUNDLE_INVALID" in result.output
    assert "grace generate" in result.output


def test_fetch_docs_cli_defaults_include_when_unset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    def fake_fetch_docs(
        *,
        psp_name: str,
        source: str,
        output_dir: Path,
        include: object,
        exclude: object,
        domain: object = "all",
    ) -> object:
        captured["include"] = include
        captured["exclude"] = exclude
        captured["domain"] = domain

        out_dir = output_dir

        class _R:
            output_dir = out_dir
            files_written: list[Path] = []
            skipped_count = 0

        return _R()

    monkeypatch.setattr("grace.cli.fetch_docs", fake_fetch_docs)
    result = CliRunner().invoke(
        main,
        ["fetch-docs", "cashfree", "--from", "x.txt", "--output", str(tmp_path / "out")],
    )
    assert result.exit_code == 0, result.output
    assert captured["include"] is None
    assert captured["exclude"] is None
    assert captured["domain"] == "all"
