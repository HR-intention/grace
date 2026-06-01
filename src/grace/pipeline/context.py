from __future__ import annotations

from pathlib import Path

import httpx

from grace.errors import GraceError, GraceErrorReason
from grace.pipeline.types import GenerationContext, PspDocs


# ---------------------------------------------------------------------------
# Rulebook constants
# ---------------------------------------------------------------------------

CORE_RULEBOOK_FILES = [
    "rulesbook/codegen/python/README.md",
    "rulesbook/codegen/python/pitfalls.md",
    "rulesbook/codegen/python/ground_rules.md",
    "rulesbook/codegen/python/connector_abc.md",
    "rulesbook/codegen/python/domain_types.md",
    "rulesbook/codegen/python/file_layout.md",
    "rulesbook/codegen/python/status_mapping.md",
    "rulesbook/codegen/python/webhook_handling.md",
    "rulesbook/codegen/python/testing.md",
    "rulesbook/codegen/python/marker.md",
    # Shared / cross-domain pattern
    "rulesbook/codegen/guides/patterns/pattern_IncomingWebhook_flow.md",
]

DOMAIN_PATTERN_FILES: dict[str, list[str]] = {
    "orders": [
        "rulesbook/codegen/guides/patterns/pattern_createorder.md",
        "rulesbook/codegen/guides/patterns/pattern_psync.md",
        "rulesbook/codegen/guides/patterns/pattern_refund.md",
        "rulesbook/codegen/guides/patterns/pattern_rsync.md",
    ],
    "subscriptions": [
        "rulesbook/codegen/guides/patterns/pattern_create_subscription.md",
        "rulesbook/codegen/guides/patterns/pattern_sync_subscription.md",
        "rulesbook/codegen/guides/patterns/pattern_manage_mandate.md",
        "rulesbook/codegen/guides/patterns/pattern_mandate_webhook.md",
    ],
}

# Kept for backward-compat in case any existing code imports RULEBOOK_FILES directly.
RULEBOOK_FILES = CORE_RULEBOOK_FILES + DOMAIN_PATTERN_FILES["orders"] + DOMAIN_PATTERN_FILES["subscriptions"]

# ---------------------------------------------------------------------------
# Domain-keyed helpers
# ---------------------------------------------------------------------------

_DOMAIN_FOLDER_MAP: dict[str, list[str]] = {
    "orders": ["orders"],
    "subscriptions": ["subscriptions"],
    "all": ["orders", "subscriptions"],
}


def rulebook_files_for_domain(domain: str) -> list[str]:
    """Return the relative rulebook file list for *domain*.

    ``domain`` is one of ``"orders"``, ``"subscriptions"``, or ``"all"``.
    Core files and the shared webhook pattern are always included.
    Per-flow patterns are gated by domain.
    """
    files: list[str] = list(CORE_RULEBOOK_FILES)
    if domain in ("orders", "all"):
        files.extend(DOMAIN_PATTERN_FILES["orders"])
    if domain in ("subscriptions", "all"):
        files.extend(DOMAIN_PATTERN_FILES["subscriptions"])
    return files


def default_rulebook_paths(*, repo_root: Path, domain: str = "all") -> list[Path]:
    """Return absolute paths to every rulebook file Claude Code should read."""
    paths: list[Path] = []
    for rel in rulebook_files_for_domain(domain):
        p = (repo_root / rel).resolve()
        if not p.exists():
            raise GraceError(
                reason=GraceErrorReason.CONTEXT_BUNDLE_INVALID,
                detail=f"rulebook file missing: {p}",
            )
        paths.append(p)
    return paths


# ---------------------------------------------------------------------------
# Source / doc-bundle resolution
# ---------------------------------------------------------------------------

_DOMAIN_SUBFOLDERS = {"_shared", "orders", "subscriptions"}


def _is_grouped_layout(p: Path) -> bool:
    """Return True when *p* is a directory using the grouped layout.

    A grouped layout has at least one of the known domain sub-directories
    (``_shared``, ``orders``, or ``subscriptions``) directly inside it.
    """
    return p.is_dir() and any((p / sub).is_dir() for sub in _DOMAIN_SUBFOLDERS)


def _resolve_grouped_docs(p: Path, psp_name: str, domain: str) -> PspDocs:
    """Build a domain-scoped PspDocs from a grouped-layout directory."""
    active_folders: list[str] = ["_shared"] + _DOMAIN_FOLDER_MAP.get(domain, ["orders", "subscriptions"])
    local_paths: list[Path] = []
    for folder in active_folders:
        folder_path = p / folder
        if folder_path.is_dir():
            local_paths.extend(sorted(child.resolve() for child in folder_path.rglob("*") if child.is_file()))

    # Sibling spec: connector_docs/<psp_name>.md next to connector_docs/<psp_name>/
    sibling_spec = (p.parent / f"{psp_name}.md").resolve()
    if sibling_spec.exists():
        local_paths.append(sibling_spec)

    return PspDocs(
        source_uri=str(p),
        source_kind="local_dir",
        local_paths=local_paths,
    )


def resolve_source(source: str) -> PspDocs:
    """Resolve `source` into a PspDocs.

    Accepts: a URL (http/https), a local file path, or a local directory.
    For domain-aware resolution from a grouped layout, use
    ``resolve_source_for_domain`` instead.
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


def resolve_source_for_domain(source: str, *, psp_name: str, domain: str) -> PspDocs:
    """Resolve *source* with domain-aware doc bundling.

    - URL / single file: identical to ``resolve_source``.
    - Local directory with grouped layout (has ``_shared/``, ``orders/``,
      or ``subscriptions/`` sub-dirs): applies domain scoping.
    - Flat local directory (no domain sub-dirs): falls back to the original
      behaviour (all direct-child files).
    """
    if source.startswith(("http://", "https://")):
        return resolve_source(source)

    p = Path(source).expanduser().resolve()
    if not p.exists():
        raise GraceError(
            reason=GraceErrorReason.SOURCE_FETCH_FAILED,
            detail=f"source not found: {p}",
        )
    if p.is_file():
        return PspDocs(source_uri=str(p), source_kind="local_file", local_paths=[p])

    if _is_grouped_layout(p):
        return _resolve_grouped_docs(p, psp_name=psp_name, domain=domain)

    # Flat layout fallback — keep existing behaviour.
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
    tests_dir: Path | None = None,
    domain: str = "all",
) -> GenerationContext:
    """Build the full GenerationContext for a generate run.

    `tests_dir`, when provided, is the absolute parent directory under which
    the generated `tests/` subtree gets relocated (to `<tests_dir>/<psp>/`)
    after Claude writes it. None keeps the in-package layout.
    """
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = (Path.cwd() / ".grace" / "runs" / psp_name).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)
    resolved_tests_dir = tests_dir.expanduser().resolve() if tests_dir is not None else None
    return GenerationContext(
        psp_name=psp_name,
        rulebook_paths=default_rulebook_paths(repo_root=repo_root, domain=domain),
        psp_docs=resolve_source_for_domain(source, psp_name=psp_name, domain=domain),
        output_dir=output_dir,
        target_module=f"lens.connectors.{psp_name}",
        lens_version_constraint=lens_version_constraint,
        grace_version=grace_version,
        source_version=source_version,
        reports_dir=reports_dir,
        tests_dir=resolved_tests_dir,
        domain=domain,
    )
