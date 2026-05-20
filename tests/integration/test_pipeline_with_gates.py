from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import pytest

from grace.errors import GraceError, GraceErrorReason
from grace.pipeline import PipelineHooks, run_pipeline
from grace.pipeline.types import GenerationContext, GenerationResult, PspDocs


pytestmark = pytest.mark.integration


@dataclass
class _StubRunner:
    files: list[tuple[str, str]]

    async def is_available(self) -> tuple[bool, str]:
        return (True, "ok")

    async def generate(self, ctx: GenerationContext) -> GenerationResult:
        written: list[Path] = []
        for name, body in self.files:
            p = ctx.output_dir / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body)
            written.append(p)
        return GenerationResult(
            output_dir=ctx.output_dir,
            files_written=written,
            stdout="",
            stderr="",
            exit_code=0,
        )


def test_pipeline_raises_when_rubric_fails(tmp_path: Path) -> None:
    rb = tmp_path / "rb.md"
    rb.write_text("rb")
    ctx = GenerationContext(
        psp_name="demo",
        rulebook_paths=[rb],
        psp_docs=PspDocs(source_uri="x", source_kind="local_file", local_paths=[rb]),
        output_dir=tmp_path / "out",
        target_module="lens.connectors.demo",
        lens_version_constraint="^0.1",
        grace_version="0.1.0",
        source_version="x",
    )
    runner = _StubRunner(files=[])
    with pytest.raises(GraceError) as exc:
        asyncio.run(run_pipeline(ctx=ctx, runner=runner, hooks=PipelineHooks(run_gates=True)))
    assert exc.value.reason is GraceErrorReason.QUALITY_GATE_FAILED
