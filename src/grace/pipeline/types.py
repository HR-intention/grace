from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


SourceKind = Literal["url", "local_file", "local_dir"]


@dataclass(frozen=True)
class PspDocs:
    """A reference to the target PSP's API documentation, plus any cached content."""

    source_uri: str
    source_kind: SourceKind
    local_paths: list[Path] = field(default_factory=list)
    content_bytes: bytes | None = None


@dataclass(frozen=True)
class GenerationContext:
    """Everything the pipeline needs to invoke Claude Code."""

    psp_name: str
    rulebook_paths: list[Path]
    psp_docs: PspDocs
    output_dir: Path
    target_module: str
    lens_version_constraint: str
    grace_version: str
    source_version: str
    reports_dir: Path
    """Where quality_report.json and coverage.json land. Per-project +
    per-psp: `<cwd>/.grace/runs/<psp>/`. Kept OUT of the generated
    package directory so the reports don't end up committed alongside
    the source they describe."""

    tests_dir: Path | None = None
    """If set, the pipeline relocates `<output_dir>/tests/` to
    `<tests_dir>/<psp_name>/` after Claude writes them but before gates
    run. None keeps the canonical in-package layout. Resolved from
    `paths.tests_dir` in the consumer config — see `PathsConfig`."""


@dataclass(frozen=True)
class GenerationResult:
    """What the runner produces after Claude Code exits."""

    output_dir: Path
    files_written: list[Path]
    stdout: str
    stderr: str
    exit_code: int
    # Parsed from the final `result` JSONL event when --output-format
    # stream-json is in use. Useful for tracking iteration cost.
    cost_usd: float | None = None
    duration_ms: int | None = None
