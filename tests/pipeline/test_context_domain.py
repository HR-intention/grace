from __future__ import annotations

from pathlib import Path
from grace.pipeline.context import assemble_context


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_rulebook_selection_is_domain_keyed() -> None:
    from grace.pipeline.context import rulebook_files_for_domain
    orders = " ".join(rulebook_files_for_domain("orders"))
    subs = " ".join(rulebook_files_for_domain("subscriptions"))
    assert "connector_abc.md" in orders and "connector_abc.md" in subs   # core always
    assert "pattern_create_subscription.md" in subs
    assert "pattern_create_subscription.md" not in orders
    assert "pattern_createorder.md" in orders
    assert "pattern_createorder.md" not in subs
    all_ = " ".join(rulebook_files_for_domain("all"))
    assert "pattern_create_subscription.md" in all_ and "pattern_createorder.md" in all_


def test_doc_bundle_is_domain_scoped(tmp_path: Path) -> None:
    repo = REPO_ROOT
    docs = tmp_path / "connector_docs" / "cashfree"
    for sub in ("_shared", "orders", "subscriptions"):
        (docs / sub).mkdir(parents=True)
        (docs / sub / f"{sub}.md").write_text(sub)
    (tmp_path / "connector_docs" / "cashfree.md").write_text("# spec")
    ctx = assemble_context(
        psp_name="cashfree", source=str(docs), output_dir=tmp_path / "out",
        lens_version_constraint="^0.2", grace_version="0.6", source_version="t",
        repo_root=repo, domain="subscriptions",
    )
    names = {p.name for p in ctx.psp_docs.local_paths}
    assert "_shared.md" in names and "subscriptions.md" in names and "cashfree.md" in names
    assert "orders.md" not in names      # other domain excluded


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
