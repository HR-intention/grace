from __future__ import annotations

import asyncio
import importlib.metadata
import json
from pathlib import Path
from typing import Any

import click

from grace.config import (
    GraceConfig,
    load_config,
    load_config_with_source,
    set_config_value,
)
from grace.docs_build import build_docs
from grace.errors import GraceError, GraceErrorReason
from grace.fetch_docs import fetch_docs
from grace.pipeline import GenerationContext, PipelineHooks, run_pipeline
from grace.pipeline.context import assemble_context
from grace.pipeline.runner import ClaudeCodeRunner
from grace.skills_install import install_skills, list_skills


# Per-reason actionable hints surfaced to the user when a GraceError bubbles up
# through the CLI. Detail (the underlying stderr/stdout from the failing
# subprocess) is preserved alongside the hint.
_ERROR_HINTS: dict[GraceErrorReason, str] = {
    GraceErrorReason.CLAUDE_CODE_NOT_AUTHENTICATED: (
        "claude -p got a 401 from the Anthropic API.\n"
        "  For Pro/Max subscribers (no API key needed):\n"
        "    claude setup-token\n"
        '    export CLAUDE_CODE_OAUTH_TOKEN="<paste-the-token>"\n'
        "  Then verify with: echo hi | claude -p\n"
        "  See README \"Troubleshooting\" or anthropics/claude-code#28827."
    ),
    GraceErrorReason.CLAUDE_CODE_NOT_FOUND: (
        "Install Claude Code first (https://docs.claude.com/claude-code),\n"
        "  then `claude /login` (or `claude setup-token`)."
    ),
    GraceErrorReason.CLAUDE_CODE_TIMEOUT: (
        "Generation timed out. Bump the timeout in ~/.grace/config.yaml:\n"
        "    claude_code:\n"
        "      timeout_s: 9000   # raise from the default 6000s\n"
        "  Then retry."
    ),
    GraceErrorReason.CLAUDE_CODE_FAILED: (
        "claude -p exited non-zero for a non-auth reason. Inspect the detail above.\n"
        "  Try `echo hi | claude -p` to confirm the CLI itself works."
    ),
    GraceErrorReason.CONTEXT_BUNDLE_INVALID: (
        "Rulebook file missing. Are you running grace from inside the Grace repo?\n"
        "  cd into the Grace fork and retry; grace resolves rulebook paths relative\n"
        "  to its own source tree."
    ),
    GraceErrorReason.QUALITY_GATE_FAILED: (
        "Generated package failed quality gates. Open\n"
        "    <output>/quality_report.json\n"
        "  for the per-dimension breakdown, then sharpen the rulebook page that maps\n"
        "  to the missing dimension and `grace regenerate <psp>`. Do NOT hand-edit\n"
        "  generated files (constitution §4)."
    ),
    GraceErrorReason.SOURCE_FETCH_FAILED: (
        "Could not load the docs source. Check the URL / file path / network and retry."
    ),
    GraceErrorReason.CONFIG_INVALID: (
        "~/.grace/config.yaml is malformed. The detail above points at the offending key."
    ),
}


def _click_error_from_grace(e: GraceError) -> click.ClickException:
    """Translate a GraceError into a ClickException with an actionable hint."""
    hint = _ERROR_HINTS.get(e.reason, "")
    detail = (e.detail or "").strip()
    pieces: list[str] = [e.reason.value]
    if detail:
        pieces.append(detail)
    if hint:
        pieces.append("")
        pieces.append(hint)
    return click.ClickException("\n".join(pieces))


def _grace_version() -> str:
    try:
        return importlib.metadata.version("grace-cli")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0+local"


def _repo_root() -> Path:
    # src/grace/cli.py → parents[0]=src/grace, parents[1]=src, parents[2]=repo root.
    return Path(__file__).resolve().parents[2]


def _last_run_path() -> Path:
    """Per-project last-run record.

    Lives at `<cwd>/.grace/last_run.json` (i.e., in whichever consumer
    repo grace was invoked from), so two Lens-like checkouts iterating
    on Grace simultaneously don't clobber each other's state. Add
    `.grace/` to the consumer's `.gitignore`.

    Was previously `~/.grace/last_run.json` (user-global); migration:
    the next `grace generate` writes a fresh per-project record; the
    old global file becomes vestigial and can be deleted.
    """
    return Path.cwd() / ".grace" / "last_run.json"


