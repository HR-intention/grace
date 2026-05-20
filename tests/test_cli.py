from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from grace.cli import main
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
    monkeypatch.setattr("grace.cli._default_docs_dir", lambda _psp: docs)
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
    monkeypatch.setattr("grace.cli._default_docs_dir", lambda _psp: empty)
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
    ) -> object:
        captured["include"] = include
        captured["exclude"] = exclude

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
