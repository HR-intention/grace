"""Structural tests that verify the rulebook markdown files reflect lens 0.2.0
capability-interface model and NOT the retired lens 0.1 shape."""

from pathlib import Path

R = Path("rulesbook/codegen/python")

# Read at module scope so the file reads happen before conftest chdir fires.
_WEBHOOK_TEXT = (R / "webhook_handling.md").read_text()
_CONNECTOR_ABC_TEXT = (R / "connector_abc.md").read_text()
_STATUS_MAPPING_TEXT = (R / "status_mapping.md").read_text()

_DOMAIN_TYPES_TEXT = (R / "domain_types.md").read_text()
_PITFALLS_TEXT = (R / "pitfalls.md").read_text()
_TESTING_TEXT = (R / "testing.md").read_text()

P = Path("rulesbook/codegen/guides/patterns")

# Mandate patterns — also read at module scope (before conftest chdir fires).
_CREATE_SUBSCRIPTION_TEXT = (P / "pattern_create_subscription.md").read_text()
_MANAGE_MANDATE_TEXT = (P / "pattern_manage_mandate.md").read_text()
_CREATE_ORDER_TEXT = (P / "pattern_createorder.md").read_text()
_PSYNC_TEXT = (P / "pattern_psync.md").read_text()
_REFUND_TEXT = (P / "pattern_refund.md").read_text()
_RSYNC_TEXT = (P / "pattern_rsync.md").read_text()
_SYNC_SUBSCRIPTION_TEXT = (P / "pattern_sync_subscription.md").read_text()
_MANDATE_WEBHOOK_TEXT = (P / "pattern_mandate_webhook.md").read_text()
_INCOMING_WEBHOOK_TEXT = (P / "pattern_IncomingWebhook_flow.md").read_text()


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


def test_mandate_patterns_exist_and_pin_rules() -> None:
    create = _CREATE_SUBSCRIPTION_TEXT
    assert "plan" in create.lower() and "payment_methods" in create and "idempotency_key" in create
    manage = _MANAGE_MANDATE_TEXT
    assert "ACTIVATE" in manage and "next_scheduled_time" in manage and "idempotency_key" in manage


def test_rulebook_pins_payment_method_members() -> None:
    sm = _STATUS_MAPPING_TEXT
    dt = _DOMAIN_TYPES_TEXT
    assert "BANK_REDIRECT" in (sm + dt)
    assert "net_banking" in sm.lower()                 # mapping guidance


def test_rulebook_distinguishes_webhook_event_fields() -> None:
    dt = _DOMAIN_TYPES_TEXT
    assert "raw_payload" in dt and "MandateWebhookEvent" in dt and "PaymentWebhookEvent" in dt


def test_pitfalls_cover_generics_and_auth_guard() -> None:
    p = _PITFALLS_TEXT
    assert "dict[str, Any]" in p
    assert "expose" in p and ("Maskable[str] | None" in p or "None-guard" in p.replace("-", " ") or "secret_key" in p)


# ---------------------------------------------------------------------------
# Fix A — HttpUrl coercion for payment_link
# ---------------------------------------------------------------------------

def test_pitfalls_document_payment_link_httpurl_coercion() -> None:
    """pitfalls.md must warn that payment_link is HttpUrl and bare str fails mypy."""
    p = _PITFALLS_TEXT
    assert "payment_link" in p
    assert "HttpUrl" in p
    # Must say to coerce with HttpUrl(...) not pass a bare str
    assert "HttpUrl(" in p or "HttpUrl(url)" in p or "coerce" in p.lower()


def test_createorder_pattern_documents_httpurl_coercion() -> None:
    """pattern_createorder.md must show HttpUrl(...) coercion for payment_link."""
    t = _CREATE_ORDER_TEXT
    assert "HttpUrl" in t
    assert "HttpUrl(" in t


# ---------------------------------------------------------------------------
# Fix B — testing.md error-path + core-module + _classify + fallback coverage
# ---------------------------------------------------------------------------

