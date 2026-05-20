"""Install Grace's bundled Claude Code Skills templates into a consumer's `.skills/`.

Mirrors juspay-prism's `.skills/` pattern. Each skill is a directory with a
top-level `SKILL.md` (Anthropic Skills v1 frontmatter) plus a `references/`
subtree. Shared references live under `_shared/references/` and skills can
symlink to them (the same way upstream does), but for v1 we just copy.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from grace.errors import GraceError, GraceErrorReason


def _templates_root() -> Path:
    """Root of the bundled skills templates inside the Grace package."""
    return Path(__file__).parent / "skills_templates"


def list_skills() -> list[str]:
    """Names of every skill the bundle ships (excluding `_shared`)."""
    root = _templates_root()
    if not root.is_dir():
        return []
    return sorted(
        p.name
        for p in root.iterdir()
        if p.is_dir() and not p.name.startswith(("_", "."))
    )


@dataclass(frozen=True)
class InstallResult:
    install_root: Path                  # the .skills/ dir written to
    skills_installed: list[str]
    files_written: int


def install_skills(*, target_root: Path, force: bool = False) -> InstallResult:
    """Copy the bundled skills + `_shared/` references into `<target_root>/.skills/`.

    If `force` is False and the target `.skills/` already exists with content,
    raises. Pass `force=True` to overwrite (per-skill granular: existing skills
    are replaced atomically by moving the old one aside, copying in the new one).
    """
    src_root = _templates_root()
    if not src_root.is_dir():
        raise GraceError(
            reason=GraceErrorReason.CONTEXT_BUNDLE_INVALID,
            detail=f"skills templates missing at {src_root}",
        )

    skills_dir = target_root / ".skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    installed: list[str] = []
    files_written = 0

    # Copy `_shared/` first so per-skill refs that reference it are valid.
    shared_src = src_root / "_shared"
    if shared_src.is_dir():
        shared_dst = skills_dir / "_shared"
        if shared_dst.exists():
            if not force:
                raise GraceError(
                    reason=GraceErrorReason.CONTEXT_BUNDLE_INVALID,
                    detail=(
                        f"{shared_dst} already exists. Re-run with --force to overwrite, "
                        f"or remove it first."
                    ),
                )
            shutil.rmtree(shared_dst)
        shutil.copytree(shared_src, shared_dst)
        files_written += sum(1 for _ in shared_dst.rglob("*") if _.is_file())

    # Copy each skill dir.
    for skill_name in list_skills():
        skill_src = src_root / skill_name
        skill_dst = skills_dir / skill_name
        if skill_dst.exists():
            if not force:
                raise GraceError(
                    reason=GraceErrorReason.CONTEXT_BUNDLE_INVALID,
                    detail=(
                        f"{skill_dst} already exists. Re-run with --force to overwrite, "
                        f"or remove it first."
                    ),
                )
            shutil.rmtree(skill_dst)
        shutil.copytree(skill_src, skill_dst)
        installed.append(skill_name)
        files_written += sum(1 for _ in skill_dst.rglob("*") if _.is_file())

    return InstallResult(
        install_root=skills_dir,
        skills_installed=installed,
        files_written=files_written,
    )