def _save_last_run(*, psp: str, source: str, output: Path) -> None:
    p = _last_run_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"psp": psp, "source": source, "output": str(output)}))


def _load_last_run(psp: str) -> dict[str, str]:
    p = _last_run_path()
    if not p.exists():
        raise click.ClickException("no previous run on record (run `grace generate` first)")
    data: Any = json.loads(p.read_text())
    if not isinstance(data, dict) or data.get("psp") != psp:
        raise click.ClickException(f"no previous run for {psp}")
    return {str(k): str(v) for k, v in data.items()}


async def _run_pipeline(
    *, ctx: GenerationContext, runner: ClaudeCodeRunner, hooks: PipelineHooks
) -> None:
    await run_pipeline(ctx=ctx, runner=runner, hooks=hooks)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=_grace_version(), prog_name="grace")
def main() -> None:
    """Grace — generate Python PSP connectors for the Orbit Lens."""


@main.command()
def doctor() -> None:
    """Check whether Claude Code is reachable."""
    cfg = load_config()
    runner = ClaudeCodeRunner(
        cli_path=cfg.claude_code.cli_path, timeout_s=cfg.claude_code.timeout_s
    )
    healthy, detail = asyncio.run(runner.is_available())
    if healthy:
        click.echo(f"healthy: {detail}")
        raise SystemExit(0)
    click.echo(f"unhealthy: {detail}")
    raise SystemExit(1)


def _log_report_paths(reports_dir: Path) -> None:
    """Print the locations of quality_report.json + coverage.json with a
    short tip on the most useful jq invocations. Called from the `finally`
    branch of `generate` so it fires on both success and failure paths.

    When quality_report.json contains a non-empty ``by_domain`` map, also
    prints a compact per-domain summary table:

        Per-domain:
          domain         mypy   tests_failed   coverage
          orders           21             11      75.3%
          subscriptions     8              0      85.6%
    """
    quality = reports_dir / "quality_report.json"
    coverage = reports_dir / "coverage.json"
    click.echo()
    click.echo("Reports:")
    if quality.is_file():
        click.echo(f"  quality:   {quality}")
    if coverage.is_file():
        click.echo(f"  coverage:  {coverage}")
    if quality.is_file():
        click.echo(
            "  inspect:   "
            f"cat {quality} | python -m json.tool"
        )
        # Print per-domain breakdown table when present.
        try:
            report_data: Any = json.loads(quality.read_text())
            by_domain: Any = report_data.get("by_domain") if isinstance(report_data, dict) else None
            if isinstance(by_domain, dict) and by_domain:
                click.echo()
                click.echo("Per-domain:")
                header = f"  {'domain':<16} {'mypy':>6}   {'tests_failed':>12}   {'coverage':>8}"
                click.echo(header)
                for domain, metrics in sorted(by_domain.items()):
                    if not isinstance(metrics, dict):
                        continue
                    mypy_errors = int(metrics.get("mypy_errors", 0))
                    tests_failed = int(metrics.get("tests_failed", 0))
                    coverage_pct = float(metrics.get("coverage_pct", 0.0))
                    cov_str = f"{coverage_pct:.1f}%"
                    click.echo(
                        f"  {domain:<16} {mypy_errors:>6}   {tests_failed:>12}   {cov_str:>8}"
                    )
        except (ValueError, OSError, KeyError):
            pass


def _default_docs_dir(psp: str, cfg: "GraceConfig | None" = None) -> Path:
    """`<docs_dir>/<psp>/` under the **current working directory**.

    `docs_dir` is read from `<cwd>/.grace/config.yaml` if configured
    (`paths.docs_dir`), defaulting to `connector_docs`. The expectation is
    that grace is invoked from inside the consumer repo (e.g. Lens), so
    docs snapshots get versioned alongside the package they produced —
    not inside Grace's own tree.
    """
    cfg = cfg if cfg is not None else load_config()
    return Path.cwd() / cfg.paths.docs_dir / psp


