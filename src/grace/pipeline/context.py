from __future__ import annotations

from pathlib import Path

import httpx

from grace.errors import GraceError, GraceErrorReason
from grace.pipeline.types import GenerationContext, PspDocs


RULEBOOK_FILES = [
    "rulesbook/codegen/python/README.md",
    "rulesbook/codegen/python/ground_rules.md",
    "rulesbook/codegen/python/connector_abc.md",
    "rulesbook/codegen/python/domain_types.md",
    "rulesbook/codegen/python/file_layout.md",
    "rulesbook/codegen/python/status_mapping.md",
    "rulesbook/codegen/python/webhook_handling.md",
    "rulesbook/codegen/python/testing.md",
    "rulesbook/codegen/python/marker.md",
    "rulesbook/codegen/guides/patterns/pattern_createorder.md",
    "rulesbook/codegen/guides/patterns/pattern_psync.md",
    "rulesbook/codegen/guides/patterns/pattern_refund.md",
    "rulesbook/codegen/guides/patterns/pattern_rsync.md",
    "rulesbook/codegen/guides/patterns/pattern_IncomingWebhook_flow.md",
]


def default_rulebook_paths(*, repo_root: Path) -> list[Path]:
    """Return absolute paths to every rulebook file Claude Code should read."""
    paths: list[Path] = []
    for rel in RULEBOOK_FILES:
        p = (repo_root / rel).resolve()
        if not p.exists():
            raise GraceError(
                reason=GraceErrorReason.CONTEXT_BUNDLE_INVALID,
                detail=f"rulebook file missing: {p}",
            )
        paths.append(p)
    return paths


def resolve_source(source: str) -> PspDocs:
    """Resolve `source` into a PspDocs.

    Accepts: a URL (http/https), a local file path, or a local directory.
    """
    if source.startswith(("http://", "https://")):
        try:
            resp = httpx.get(source, timeout=30.0, follow_redirects=True)
        except httpx.HTTPError as e:
            raise GraceError(reason=GraceErrorReason.SOURCE_FETCH_FAILED, detail=str(e)) from e
        if resp.status_code >= 400:
            raise GraceError(
                reason=GraceErrorReason.SOURCE_FETCH_FAILED,
                detail=f"GET {source} -> HTTP {resp.status_code}",
            )
        return PspDocs(
            source_uri=source,
            source_kind="url",
            local_paths=[],
            content_bytes=resp.content,
        )

    p = Path(source).expanduser().resolve()
    if not p.exists():
        raise GraceError(
            reason=GraceErrorReason.SOURCE_FETCH_FAILED,
            detail=f"source not found: {p}",
        )
    if p.is_file():
        return PspDocs(source_uri=str(p), source_kind="local_file", local_paths=[p])
    return PspDocs(
        source_uri=str(p),
        source_kind="local_dir",
        local_paths=sorted(child.resolve() for child in p.iterdir() if child.is_file()),
    )


def assemble_context(
    *,
    psp_name: str,
    source: str,
    output_dir: Path,
    lens_version_constraint: str,
    grace_version: str,
    source_version: str,
    repo_root: Path,
) -> GenerationContext:
    """Build the full GenerationContext for a generate run."""
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return GenerationContext(
        psp_name=psp_name,
        rulebook_paths=default_rulebook_paths(repo_root=repo_root),
        psp_docs=resolve_source(source),
        output_dir=output_dir,
        target_module=f"lens.connectors.{psp_name}",
        lens_version_constraint=lens_version_constraint,
        grace_version=grace_version,
        source_version=source_version,
    )
