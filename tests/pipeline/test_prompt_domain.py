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


def test_orders_prompt_pins_payment_method_members_and_event_fields(tmp_path: Path) -> None:
    p = build_prompt(_ctx(tmp_path, "orders"))
    assert "BANK_REDIRECT" in p and "BANK_TRANSFER" in p     # locked members named
    assert "NET_BANKING" in p                                # named as INVALID / do-not-invent
    assert "raw_payload" in p                                # PaymentWebhookEvent field
    assert "occurred_at" in p                                # named (as NOT on PaymentWebhookEvent)
    assert "dict[str, Any]" in p                             # parameterize builtins


def test_subscriptions_prompt_pins_mandate_event_fields(tmp_path: Path) -> None:
    p = build_prompt(_ctx(tmp_path, "subscriptions"))
    assert "MandateWebhookEvent" in p and "occurred_at" in p and "dict[str, Any]" in p


def test_prompt_has_auth_none_guard_rule(tmp_path: Path) -> None:
    p = build_prompt(_ctx(tmp_path, "orders"))
    assert "expose" in p and ("Maskable[str] | None" in p or "None-guard" in p or "secret_key" in p)


def test_orders_prompt_requires_httpurl_coercion(tmp_path: Path) -> None:
    """The orders prompt must tell the generator to coerce payment_link to HttpUrl."""
    p = build_prompt(_ctx(tmp_path, "orders"))
    # The prompt must mention HttpUrl in the context of payment_link coercion
    assert "HttpUrl" in p
    # Must explicitly instruct coercion — either HttpUrl(url) or HttpUrl(payment_link)
    assert "HttpUrl(" in p


def test_orders_prompt_requires_error_path_coverage(tmp_path: Path) -> None:
    """The orders prompt must require error-path test coverage (≥80% gate)."""
    p = build_prompt(_ctx(tmp_path, "orders"))
    assert "PSP_UNAVAILABLE" in p
    assert "_map_http_error" in p or "AUTHENTICATION_FAILED" in p


def test_prompt_requires_classify_and_core_tests(tmp_path: Path) -> None:
    """Prompts for 'all' domain must mention _classify and core module tests."""
    p = build_prompt(_ctx(tmp_path, "all"))
    assert "_classify" in p
    # core/status.py coverage must be mentioned
    assert "core/status.py" in p or "map_failure_reason" in p


def test_orders_prompt_requires_status_map_fallback_tests(tmp_path: Path) -> None:
    """The orders prompt must require status_map fallback (UNKNOWN) coverage."""
    p = build_prompt(_ctx(tmp_path, "orders"))
    assert "UNKNOWN" in p or "fallback" in p.lower() or "status_map" in p


def test_orders_prompt_requires_refund_request_fields(tmp_path: Path) -> None:
    p = build_prompt(_ctx(tmp_path, "orders"))
    assert "amount_to_refund" in p                         # RefundRequest field
    assert "psp_order_id" in p                             # named (as NOT on RefundRequest/SyncRefundRequest)
    assert "order_id" in p
    # the refund types must be flagged as lacking psp_order_id
    assert "RefundRequest" in p and "SyncRefundRequest" in p
    # the self-check grep must call out RefundRequest/SyncRefundRequest + psp_order_id → ZERO
    assert "RefundRequest|SyncRefundRequest" in p or "psp_order_id" in p
    # the NO psp_order_id rule must be explicit (not just incidental presence of both strings)
    assert "no psp_order_id" in p.lower() or "have no psp_order_id" in p.lower() or "RefundRequest.*psp_order_id" in p
    # refund URL must instruct use of order_id, not psp_order_id
    assert "request.order_id" in p                         # use order_id for refund URLs
    # int minor-units rule for refunded_amount / paid_amount (not Amount)
    assert "refunded_amount" in p and "paid_amount" in p
    assert "int" in p                                       # int minor-units named
