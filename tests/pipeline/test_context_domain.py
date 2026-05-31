from __future__ import annotations

from pathlib import Path
from grace.pipeline.context import assemble_context

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_assemble_context_carries_domain(tmp_path: Path) -> None:
    repo = REPO_ROOT
    docs = tmp_path / "connector_docs" / "cashfree"
    (docs / "_shared").mkdir(parents=True)
    (docs / "subscriptions").mkdir()
    (docs / "_shared" / "auth.md").write_text("x")
    (docs / "subscriptions" / "m.md").write_text("y")
    (tmp_path / "connector_docs" / "cashfree.md").write_text("# spec")
    ctx = assemble_context(
        psp_name="cashfree", source=str(docs), output_dir=tmp_path / "out",
        lens_version_constraint="^0.2", grace_version="0.6", source_version="t",
        repo_root=repo, domain="subscriptions",
    )
    assert ctx.domain == "subscriptions"
