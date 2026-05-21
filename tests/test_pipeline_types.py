from __future__ import annotations

from pathlib import Path

from grace.pipeline.types import GenerationContext, GenerationResult, PspDocs


def test_psp_docs_local_file(tmp_path: Path) -> None:
    spec = tmp_path / "openapi.yaml"
    spec.write_text("openapi: 3.0.0")
    docs = PspDocs(
        source_uri=str(spec),
        source_kind="local_file",
        local_paths=[spec],
        content_bytes=None,
    )
    assert docs.source_kind == "local_file"
    assert docs.local_paths == [spec]


def test_generation_context_construction(tmp_path: Path) -> None:
    ctx = GenerationContext(
        psp_name="cashfree",
        rulebook_paths=[tmp_path / "rb1.md"],
        psp_docs=PspDocs(
            source_uri="x", source_kind="url", local_paths=[], content_bytes=b"x"
        ),
        output_dir=tmp_path / "out",
        target_module="lens.connectors.cashfree",
        lens_version_constraint="^0.1",
        grace_version="0.1.0",
        source_version="2024-09-01",
        reports_dir=tmp_path / "_reports",
    )
    assert ctx.psp_name == "cashfree"
    assert ctx.target_module == "lens.connectors.cashfree"


def test_generation_result_carries_paths(tmp_path: Path) -> None:
    r = GenerationResult(
        output_dir=tmp_path,
        files_written=[tmp_path / "connector.py"],
        stdout="ok",
        stderr="",
        exit_code=0,
    )
    assert r.exit_code == 0
    assert r.files_written[0].name == "connector.py"
