from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
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


async def run_pipeline(
    *,
    ctx: GenerationContext,
    runner: _RunnerProto,
    hooks: PipelineHooks = PipelineHooks(),
) -> GenerationResult:
    """Three-step pipeline: context → invoke → gates.

    Context assembly happens upstream of this function (callers use
    grace.pipeline.context.assemble_context). This function:
      1. Calls runner.generate(ctx).
      2. Post-processes any emitted .py file missing a marker.
      3. (Optional) runs quality gates — implemented in pipeline/gates.py.
    """
    result = await runner.generate(ctx)

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

    if hooks.run_gates:
        from grace.pipeline.gates import run_gates_blocking

        run_gates_blocking(ctx=ctx, result=result)

    return result
