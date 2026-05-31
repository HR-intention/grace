"""Structural tests that verify the rulebook markdown files reflect lens 0.2.0
capability-interface model and NOT the retired lens 0.1 shape."""

from pathlib import Path

R = Path("rulesbook/codegen/python")

# Read at module scope so the file reads happen before conftest chdir fires.
_WEBHOOK_TEXT = (R / "webhook_handling.md").read_text()
_CONNECTOR_ABC_TEXT = (R / "connector_abc.md").read_text()
_STATUS_MAPPING_TEXT = (R / "status_mapping.md").read_text()


def test_webhook_rule_is_shared_router_not_connector_method() -> None:
    t = _WEBHOOK_TEXT
    assert "WebhookHandlers" in t and "WebhookFamily" in t and "build_webhook_handlers" in t
    assert "handle_webhook" not in t            # retired in 0.2.0


def test_connector_abc_rule_is_capability_mixins() -> None:
    t = _CONNECTOR_ABC_TEXT
    assert "PaymentsConnector" in t and "MandateConnector" in t
    assert "_<Psp>Base" in t or "shared base" in t


def test_status_mapping_has_failure_class_published_note() -> None:
    t = _STATUS_MAPPING_TEXT
    assert "FAILURE_CLASS" in t and "never branch" in t.lower()
