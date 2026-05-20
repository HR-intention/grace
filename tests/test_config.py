from __future__ import annotations

from pathlib import Path

import pytest

from grace.config import load_config
from grace.errors import GraceError, GraceErrorReason


def test_default_config_when_file_absent(tmp_path: Path) -> None:
    cfg = load_config(config_path=tmp_path / "missing.yaml")
    assert cfg.claude_code.cli_path is None
    assert cfg.claude_code.timeout_s == 6000
    assert cfg.quality.mypy_strict is True
    assert cfg.quality.min_coverage_pct == 80
    assert cfg.quality.min_rubric_score == 60
    assert cfg.lens.version_constraint == "^0.1"


def test_config_loaded_from_yaml(tmp_path: Path) -> None:
    p = tmp_path / "config.yaml"
    p.write_text(
        "claude_code:\n"
        "  cli_path: /usr/local/bin/claude\n"
        "  timeout_s: 600\n"
        "quality:\n"
        "  mypy_strict: false\n"
        "  min_coverage_pct: 85\n"
        "  min_rubric_score: 70\n"
        "lens:\n"
        "  version_constraint: '^0.2'\n"
    )
    cfg = load_config(config_path=p)
    assert str(cfg.claude_code.cli_path) == "/usr/local/bin/claude"
    assert cfg.claude_code.timeout_s == 600
    assert cfg.quality.mypy_strict is False
    assert cfg.quality.min_coverage_pct == 85
    assert cfg.quality.min_rubric_score == 70
    assert cfg.lens.version_constraint == "^0.2"


def test_invalid_yaml_raises_config_invalid(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("claude_code: not-a-mapping")
    with pytest.raises(GraceError) as exc:
        load_config(config_path=p)
    assert exc.value.reason is GraceErrorReason.CONFIG_INVALID
