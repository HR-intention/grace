from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from grace.pipeline.marker import ensure_marker
from grace.pipeline.types import GenerationContext, GenerationResult


class _RunnerProto(Protocol):
    async def is_available(self) -> tuple[bool, str]: ...
    async def generate(self, ctx: GenerationContext) -> GenerationResult: ...


@dataclass(frozen=True)
class PipelineHooks:
    run_gates: bool = True
    """Set False for tests that only exercise marker-ensure + orchestration."""


def relocated_tests_path(ctx: GenerationContext) -> Path | None:
    """Where the package's tests live after a (potential) relocation.

    Returns `<ctx.tests_dir>/<psp_name>/` when `ctx.tests_dir` is set,
    else None. Pure function over ctx — does not touch the filesystem.
    Useful for tests + for `run_gates_blocking` to know where to point
    pytest.
    """
    if ctx.tests_dir is None:
        return None
    return ctx.tests_dir / ctx.psp_name


def _relocate_tests(ctx: GenerationContext) -> Path | None:
    """If `ctx.tests_dir` is set, move `<output_dir>/tests/` to
    `<tests_dir>/<psp_name>/`. Returns the new tests root, or None if
    relocation wasn't configured / there were no tests to move.

    Overwrites an existing destination so `grace regenerate` is idempotent.
    """
    dest = relocated_tests_path(ctx)
    if dest is None:
        return None
    src = ctx.output_dir / "tests"
    if not src.is_dir():
        return None
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    return dest


async def run_pipeline(
    *,
    ctx: GenerationContext,
    runner: _RunnerProto,
    hooks: PipelineHooks = PipelineHooks(),
) -> GenerationResult:
    """Four-step pipeline: invoke → marker → relocate-tests → gates.

    Context assembly happens upstream of this function (callers use
    grace.pipeline.context.assemble_context). This function:
      1. Calls runner.generate(ctx).
      2. Post-processes any emitted .py file missing a marker.
      3. If ctx.tests_dir is set, relocates `<output_dir>/tests/` to
         `<tests_dir>/<psp>/` so generated tests live alongside the
         consumer's existing test suite rather than inside the package.
      4. (Optional) runs quality gates — implemented in pipeline/gates.py.
    """
    result = await runner.generate(ctx)

    from grace.pipeline.compose import write_compose_surface
    write_compose_surface(
        result.output_dir,
        psp_name=ctx.psp_name,
    )

    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    for p in result.output_dir.rglob("*.py"):
        ensure_marker(
            p,
            psp_name=ctx.psp_name,
            source_version=ctx.source_version,
            generated_utc_iso8601=generated_at,
            grace_version=ctx.grace_version,
            source_uri=ctx.psp_docs.source_uri,
        )

    _relocate_tests(ctx)

    if hooks.run_gates:
        from grace.pipeline.gates import run_gates_blocking

        run_gates_blocking(ctx=ctx, result=result)

    return result
