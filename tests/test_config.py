from __future__ import annotations

from pathlib import Path

import pytest

from grace.config import (
    load_config,
    load_config_with_source,
    set_config_value,
)
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


def test_paths_defaults() -> None:
    cfg = load_config(config_path=Path("/nonexistent"))
    assert cfg.paths.docs_dir == "connector_docs"
    assert cfg.paths.output_dir == "lens/connectors"
    assert cfg.paths.tests_dir is None


def test_paths_overridable(tmp_path: Path) -> None:
    p = tmp_path / "config.yaml"
    p.write_text(
        "paths:\n"
        "  docs_dir: my_docs\n"
        "  output_dir: src/lens/connectors\n"
        "  tests_dir: tests/connectors\n"
    )
    cfg = load_config(config_path=p)
    assert cfg.paths.docs_dir == "my_docs"
    assert cfg.paths.output_dir == "src/lens/connectors"
    assert cfg.paths.tests_dir == "tests/connectors"


def test_load_prefers_project_over_user(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When both <cwd>/.grace/config.yaml AND ~/.grace/config.yaml exist,
    the per-project file wins (no merge)."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    project_cfg = project_root / ".grace" / "config.yaml"
    project_cfg.parent.mkdir()
    project_cfg.write_text("paths:\n  output_dir: project/wins\n")

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    user_cfg = fake_home / ".grace" / "config.yaml"
    user_cfg.parent.mkdir()
    user_cfg.write_text("paths:\n  output_dir: user/loses\n")

    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.chdir(project_root)

    loaded = load_config_with_source()
    assert loaded.source == project_cfg
    assert loaded.config.paths.output_dir == "project/wins"


def test_load_falls_back_to_user_when_no_project_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project_root = tmp_path / "project_no_config"
    project_root.mkdir()
    fake_home = tmp_path / "home2"
    fake_home.mkdir()
    user_cfg = fake_home / ".grace" / "config.yaml"
    user_cfg.parent.mkdir()
    user_cfg.write_text("paths:\n  output_dir: from_user_home\n")
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.chdir(project_root)

    loaded = load_config_with_source()
    assert loaded.source == user_cfg
    assert loaded.config.paths.output_dir == "from_user_home"


def test_set_config_value_creates_file_and_persists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    written = set_config_value("paths.output_dir", "src/lens/connectors")
    assert written == tmp_path / ".grace" / "config.yaml"
    assert written.is_file()

    loaded = load_config_with_source()
    assert loaded.config.paths.output_dir == "src/lens/connectors"


def test_set_config_value_preserves_other_keys(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".grace").mkdir()
    (tmp_path / ".grace" / "config.yaml").write_text(
        "paths:\n  docs_dir: existing_docs\n"
        "claude_code:\n  timeout_s: 7000\n"
    )

    set_config_value("paths.output_dir", "src/lens/connectors")

    cfg = load_config()
    # The new key landed, AND the existing keys survived.
    assert cfg.paths.output_dir == "src/lens/connectors"
    assert cfg.paths.docs_dir == "existing_docs"
    assert cfg.claude_code.timeout_s == 7000


def test_set_config_value_refuses_bad_key() -> None:
    with pytest.raises(GraceError) as exc:
        set_config_value("not_dotted", "x")
    assert exc.value.reason is GraceErrorReason.CONFIG_INVALID


def test_set_config_value_refuses_value_that_fails_validation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Setting a value that wouldn't validate against the schema must
    refuse — and must NOT leave the file in a broken state."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(GraceError) as exc:
        set_config_value("paths.unknown_key", "x")
    assert exc.value.reason is GraceErrorReason.CONFIG_INVALID
    # Schema rejected the write — config file shouldn't exist (or shouldn't
    # contain the bad key).
    cfg_path = tmp_path / ".grace" / "config.yaml"
    if cfg_path.exists():
        assert "unknown_key" not in cfg_path.read_text()
