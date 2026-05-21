from __future__ import annotations

import asyncio
import importlib.metadata
import json
from pathlib import Path
from typing import Any

import click

from grace.config import load_config
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


def _default_docs_dir(psp: str) -> Path:
    """`connector_docs/<psp>/` under the **current working directory**.

    The expectation is that grace is invoked from inside the consumer repo
    (e.g. Lens), so docs snapshots get versioned alongside the package they
    produced — not inside Grace's own tree. Grace is a CLI tool the consumer
    depends on, never the other way around.
    """
    return Path.cwd() / "connector_docs" / psp


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
def generate(psp: str, source: str | None, output: Path | None, config: Path | None) -> None:
    """Generate a connector package for PSP from the given source."""
    cfg = load_config(config_path=config)

    if source is None:
        default = _default_docs_dir(psp)
        if not default.is_dir() or not any(default.iterdir()):
            raise click.ClickException(
                f"no --from and {default} is empty; run "
                f"`grace fetch-docs {psp} --from <llms.txt-url>` first"
            )
        source = str(default)

    out = output or (Path.cwd() / "lens" / "connectors" / psp)

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
        asyncio.run(_run_pipeline(ctx=ctx, runner=runner, hooks=PipelineHooks(run_gates=True)))
        click.echo("─" * 78)
        click.echo(f"OK: wrote {out}")

        # Auto-refresh the consumer-side docs catalog so llms.txt stays in sync
        # with every successful generation. Best-effort: a docs-build failure
        # shouldn't fail the generation.
        try:
            docs_result = build_docs(lens_root=Path.cwd())
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
    "--include",
    "include",
    multiple=True,
    help=(
        "Glob to keep (matched against URL path). Repeat for OR. "
        "Defaults are tuned for hosted-checkout PSPs (orders/payments/refunds/"
        "webhooks/auth/errors). Out-of-scope sections are excluded by default."
    ),
)
@click.option(
    "--exclude",
    "exclude",
    multiple=True,
    help="Glob to drop (matched against URL path). Repeat for OR.",
)
@click.option(
    "--output",
    "output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory. Defaults to <repo>/connector_docs/<psp>/.",
)
def fetch_docs_cmd(
    psp: str,
    source: str,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
    output: Path | None,
) -> None:
    """Fetch a PSP's docs from its llms.txt into connector_docs/<psp>/."""
    out = output or _default_docs_dir(psp)
    try:
        result = fetch_docs(
            psp_name=psp,
            source=source,
            output_dir=out,
            include=list(include) if include else None,
            exclude=list(exclude) if exclude else None,
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
    package under `<cwd>/lens/connectors/*/` and emits
    `<cwd>/docs-generated/llms.txt` plus one `.md` per connector. Idempotent.

    This is invoked automatically at the end of every successful `grace generate`,
    so most users won't need to run it directly.
    """
    try:
        result = build_docs(lens_root=Path.cwd())
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
