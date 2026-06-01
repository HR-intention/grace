from __future__ import annotations

from grace.pipeline.domain_breakdown import domain_of_file, domain_of_test, build_domain_breakdown


def test_domain_of_file() -> None:
    assert domain_of_file("src/lens/connectors/cashfree/orders/webhooks.py") == "orders"
    assert domain_of_file("src/lens/connectors/cashfree/subscriptions/connector.py") == "subscriptions"
    assert domain_of_file("src/lens/connectors/cashfree/core/auth.py") == "core"
    assert domain_of_file("src/lens/connectors/cashfree/connector.py") == "root"


def test_domain_of_test_heuristic_flat() -> None:
    assert domain_of_test("tests/integration/connectors/cashfree/test_refund.py::test_x") == "orders"
    assert domain_of_test("tests/integration/connectors/cashfree/test_create_subscription.py::t") == "subscriptions"
    assert domain_of_test("tests/integration/connectors/cashfree/test_webhook_router.py::t") == "root"


def test_domain_of_test_path_takes_precedence() -> None:
    assert domain_of_test("tests/.../cashfree/subscriptions/test_sync.py::t") == "subscriptions"


def test_build_domain_breakdown() -> None:
    mypy_stdout = (
        "src/lens/connectors/cashfree/orders/webhooks.py:82: error: Missing type arguments [type-arg]\n"
        "src/lens/connectors/cashfree/orders/webhooks.py:85: error: bad [call-arg]\n"
        "src/lens/connectors/cashfree/subscriptions/webhooks.py:91: error: x [type-arg]\n"
        "src/lens/connectors/cashfree/core/auth.py:28: error: y [union-attr]\n"
        "Found 4 errors in 3 files\n"
    )
    pytest_stdout = (
        "FAILED tests/integration/connectors/cashfree/test_refund.py::test_refund_happy_path\n"
        "FAILED tests/integration/connectors/cashfree/test_webhook_router.py::TestPaymentWebhookParsing::test_payment_success\n"
    )
    coverage = {"files": {
        "src/lens/connectors/cashfree/orders/connector.py": {"summary": {"covered_lines": 75, "num_statements": 100}},
        "src/lens/connectors/cashfree/subscriptions/connector.py": {"summary": {"covered_lines": 90, "num_statements": 100}},
    }}
    bd = build_domain_breakdown(mypy_stdout=mypy_stdout, pytest_stdout=pytest_stdout, coverage=coverage)
    assert bd["orders"]["mypy_errors"] == 2
    assert bd["subscriptions"]["mypy_errors"] == 1
    assert bd["core"]["mypy_errors"] == 1
    assert bd["orders"]["tests_failed"] == 1
    assert bd["root"]["tests_failed"] == 1            # webhook_router → root
    assert round(bd["orders"]["coverage_pct"], 1) == 75.0
    assert round(bd["subscriptions"]["coverage_pct"], 1) == 90.0