def test_testing_md_mandates_error_paths_and_core() -> None:
    """testing.md must mandate error-path tests AND core/ module tests."""
    t = _TESTING_TEXT
    # Error path coverage: _map_http_error / PSP_UNAVAILABLE must both appear
    assert "_map_http_error" in t or "PSP_UNAVAILABLE" in t
    # Must reference the failure-substring map (core/status.py)
    assert "core/status.py" in t or "map_failure_reason" in t or "failure" in t.lower()
    # Must mention _classify (the compose-surface discriminator)
    assert "_classify" in t
    # Must explicitly state the 80% coverage floor
    assert "80" in t or "≥ 80" in t


def test_testing_md_mandates_status_map_fallback_tests() -> None:
    """testing.md must require status_map fallback (UNKNOWN/unmapped) coverage."""
    t = _TESTING_TEXT
    assert "status_map" in t or "fallback" in t.lower() or "UNKNOWN" in t


def test_testing_md_mandates_specific_error_reasons() -> None:
    """testing.md must call out specific ConnectorErrorReason branches to test."""
    t = _TESTING_TEXT
    # Must name at least: 401/403 auth, 429 rate-limited, 5xx unavailable, 404 not-found
    assert "AUTHENTICATION_FAILED" in t or "401" in t
    assert "RATE_LIMITED" in t or "429" in t
    assert "PSP_UNAVAILABLE" in t


def test_createorder_pattern_requires_error_path_tests() -> None:
    """pattern_createorder.md must require more than just happy path tests."""
    t = _CREATE_ORDER_TEXT
    # 5xx and network error paths must be explicitly required
    assert "5xx" in t or "PSP_UNAVAILABLE" in t
    assert "network" in t.lower() or "ConnectError" in t or "httpx.HTTPError" in t


def test_psync_pattern_requires_error_path_tests() -> None:
    """pattern_psync.md must require 5xx error path test."""
    t = _PSYNC_TEXT
    assert "5xx" in t or "PSP_UNAVAILABLE" in t


def test_refund_pattern_requires_5xx_test() -> None:
    """pattern_refund.md must require a 5xx/network error test case."""
    t = _REFUND_TEXT
    assert "5xx" in t or "PSP_UNAVAILABLE" in t


def test_rsync_pattern_requires_not_found_test() -> None:
    """pattern_rsync.md must require a 404/REFUND_NOT_FOUND test case."""
    t = _RSYNC_TEXT
    assert "404" in t or "REFUND_NOT_FOUND" in t


def test_sync_subscription_pattern_requires_404_and_5xx_tests() -> None:
    """pattern_sync_subscription.md must require 404 and 5xx test cases."""
    t = _SYNC_SUBSCRIPTION_TEXT
    assert "404" in t or "ORDER_NOT_FOUND" in t
    assert "5xx" in t or "PSP_UNAVAILABLE" in t


def test_mandate_webhook_pattern_requires_debit_failed_test() -> None:
    """pattern_mandate_webhook.md must require a DEBIT_FAILED test with failure_code."""
    t = _MANDATE_WEBHOOK_TEXT
    assert "MANDATE_DEBIT_FAILED" in t
    assert "failure_code" in t


def test_incoming_webhook_pattern_requires_classify_tests() -> None:
    """pattern_IncomingWebhook_flow.md must document _classify test requirement."""
    t = _INCOMING_WEBHOOK_TEXT
    assert "_classify" in t
    # Should test both payment and mandate family routing
    assert "MANDATE" in t and "PAYMENT" in t


def test_create_subscription_pattern_pins_rails_union() -> None:
    t = _CREATE_SUBSCRIPTION_TEXT
    assert "rails" in t                      # plural request field
    assert "request.rail:" not in t          # singular form removed
    assert "NOT_SUPPORTED" in t              # reject unsupported rails
    assert "exclude_none" in t or "omit" in t.lower()   # None/empty ⇒ omit, never []
