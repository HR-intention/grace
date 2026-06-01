"""T11: verify that run_pipeline writes the compose surface *before* the
marker loop stamps it."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from grace.pipeline.orchestrate import PipelineHooks, run_pipeline
from grace.pipeline.marker import has_marker
from grace.pipeline.types import GenerationContext, GenerationResult, PspDocs


@dataclass
class _DomainStubRunner:
    """Writes a minimal domain-mixin layout under ctx.output_dir:
      orders/connector.py  (with a DemoOrders class)
      orders/webhooks.py   (with _parse_payment_webhook)
      core/auth.py         (minimal stub)
    """

    async def is_available(self) -> tuple[bool, str]:
        return (True, "ok")

    async def generate(self, ctx: GenerationContext) -> GenerationResult:
        written: list[Path] = []

        # orders/ domain
        orders_dir = ctx.output_dir / "orders"
        orders_dir.mkdir(parents=True, exist_ok=True)

        orders_connector = orders_dir / "connector.py"
        orders_connector.write_text(
            "class DemoOrders:\n"
            "    pass\n"
        )
        written.append(orders_connector)

        orders_webhooks = orders_dir / "webhooks.py"
        orders_webhooks.write_text(
            "def _parse_payment_webhook(raw):\n"
            "    pass\n"
        )
        written.append(orders_webhooks)

        # core/ directory
        core_dir = ctx.output_dir / "core"
        core_dir.mkdir(parents=True, exist_ok=True)

        core_auth = core_dir / "auth.py"
        core_auth.write_text(
            "def verify_signature(config, raw, headers):\n"
            "    pass\n"
        )
        written.append(core_auth)

        return GenerationResult(
            output_dir=ctx.output_dir,
            files_written=written,
            stdout="",
            stderr="",
            exit_code=0,
        )


def test_run_pipeline_emits_marked_compose_surface(tmp_path: Path) -> None:
    rb = tmp_path / "rb.md"
    rb.write_text("rb")

    ctx = GenerationContext(
        psp_name="demo",
        rulebook_paths=[rb],
        psp_docs=PspDocs(source_uri="x", source_kind="local_file", local_paths=[rb]),
        output_dir=tmp_path / "out",
        target_module="lens.connectors.demo",
        lens_version_constraint="^0.2",
        grace_version="0.1.0",
        source_version="2024-09-01",
        reports_dir=tmp_path / "_reports",
        domain="orders",
    )
    runner = _DomainStubRunner()
    asyncio.run(run_pipeline(ctx=ctx, runner=runner, hooks=PipelineHooks(run_gates=False)))

    # compose surface written
    assert (ctx.output_dir / "connector.py").is_file()
    assert "class DemoConnector(DemoOrders)" in (ctx.output_dir / "connector.py").read_text()
    # marker stamped by the existing ensure_marker loop
    assert has_marker(ctx.output_dir / "connector.py")
    assert has_marker(ctx.output_dir / "webhooks.py")
    assert (ctx.output_dir / "__init__.py").is_file()