def _default_output_dir(psp: str, cfg: "GraceConfig | None" = None) -> Path:
    """`<output_dir>/<psp>/` under the **current working directory**.

    `output_dir` is read from `<cwd>/.grace/config.yaml` (`paths.output_dir`),
    defaulting to `lens/connectors`. For src-layout consumers (Lens uses
    `src/lens/`), set this to `src/lens/connectors` so the generated package
    is importable as `lens.connectors.<psp>`.
    """
    cfg = cfg if cfg is not None else load_config()
    return Path.cwd() / cfg.paths.output_dir / psp


def _resolved_tests_dir(cfg: "GraceConfig | None" = None) -> Path | None:
    """`<cwd>/<paths.tests_dir>` if configured, else None.

    The pipeline uses this to relocate the generated `tests/` subtree
    from `<output_dir>/<psp>/tests/` to `<tests_dir>/<psp>/` so connector
    tests can live alongside the consumer's existing test suite (e.g.,
    Lens has `tests/` at repo root).
    """
    cfg = cfg if cfg is not None else load_config()
    if cfg.paths.tests_dir is None:
        return None
    return Path.cwd() / cfg.paths.tests_dir


@main.command()
@click.argument("psp")
@click.option(
    "--from",
    "source",
    default=None,
    help=(
        "URL, local file, or local directory of PSP docs. "
        "Defaults to <repo>/connector_docs/<psp>/ (populated by `grace fetch-docs`)."
    ),
)
@click.option(
    "--output",
    "output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory. Defaults to ./lens/connectors/<psp>/.",
)
@click.option(
    "--config",
    "config",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to grace config.yaml; defaults to ~/.grace/config.yaml.",
)
@click.option(
    "--domain",
    "domain",
    type=click.Choice(["orders", "subscriptions", "all"]),
    default="all",
    help="Which capability domain to (re)generate.",
)
def generate(psp: str, source: str | None, output: Path | None, config: Path | None, domain: str) -> None:
    """Generate a connector package for PSP from the given source."""
    cfg = load_config(config_path=config)

    if source is None:
        default = _default_docs_dir(psp, cfg)
        if not default.is_dir() or not any(default.iterdir()):
            raise click.ClickException(
                f"no --from and {default} is empty; run "
                f"`grace fetch-docs {psp} --from <llms.txt-url>` first "
                f"(or `grace config set paths.docs_dir <new-path>` to point elsewhere)"
            )
        source = str(default)

    out = output or _default_output_dir(psp, cfg)
    tests_dir = _resolved_tests_dir(cfg)

    # Log resolved paths so the user always sees what's about to be read /
    # written. Avoids the "wait, where did the files go?" surprise.
    click.echo(f"→ Source: {source}")
    click.echo(f"→ Output: {out}")
    if tests_dir is not None:
        click.echo(f"→ Tests:  {tests_dir / psp}  (relocated from {out}/tests/)")
    click.echo(f"→ Lens version constraint: {cfg.lens.version_constraint}")
    click.echo()

    # Persist the invocation args BEFORE running the pipeline so `grace
    # regenerate <psp>` can replay them even when the pipeline raises
    # (typically QUALITY_GATE_FAILED during rulebook iteration). The whole
    # point of `regenerate` is to retry after a failed run; saving only on
    # success defeated that.
    _save_last_run(psp=psp, source=source, output=out)

    try:
        ctx = assemble_context(
            psp_name=psp,
            source=source,
            output_dir=out,
            lens_version_constraint=cfg.lens.version_constraint,
            grace_version=_grace_version(),
            source_version=source,
            repo_root=_repo_root(),
            tests_dir=tests_dir,
            domain=domain,
        )
        runner = ClaudeCodeRunner(
            cli_path=cfg.claude_code.cli_path, timeout_s=cfg.claude_code.timeout_s
        )
        click.echo(
            f"→ Spawning claude -p for {psp} (this can take several minutes; "
            f"timeout = {int(cfg.claude_code.timeout_s)}s). "
            f"Output streams below; quality gates run after exit."
        )
        click.echo("─" * 78)
        try:
            asyncio.run(_run_pipeline(ctx=ctx, runner=runner, hooks=PipelineHooks(run_gates=True)))
            click.echo("─" * 78)
            click.echo(f"OK: wrote {out}")
        finally:
            # Report paths are always interesting — on success the user wants
            # to inspect quality_report.json; on failure they want the findings
            # list and the coverage breakdown. Print them either way.
            _log_report_paths(ctx.reports_dir)

        # Auto-refresh the consumer-side docs catalog so llms.txt stays in sync
        # with every successful generation. Best-effort: a docs-build failure
        # shouldn't fail the generation. The consumer's paths.output_dir tells
        # us where the connector packages actually live (e.g. src/lens/connectors
        # for src-layout Lens, not the default lens/connectors).
        try:
            docs_result = build_docs(
                lens_root=Path.cwd(),
                connectors_subpath=cfg.paths.output_dir,
            )
            click.echo(
                f"OK: refreshed {docs_result.output_root.relative_to(Path.cwd())} "
                f"({len(docs_result.connectors)} connectors)"
            )
        except GraceError as e:
            click.echo(f"warning: docs refresh skipped — {e.reason.value}: {e.detail}", err=True)
    except GraceError as e:
        raise _click_error_from_grace(e) from e


