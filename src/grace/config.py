from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from grace.errors import GraceError, GraceErrorReason


class ClaudeCodeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    cli_path: Path | None = None
    timeout_s: float = 6000.0


class QualityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    mypy_strict: bool = True
    min_coverage_pct: int = 80
    min_rubric_score: int = 60


class LensConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version_constraint: str = "^0.1"


class PathsConfig(BaseModel):
    """Where things live in the consumer repo.

    Both are paths **relative to the consumer repo root** (the directory
    containing `.grace/`). Stored as strings so the YAML is hand-editable
    without quoting quirks; resolved at command time.

    Defaults match the flat layout (no src/). For Lens-style src-layout
    repos, set `output_dir: src/lens/connectors`.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    docs_dir: str = "connector_docs"
    """Where `grace fetch-docs` writes + where `grace generate` reads
    when `--from` is omitted. The PSP-specific subdirectory is appended:
    `<repo>/<docs_dir>/<psp>/`."""

    output_dir: str = "lens/connectors"
    """Where `grace generate` writes when `--output` is omitted. The
    PSP-specific subdirectory is appended: `<repo>/<output_dir>/<psp>/`.
    For src-layout consumers, set this to `src/lens/connectors` so the
    generated package is importable as `lens.connectors.<psp>`."""


class GraceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    claude_code: ClaudeCodeConfig = Field(default_factory=ClaudeCodeConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    lens: LensConfig = Field(default_factory=LensConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)


@dataclass(frozen=True)
class LoadedConfig:
    """The validated config plus the source file(s) it came from. The CLI's
    `grace config show` surfaces both."""

    config: GraceConfig
    source: Path | None
    """The file the config was loaded from. None when only defaults are in
    effect (no per-project nor user-global config exists)."""


def _project_config_path() -> Path:
    return Path.cwd() / ".grace" / "config.yaml"


def _user_config_path() -> Path:
    return Path.home() / ".grace" / "config.yaml"


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        raw: Any = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise GraceError(reason=GraceErrorReason.CONFIG_INVALID, detail=str(e)) from e
    if not isinstance(raw, dict):
        raise GraceError(
            reason=GraceErrorReason.CONFIG_INVALID,
            detail=f"root must be a mapping in {path}",
        )
    return raw


def _validate(raw: dict[str, Any]) -> GraceConfig:
    try:
        return GraceConfig.model_validate(raw)
    except ValidationError as e:
        raise GraceError(reason=GraceErrorReason.CONFIG_INVALID, detail=str(e)) from e


def load_config(config_path: Path | None = None) -> GraceConfig:
    """Load config from (in order):

      1. The explicit `config_path` argument, if given.
      2. The per-project config at `<cwd>/.grace/config.yaml`, if it exists.
      3. The user-global config at `~/.grace/config.yaml`, if it exists.
      4. Built-in defaults.

    Returns the first-found, validated `GraceConfig`. No merging across
    layers — first hit wins as a whole — to keep behaviour predictable
    when both files exist.
    """
    return load_config_with_source(config_path).config


def load_config_with_source(config_path: Path | None = None) -> LoadedConfig:
    """Like `load_config` but also returns the file the config came from
    (or `None` if only defaults are in effect). Used by `grace config show`."""
    if config_path is not None:
        if not config_path.exists():
            return LoadedConfig(config=GraceConfig(), source=None)
        return LoadedConfig(config=_validate(_read_yaml(config_path)), source=config_path)
    for candidate in (_project_config_path(), _user_config_path()):
        if candidate.exists():
            return LoadedConfig(
                config=_validate(_read_yaml(candidate)), source=candidate
            )
    return LoadedConfig(config=GraceConfig(), source=None)


def set_config_value(key: str, value: str, *, target: Path | None = None) -> Path:
    """Update one dotted key in the project config file.

    `key` is dotted (e.g., `paths.output_dir`). `value` is a string and is
    YAML-encoded into the file as-is (no shell-style escaping). `target`
    defaults to `<cwd>/.grace/config.yaml` (the project-level config);
    pass an explicit Path to write elsewhere.

    Returns the path that was written.
    """
    target_path = target if target is not None else _project_config_path()
    if "." not in key:
        raise GraceError(
            reason=GraceErrorReason.CONFIG_INVALID,
            detail=f"config key must be dotted (e.g., paths.output_dir), got: {key!r}",
        )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    raw: dict[str, Any] = _read_yaml(target_path) if target_path.exists() else {}

    section, _, leaf = key.partition(".")
    if "." in leaf:
        raise GraceError(
            reason=GraceErrorReason.CONFIG_INVALID,
            detail=f"only single-level dotted keys supported (got: {key!r})",
        )
    raw.setdefault(section, {})
    if not isinstance(raw[section], dict):
        raise GraceError(
            reason=GraceErrorReason.CONFIG_INVALID,
            detail=f"existing {section!r} in {target_path} is not a mapping",
        )
    raw[section][leaf] = value

    # Round-trip through validation to refuse bad values before writing.
    _validate(raw)

    target_path.write_text(yaml.safe_dump(raw, default_flow_style=False, sort_keys=True))
    return target_path
