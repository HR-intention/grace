"""Fetch PSP documentation from an llms.txt index into connector_docs/<psp>/.

llms.txt (https://llmstxt.org/) is a markdown file listing every doc page on a
site. Many PSP doc sites publish one. This module:

  1. Fetches the llms.txt (URL or local path).
  2. Extracts every markdown URL it lists.
  3. Filters by include-globs against the URL path.
  4. Fetches each filtered page and writes it as a numbered .md file into
     `connector_docs/<psp>/`.

The output directory is meant to be **committed to the repo** so generations are
reproducible against a pinned set of docs.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

from grace.errors import GraceError, GraceErrorReason


# Default include-globs applied when the caller doesn't provide --include.
# Tuned for hosted-checkout PSPs whose docs are under /api-reference/ (Cashfree)
# or /api/ (Razorpay-style). Restricting to API-reference paths keeps general
# guide pages out of the bundle. Out-of-scope sections are filtered separately
# by DEFAULT_EXCLUDE_GLOBS.
DEFAULT_INCLUDE_GLOBS: tuple[str, ...] = (
    "*api*orders*",
    "*api*payments*",
    "*api*refunds*",
    "*api*authentication*",
    "*api*overview*",
    "*api*enums*",
    "*api*errors*",
    "*webhook*",
)

# Exclude-globs override include — applied to strip out previous-version pages
# (most llms.txt files list both /latest/ and /previous/v.../ flavors).
DEFAULT_EXCLUDE_GLOBS: tuple[str, ...] = (
    # Previous-version docs.
    "*previous/*",
    "*v2022-*",
    "*v2023-*",
    "*v2024-*",
    # Out-of-scope per constitution §7 / FUTURE_S2S_INTERFACE.md.
    "*authorize*",
    "*/authenticate*",
    "*payments_pay*",
    "*/pay.md",
    "*preauth*",
    "*capture*",
    "*/void*",
    "*setup-mandate*",
    "*mandate*",
    "*payment-method-token*",
    "*session-token*",
    "*incremental*",
    "*repeat-payment*",
    "*subscriptionsv1*",
    "*subscription/*",
    "*payouts/*",
    "*dispute*",
    "*token-vault*",
    # Out-of-scope feature areas (constitution §7).
    "*split*",
    "*softpos*",
    "*pgvba*",
    "*international*",
    "*bbps*",
    "*oneescrow*",
    "*settlement*",
    "*simulation*",
    "*offers*",
    "*eligibility*",
    "*risk*",
    "*flowwise*",
    "*apple-pay*",
    "*customers*",
    "*payment-links*",
    "*platforms/*",
    "*merchant-onboarding*",
    "*prepaid-payment-instruments*",
    "*vrs*",
    "*bav-v2*",
    "*bulk*",
    "*incident*",
    "*utilit*",
    "*sdk*",
    "*rate-limits*",
    "*reconciliation*",
    "*best-practices*",
    "*data-to-test*",
    "*overview-ts*",
    "*-ts*",
)


# Pages every domain's connector needs (auth, identity, error shapes, webhook signing).
SHARED_INCLUDE_GLOBS: tuple[str, ...] = (
    "*api*authentication*", "*api*overview*", "*api*enums*", "*api*errors*",
    "*webhooks*signature*", "*webhooks*security*",
)
DOMAIN_INCLUDE_GLOBS: dict[str, tuple[str, ...]] = {
    "orders": ("*api*orders*", "*api*payments*", "*api*refunds*", "*payments*webhook*"),
    "subscriptions": (
        "*subscription/*", "*subscription/plans*", "*subscription/mandate*",
        "*subscription/payment*", "*subscription*webhook*",
    ),
}
# subscriptionsv1 (legacy, body-embedded sig) is never wanted.
LEGACY_EXCLUDE_GLOBS: tuple[str, ...] = ("*subscriptionsv1*", "*previous/*", "*v2022-*", "*v2023-*", "*v2024-*")


def _domain_includes(domain: str) -> tuple[str, ...]:
    if domain == "all":
        merged = set(SHARED_INCLUDE_GLOBS)
        for globs in DOMAIN_INCLUDE_GLOBS.values():
            merged.update(globs)
        return tuple(sorted(merged))
    if domain not in DOMAIN_INCLUDE_GLOBS:
        raise GraceError(reason=GraceErrorReason.SOURCE_FETCH_FAILED, detail=f"unknown domain {domain!r}")
    return SHARED_INCLUDE_GLOBS + DOMAIN_INCLUDE_GLOBS[domain]


def filter_urls_by_domain(urls: list[str], *, domain: str) -> list[str]:
    return filter_urls(urls, include=list(_domain_includes(domain)), exclude=list(LEGACY_EXCLUDE_GLOBS))


def bucket_for_url(url: str) -> str:
    path = _path_of(url)
    for dom, globs in DOMAIN_INCLUDE_GLOBS.items():
        if any(fnmatch.fnmatch(path, g) for g in globs):
            return dom
    return "_shared"


@dataclass(frozen=True)
class FetchDocsResult:
    psp_name: str
    source: str
    output_dir: Path
    files_written: list[Path]
    skipped_count: int


_MD_URL_RE = re.compile(r"https?://\S+?\.md\b")


def parse_llms_txt(content: str) -> list[str]:
    """Extract every markdown URL listed in an llms.txt body."""
    urls = _MD_URL_RE.findall(content)
    # Preserve order, de-dup.
    seen: set[str] = set()
    ordered: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered


def _path_of(url: str) -> str:
    return urlparse(url).path


def filter_urls(
    urls: list[str],
    *,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> list[str]:
    """Filter urls by glob lists matched against the URL path.

    Include defaults to DEFAULT_INCLUDE_GLOBS; exclude defaults to
    DEFAULT_EXCLUDE_GLOBS. Empty `include` (`[]`) means "match everything"
    (callers explicitly passing an empty list disable inclusion filtering);
    `None` triggers the default tuple.
    """
    if include is None:
        include = list(DEFAULT_INCLUDE_GLOBS)
    if exclude is None:
        exclude = list(DEFAULT_EXCLUDE_GLOBS)

    def included(path: str) -> bool:
        if not include:
            return True
        return any(fnmatch.fnmatch(path, g) for g in include)

    def excluded(path: str) -> bool:
        return any(fnmatch.fnmatch(path, g) for g in exclude)

    return [u for u in urls if included(_path_of(u)) and not excluded(_path_of(u))]


def derive_filename(url: str, idx: int) -> str:
    """Make a stable, sortable local filename from a URL.

    `idx` is the zero-based position in the filtered list; we prefix it to keep
    a deterministic reading order for Claude when it ingests the directory.
    """
    path = _path_of(url).strip("/")
    # Collapse path separators and strip the trailing `.md`.
    flat = path.replace("/", "_")
    if flat.endswith(".md"):
        flat = flat[:-3]
    # Cap component length for sane filenames.
    flat = flat[-80:] if len(flat) > 80 else flat
    return f"{idx:02d}_{flat}.md"


def fetch_docs(
    *,
    psp_name: str,
    source: str,
    output_dir: Path,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    client: httpx.Client | None = None,
) -> FetchDocsResult:
    """Fetch an llms.txt + its filtered markdown pages into `output_dir`.

    `source` is a URL or local file path pointing to an llms.txt. `output_dir`
    is created if needed; existing `.md` files inside are left untouched (the
    helper writes the filtered set, so re-running with the same args is
    idempotent at file level).

    If `client` is None, builds a default httpx.Client with a 30s timeout.
    """
    owns_client = client is None
    http = client or httpx.Client(timeout=30.0, follow_redirects=True)

    try:
        llms_txt_body = _read_source(http, source)
        all_urls = parse_llms_txt(llms_txt_body)
        if not all_urls:
            raise GraceError(
                reason=GraceErrorReason.SOURCE_FETCH_FAILED,
                detail=f"no markdown URLs found in {source}",
            )
        kept = filter_urls(all_urls, include=include, exclude=exclude)
        if not kept:
            raise GraceError(
                reason=GraceErrorReason.SOURCE_FETCH_FAILED,
                detail=(
                    f"include/exclude globs filtered out every URL "
                    f"(saw {len(all_urls)}); relax the filters"
                ),
            )

        output_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for idx, url in enumerate(kept):
            try:
                resp = http.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                raise GraceError(
                    reason=GraceErrorReason.SOURCE_FETCH_FAILED,
                    detail=f"GET {url}: {e}",
                ) from e
            fname = derive_filename(url, idx)
            target = output_dir / fname
            target.write_bytes(resp.content)
            written.append(target)
        return FetchDocsResult(
            psp_name=psp_name,
            source=source,
            output_dir=output_dir,
            files_written=written,
            skipped_count=len(all_urls) - len(kept),
        )
    finally:
        if owns_client:
            http.close()


def _read_source(client: httpx.Client, source: str) -> str:
    if source.startswith(("http://", "https://")):
        try:
            resp = client.get(source)
            resp.raise_for_status()
            return resp.text
        except httpx.HTTPError as e:
            raise GraceError(
                reason=GraceErrorReason.SOURCE_FETCH_FAILED,
                detail=f"GET {source}: {e}",
            ) from e
    p = Path(source).expanduser().resolve()
    if not p.is_file():
        raise GraceError(
            reason=GraceErrorReason.SOURCE_FETCH_FAILED,
            detail=f"not a readable llms.txt file: {p}",
        )
    return p.read_text()