@main.command(name="fetch-docs")
@click.argument("psp")
@click.option(
    "--from",
    "source",
    required=True,
    help="URL or local path of an llms.txt file listing the PSP's doc pages.",
)
@click.option(
    "--domain",
    "domain",
    type=click.Choice(["orders", "subscriptions", "all"]),
    default="all",
    help=(
        "Which capability domain's docs to fetch. "
        "Selects the appropriate URL globs for orders, subscriptions, or both. "
        "Bypassed when --include/--exclude are provided as manual overrides."
    ),
)
@click.option(
    "--include",
    "include",
    multiple=True,
    help=(
        "Glob to keep (matched against URL path). Repeat for OR. "
        "Bypasses the --domain preset when provided."
    ),
)
@click.option(
    "--exclude",
    "exclude",
    multiple=True,
    help=(
        "Glob to drop (matched against URL path). Repeat for OR. "
        "Bypasses the --domain preset when provided."
    ),
)
@click.option(
    "--output",
    "output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory. Defaults to <repo>/<paths.docs_dir>/<psp>/ "
    "(set via `grace config set paths.docs_dir <path>`).",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite an existing connector_docs/<psp>.md scaffold.",
)
def fetch_docs_cmd(
    psp: str,
    source: str,
    domain: str,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
    output: Path | None,
    force: bool,
) -> None:
    """Fetch a PSP's docs from its llms.txt into connector_docs/<psp>/."""
    cfg = load_config()
    out = output or _default_docs_dir(psp, cfg)
    click.echo(f"→ From: {source}")
    click.echo(f"→ Into: {out}")
    click.echo()
    try:
        result = fetch_docs(
            psp_name=psp,
            source=source,
            output_dir=out,
            domain=domain,
            include=list(include) if include else None,
            exclude=list(exclude) if exclude else None,
            force=force,
        )
    except GraceError as e:
        raise _click_error_from_grace(e) from e
    click.echo(
        f"OK: wrote {len(result.files_written)} files to {result.output_dir} "
        f"(skipped {result.skipped_count} by filter)"
    )


@main.command()
def docs() -> None:
    """Build the consumer-side docs catalog (docs-generated/llms.txt + per-connector .md).

    Run from inside the consumer repo (e.g. Lens). Static-analyzes every
    connector package under `<cwd>/<paths.output_dir>/*/` and emits
    `<cwd>/docs-generated/llms.txt` plus one `.md` per connector. Idempotent.

    This is invoked automatically at the end of every successful `grace generate`,
    so most users won't need to run it directly.
    """
    cfg = load_config()
    try:
        result = build_docs(
            lens_root=Path.cwd(),
            connectors_subpath=cfg.paths.output_dir,
        )
    except GraceError as e:
        raise _click_error_from_grace(e) from e
    click.echo(
        f"OK: wrote {len(result.files_written)} files under "
        f"{result.output_root} ({len(result.connectors)} connectors discovered)"
    )


@main.group(name="skills")
def skills_group() -> None:
    """Manage the bundled Claude Code Skills pack for the consumer repo."""


@skills_group.command(name="list")
def skills_list_cmd() -> None:
    """List every skill Grace ships."""
    names = list_skills()
    if not names:
        click.echo("(no skills bundled)")
        return
    for n in names:
        click.echo(n)


