from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from grace.cli import main


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
