from __future__ import annotations

import asyncio
import importlib.metadata
import json
from pathlib import Path
from typing import Any

import click

from grace.config import load_config
from grace.errors import GraceError
from grace.fetch_docs import fetch_docs
from grace.pipeline import GenerationContext, PipelineHooks, run_pipeline
from grace.pipeline.context import assemble_context
from grace.pipeline.runner import ClaudeCodeRunner


def _grace_version() -> str:
    try:
        return importlib.metadata.version("grace-cli")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0+local"


def _repo_root() -> Path:
    # src/grace/cli.py → parents[0]=src/grace, parents[1]=src, parents[2]=repo root.
    return Path(__file__).resolve().parents[2]


def _last_run_path() -> Path:
    return Path.home() / ".grace" / "last_run.json"


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
    """`connector_docs/<psp>/` under the repo root."""
    return _repo_root() / "connector_docs" / psp


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
        asyncio.run(_run_pipeline(ctx=ctx, runner=runner, hooks=PipelineHooks(run_gates=True)))
        _save_last_run(psp=psp, source=source, output=out)
        click.echo(f"OK: wrote {out}")
    except GraceError as e:
        raise click.ClickException(f"{e.reason.value}: {e.detail or ''}") from e


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
        raise click.ClickException(f"{e.reason.value}: {e.detail or ''}") from e
    click.echo(
        f"OK: wrote {len(result.files_written)} files to {result.output_dir} "
        f"(skipped {result.skipped_count} by filter)"
    )


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
