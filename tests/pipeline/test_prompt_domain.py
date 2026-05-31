from __future__ import annotations

from pathlib import Path

from grace.pipeline.context import assemble_context
from grace.pipeline.prompt import build_prompt
from grace.pipeline.types import GenerationContext


REPO_ROOT = Path(__file__).resolve().parents[2]


def _ctx(tmp_path: Path, domain: str) -> GenerationContext:
    """Build a GenerationContext via assemble_context for prompt tests."""
    docs = tmp_path / "connector_docs" / "cashfree"
    for sub in ("_shared", "orders", "subscriptions"):
        (docs / sub).mkdir(parents=True)
        (docs / sub / f"{sub}.md").write_text(sub)
    (tmp_path / "connector_docs" / "cashfree.md").write_text("# spec")
    return assemble_context(
        psp_name="cashfree",
        source=str(docs),
        output_dir=tmp_path / "out",
        lens_version_constraint="^0.2",
        grace_version="0.6.0",
        source_version="t",
        repo_root=REPO_ROOT,
        domain=domain,
    )


def test_prompt_pins_capability_imports_and_drops_retired(tmp_path: Path) -> None:
    p = build_prompt(_ctx(tmp_path, "subscriptions"))
    assert "from lens.mandate_connector import MandateConnector" in p
    assert "from lens.webhook import WebhookHandlers, WebhookFamily" in p
    assert "from lens.enums import" in p and "from lens.factory import" in p
    assert "_<Psp>Base" in p
    assert "handle_webhook" not in p                 # retired
    assert "no `Connector` suffix" not in p          # retired pitfall
    assert "build_webhook_handlers" in p             # named (as Grace-owned)


def test_prompt_orders_uses_payments_connector(tmp_path: Path) -> None:
    p = build_prompt(_ctx(tmp_path, "orders"))
    assert "from lens.payments_connector import PaymentsConnector" in p
    assert "create_order" in p


def test_typing_check_targets_deprecated_aliases_only(tmp_path: Path) -> None:
    p = build_prompt(_ctx(tmp_path, "orders"))
    assert "Optional" in p and "Callable" in p       # bans Optional, allows Callable
    # Deprecated aliases explicitly named as banned
    assert "Dict" in p
    assert "List" in p
    # Callable must be marked as allowed (not banned)
    assert "Callable" in p
    # The check should flag Callable as allowed
    assert "Callable" in p and "allowed" in p.lower()


def test_subscriptions_prompt_excludes_orders_content(tmp_path: Path) -> None:
    p = build_prompt(_ctx(tmp_path, "subscriptions"))
    # Orders-specific imports must not appear in subscriptions prompt
    assert "from lens.payments_connector import PaymentsConnector" not in p
    # Orders-specific method names must not appear
    assert "create_order" not in p
    # Orders class write-instruction (hierarchy item) must not appear
    # (compose-surface legitimately references <Psp>Orders in the "do NOT write" notice)
    assert "<Psp>Orders(_<Psp>Base, PaymentsConnector)" not in p
    # Compose-surface notice must still be present (shared cross-domain)
    assert "Grace generates" in p
    assert "DO NOT WRITE" in p


def test_orders_prompt_excludes_mandate_content(tmp_path: Path) -> None:
    p = build_prompt(_ctx(tmp_path, "orders"))
    # Mandate-specific imports must not appear in orders prompt
    assert "from lens.mandate_connector import MandateConnector" not in p
    # Mandate-specific method names must not appear
    assert "create_subscription" not in p
    # MandateConnector class must not appear in orders prompt
    assert "MandateConnector" not in p


def test_all_prompt_has_both_domains(tmp_path: Path) -> None:
    p = build_prompt(_ctx(tmp_path, "all"))
    # Both domain methods must appear
    assert "create_order" in p
    assert "create_subscription" in p
    # Both capability imports must appear
    assert "from lens.payments_connector import PaymentsConnector" in p
    assert "from lens.mandate_connector import MandateConnector" in p