@skills_group.command(name="install")
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite any existing skill directories at the target.",
)
@click.option(
    "--output",
    "output",
    type=click.Path(path_type=Path),
    default=None,
    help="Target repo root. Defaults to current working directory.",
)
def skills_install_cmd(force: bool, output: Path | None) -> None:
    """Copy bundled skills templates into <cwd>/.skills/ (or --output)."""
    target = (output or Path.cwd()).resolve()
    try:
        result = install_skills(target_root=target, force=force)
    except GraceError as e:
        raise _click_error_from_grace(e) from e
    click.echo(
        f"OK: installed {len(result.skills_installed)} skill(s) "
        f"({result.files_written} files) into {result.install_root}"
    )
    for s in result.skills_installed:
        click.echo(f"  - {s}")


@main.group(name="config")
def config_group() -> None:
    """Inspect and edit grace's per-project config at <cwd>/.grace/config.yaml."""


@config_group.command(name="show")
def config_show_cmd() -> None:
    """Print the effective config + the file it was loaded from."""
    loaded = load_config_with_source()
    src = loaded.source if loaded.source is not None else "(defaults — no config file found)"
    click.echo(f"Source: {src}")
    click.echo()
    click.echo("Effective config:")
    click.echo("  paths:")
    click.echo(f"    docs_dir:    {loaded.config.paths.docs_dir}")
    click.echo(f"    output_dir:  {loaded.config.paths.output_dir}")
    click.echo(f"    tests_dir:   {loaded.config.paths.tests_dir or '(unset — tests stay in package)'}")
    click.echo("  claude_code:")
    click.echo(f"    cli_path:    {loaded.config.claude_code.cli_path or '(auto-detect)'}")
    click.echo(f"    timeout_s:   {int(loaded.config.claude_code.timeout_s)}")
    click.echo("  quality:")
    click.echo(f"    mypy_strict:        {loaded.config.quality.mypy_strict}")
    click.echo(f"    min_coverage_pct:   {loaded.config.quality.min_coverage_pct}")
    click.echo(f"    min_rubric_score:   {loaded.config.quality.min_rubric_score}")
    click.echo("  lens:")
    click.echo(f"    version_constraint: {loaded.config.lens.version_constraint}")
    click.echo()
    docs_psp = _default_docs_dir("<psp>", loaded.config)
    out_psp = _default_output_dir("<psp>", loaded.config)
    tests_root = _resolved_tests_dir(loaded.config)
    click.echo("Resolved at <cwd>:")
    click.echo(f"  docs:    {docs_psp}")
    click.echo(f"  output:  {out_psp}")
    if tests_root is not None:
        click.echo(f"  tests:   {tests_root / '<psp>'}")


@config_group.command(name="set")
@click.argument("key")
@click.argument("value")
def config_set_cmd(key: str, value: str) -> None:
    """Set a config value. KEY is dotted (e.g., `paths.output_dir`).

    Writes to `<cwd>/.grace/config.yaml`, creating it if needed. Refuses
    invalid values (validated against the same Pydantic schema as on-load).

    Examples:

      grace config set paths.output_dir src/lens/connectors
      grace config set paths.docs_dir   connector_docs
      grace config set paths.tests_dir  tests/connectors
      grace config set claude_code.timeout_s 9000
    """
    try:
        written = set_config_value(key, value)
    except GraceError as e:
        raise _click_error_from_grace(e) from e
    click.echo(f"OK: {key} = {value!r} → {written}")


@config_group.command(name="get")
@click.argument("key")
def config_get_cmd(key: str) -> None:
    """Print the current value for a dotted config key."""
    if "." not in key:
        raise click.ClickException(
            f"key must be dotted (e.g., paths.output_dir), got: {key!r}"
        )
    section, _, leaf = key.partition(".")
    cfg = load_config()
    section_obj = getattr(cfg, section, None)
    if section_obj is None:
        raise click.ClickException(f"unknown section: {section!r}")
    if not hasattr(section_obj, leaf):
        raise click.ClickException(f"unknown key: {key!r}")
    click.echo(getattr(section_obj, leaf))


@main.command()
@click.argument("psp")
def regenerate(psp: str) -> None:
    """Re-run the previous `generate` invocation for PSP with the same args."""
    last = _load_last_run(psp)
    ctx = click.get_current_context()
    ctx.invoke(
        generate,
        psp=psp,
        source=last["source"],
        output=Path(last["output"]),
        config=None,
    )
