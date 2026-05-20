from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from grace.errors import GraceError, GraceErrorReason


class ClaudeCodeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    cli_path: Path | None = None
    timeout_s: float = 1800.0


class QualityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    mypy_strict: bool = True
    min_coverage_pct: int = 80
    min_rubric_score: int = 60


class LensConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version_constraint: str = "^0.1"


class GraceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    claude_code: ClaudeCodeConfig = Field(default_factory=ClaudeCodeConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    lens: LensConfig = Field(default_factory=LensConfig)


def load_config(config_path: Path | None = None) -> GraceConfig:
    """Load ~/.grace/config.yaml (or the path argument). Returns defaults if absent."""
    path = config_path if config_path is not None else Path.home() / ".grace" / "config.yaml"
    if not path.exists():
        return GraceConfig()
    try:
        raw: Any = yaml.safe_load(path.read_text()) or {}
        if not isinstance(raw, dict):
            raise GraceError(
                reason=GraceErrorReason.CONFIG_INVALID,
                detail=f"root must be a mapping in {path}",
            )
        return GraceConfig.model_validate(raw)
    except yaml.YAMLError as e:
        raise GraceError(reason=GraceErrorReason.CONFIG_INVALID, detail=str(e)) from e
    except ValidationError as e:
        raise GraceError(reason=GraceErrorReason.CONFIG_INVALID, detail=str(e)) from e
