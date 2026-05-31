from pathlib import Path

SPEC = Path("connector_docs/cashfree.md").read_text()
REQUIRED = [
    "MandateStatus", "WebhookEventType", "FAILURE_CLASS",
    "CARD_EXPIRED", "LINK_EXPIRED", "ON_HOLD",
    "MANDATE_DEBIT_NOTIFIED", "MANDATE_EXPIRING_SOON",
    "USER_CANCELLED", "retry_attempts", "SUBSCRIPTION_REFUND_STATUS",
    "UPI_AUTOPAY", "next_scheduled_time", "plan_recurring_amount",
]


def test_cashfree_spec_has_section_6_rows() -> None:
    missing = [t for t in REQUIRED if t not in SPEC]
    assert not missing, f"cashfree.md missing §6 tokens: {missing}"
