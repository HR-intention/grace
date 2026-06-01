# Testing

The emitted package must have working pytest tests. Aim for ≥ 80% line coverage on the
package; the rubric awards 0–25 points linearly.

---

## Framework

- `pytest >= 8.0`, `pytest-asyncio` (configured `asyncio_mode = "auto"` — tests just declare
  `async def test_...`).
- `httpx.MockTransport` for **all** HTTP-touching tests. **Never** hit a live PSP from a unit
  test.

---

## Required test files

Per `file_layout.md`, write all tests into the **package-local `tests/` directory**:

```
tests/
  test_create_order.py
  test_sync_payment.py
  test_refund.py
  test_sync_refund.py
  test_create_subscription.py
  test_sync_subscription.py
  test_manage_mandate.py       # covers cancel_subscription, pause_subscription, resume_subscription
  test_pause_subscription.py
  test_resume_subscription.py
  test_mandate_webhook.py
  test_webhook_router.py
```

> **Relocation note**: Grace's pipeline moves `<output_dir>/tests/` to the consumer's
> configured `paths.tests_dir/<psp>/` after generation. Do NOT write the final path
> `tests/integration/connectors/<psp>/…` yourself — that doubles the path and
> pytest collects 0 tests (0% coverage).

---

## Required cases — payment domain (`orders/`)

### `test_create_order.py`
- **Happy path**: PSP returns 200 with `psp_order_id` + `payment_link`; assert
  `CreateOrderResponse` round-trips.
- **4xx path**: PSP returns 400; assert `ConnectorError(reason=INVALID_REQUEST)`.
- **5xx path**: PSP returns 503; assert `ConnectorError(reason=PSP_UNAVAILABLE)`.
- **Network-error path**: `MockTransport` raises `httpx.ConnectError`; assert
  `ConnectorError(reason=PSP_UNAVAILABLE)`.
- **HTTP error mapping coverage**: parametrized test over every branch in `_map_http_error`
  (at minimum 400, 401, 403, 404, 409, 429, one 5xx).

### `test_sync_payment.py`
- **Single-attempt path**: one `SUCCESS` attempt; assert `attempts` has one entry.
- **Multi-attempt path**: first `FAILED` then `SUCCESS`; both attempts present in order.
- **5xx path**: endpoint returns 503; assert `ConnectorError(reason=PSP_UNAVAILABLE)`.
- **Unknown PSP order-status path**: unknown `order_status` string; assert does NOT raise,
  `response.status` is the documented fallback (exercises the `_log.warning` path).

### `test_refund.py`
- **Happy path**: PSP returns `psp_refund_id` + `PENDING` (or `SUCCESS`).
- **Already-refunded path**: PSP returns 4xx; assert `ConnectorError(reason=INVALID_ORDER_STATE)`.
- **5xx path**: PSP returns 502; assert `ConnectorError(reason=PSP_UNAVAILABLE)`.

### `test_sync_refund.py`
- **PENDING path**: assert `RefundStatus.PENDING`.
- **SUCCESS path**: assert `RefundStatus.SUCCESS` + `refunded_amount` echoes.
- **Not-found path**: 404; assert `ConnectorError(reason=REFUND_NOT_FOUND)`.
- **Malformed-response path**: 200 with a body missing a required wire-model field; assert
  `ConnectorError(reason=INTERNAL)` (exercises the `except ValidationError` branch).

---

## Required cases — mandate domain (`subscriptions/`)

### `test_create_subscription.py`
- **Happy path (UPI_AUTOPAY)**: PSP returns `psp_mandate_ref` + `PENDING_AUTHORIZATION` +
  `approval.type == "UPI_COLLECT"` (or `"UPI_INTENT"`); assert `CreateSubscriptionResponse`
  round-trips.
- **Happy path (CARD_EMANDATE)**: assert `approval.type == "REDIRECT"`.
- **4xx path**: 400 body; assert `ConnectorError(reason=INVALID_REQUEST)`.
- **5xx path**: 503; assert `ConnectorError(reason=PSP_UNAVAILABLE)`.
- **All `CreateSubscriptionRequest` fields forwarded**: `customer_contact.email`,
  `customer_contact.phone`, `first_charge_at`, `description`, `return_url`, `upi_vpa`,
  `idempotency_key` — assert the mock received them in the wire request.

### `test_sync_subscription.py`
- **ACTIVE mandate**: assert `SyncSubscriptionResponse.status == MandateStatus.ACTIVE`.
- **SUSPENDED mandate with last_debit**: assert `last_debit.failure_code` populated.
- **5xx path**: assert `ConnectorError(reason=PSP_UNAVAILABLE)`.

### `test_cancel_subscription.py`, `test_pause_subscription.py`, `test_resume_subscription.py`
Each needs:
- **Happy path**: assert `ManageMandateResponse.status` is the expected post-op `MandateStatus`.
- **`idempotency_key` forwarded**: assert the mock wire request includes the key.
- **5xx path**: assert `ConnectorError(reason=PSP_UNAVAILABLE)`.
- `test_resume_subscription.py` additionally: **`effective_at` forwarded** if provided.

---

## Cross-domain webhook router test (`test_webhook_router.py`)

This test exercises the full `build_webhook_handlers → WebhookRouter.handle` dispatch path.

### Required cases

- **Signed PAYMENT_SUCCESS**: build a valid signed payload; assert the returned event is
  `PaymentWebhookEvent` and `event.attempt.status == PaymentAttemptStatus.SUCCESS`.
- **Signed MANDATE_AUTHORIZED**: build a valid signed mandate payload; assert the returned
  event is `MandateWebhookEvent` and `event.event_type == WebhookEventType.MANDATE_AUTHORIZED`.
- **Signed MANDATE_DEBIT_FAILED**: assert `event.debit.failure_code` is populated.
- **Tampered payload**: mutate bytes after signing so they *actually differ*, then assert
  `ConnectorError(reason=WEBHOOK_SIGNATURE_FAILED)`. See pattern §8 below.
- **Unknown event-type (not PAYMENT or MANDATE family)**: if the PSP emits a new-format event
  the classifier cannot route, assert `ConnectorError(reason=NOT_SUPPORTED)` (or the parser
  returns a fallback event — whichever the connector spec documents).

---

## Test fixture pattern

```python
import httpx
import pytest
from datetime import datetime, timezone
from pydantic import HttpUrl

from lens.factory import ConnectorConfig, ConnectorFactory
from lens.common import Maskable
from lens.domain_types import (
    CreateOrderRequest,
    SyncPaymentRequest,
    RefundRequest,
    SyncRefundRequest,
    Amount,
    CreateSubscriptionRequest,
    CustomerContact,
    ManageMandateRequest,
)
from lens.enums import Currency, PaymentMethod, MandateRail, MandateIntervalType


def _config() -> ConnectorConfig:
    return ConnectorConfig(
        name="<psp>",
        api_key=Maskable("test_key"),
        secret_key=Maskable("test_secret"),
        webhook_secret=Maskable("test_webhook"),
    )


def _build_orders_connector(handler) -> <Psp>Orders:
    c = <Psp>Orders(_config())
    c._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url=c.base_url)
    return c


def _build_subscriptions_connector(handler) -> <Psp>Subscriptions:
    c = <Psp>Subscriptions(_config())
    c._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url=c.base_url)
    return c


def _create_order_request() -> CreateOrderRequest:
    return CreateOrderRequest(
        merchant_id="MERCHANT_123",
        order_id="orbit-uuid-123",
        amount=Amount(minor_units=50000, currency=Currency.INR),
        return_url=HttpUrl("https://merchant.example/return"),
    )


def _create_subscription_request() -> CreateSubscriptionRequest:
    return CreateSubscriptionRequest(
        merchant_id="MERCHANT_123",
        idempotency_key="idem-mandate-1",
        rail=MandateRail.UPI_AUTOPAY,
        customer_ref="cust-ref-1",
        customer_contact=CustomerContact(email="test@example.com", phone="9999999999"),
        amount=Amount(minor_units=100000, currency=Currency.INR),
        max_amount=Amount(minor_units=500000, currency=Currency.INR),
        interval_type=MandateIntervalType.MONTH,
        description="Monthly subscription",
        expires_at=datetime(2027, 1, 1, tzinfo=timezone.utc),
        return_url=HttpUrl("https://merchant.example/mandate-return"),
    )
```

---

## Tamper-test pattern (safe mutation)

```python
# CORRECT — replace a value that is deterministically present in the signed payload:
tampered = payload.replace(b'"SUCCESS"', b'"FAILED"')
assert tampered != payload, "tampering must actually change the bytes"

with pytest.raises(ConnectorError) as exc_info:
    await router.handle(tampered, {
        "x-webhook-timestamp": timestamp,
        "x-webhook-signature": sig,   # signature of ORIGINAL payload
    })
assert exc_info.value.reason == ConnectorErrorReason.WEBHOOK_SIGNATURE_FAILED
```

```python
# WRONG — JSON always ends with `}`, so this is a no-op:
tampered = payload[:-1] + b"}"   # no change
```

Always include the `assert tampered != payload` guard.

---

## Five failure patterns to avoid

### 1. Mock-transport path assertions must include the `base_url` prefix

When the connector calls `self._client.post("/endpoint", ...)`, `request.url.path` is
`/<base_path>/endpoint` (the `base_url`'s path prefix plus the endpoint). Use
`.endswith("/endpoint")` in assertions, not `== "/endpoint"`.

### 2. `_map_http_error` must differentiate 4xx from 5xx

Map 400/422 → `INVALID_REQUEST`, 401 → `AUTHENTICATION_FAILED`, 403 → `AUTHORIZATION_FAILED`,
404 → `ORDER_NOT_FOUND`, 409 → `INVALID_ORDER_STATE`, 429 → `RATE_LIMITED`,
5xx → `PSP_UNAVAILABLE`. Generic "everything → PSP_UNAVAILABLE" tanks the 4xx test.

### 3. `sync_payment` test handler must respond to BOTH endpoints

`sync_payment` typically hits the order endpoint AND the payments-list endpoint. A handler
that only returns 200 for the first URL gets a 404 on the second. Branch on path.

### 4. Webhook test fixtures must sign payloads the same way the connector verifies

The test's signing function must mirror `core/auth.py`'s `verify_signature` exactly —
same secret, same algorithm, same encoding. The secret used in the fixture must match
the `webhook_secret` in `_config()`.

### 5. Assertions must check mock-RESPONSE values, not request-INPUT values

The connector returns PSP-side IDs from the response body. The input `psp_refund_id` on
`SyncRefundRequest` is "which refund to look up"; the response body's ID is "what the PSP says
about that refund". They can differ. Assert against `handler`'s return value, not the input.

---

## Coverage floor (≥ 80%) requires testing more than happy paths

The rubric awards 0–25 points linearly on line coverage. **The coverage gate is ≥ 80%**.
Happy-path tests alone consistently land at 60–70%. Reaching ≥ 80% requires exercising the
error branches, shared `core/` helpers, status-map fallbacks, and the `_classify` discriminator.

### Required error-path tests (per flow)

For **every** flow method in `orders/connector.py` and `subscriptions/connector.py`, write at
least one test per `ConnectorError` reason the flow can raise:

| HTTP status / condition | Expected `ConnectorErrorReason` |
|---|---|
| 401 | `AUTHENTICATION_FAILED` |
| 403 | `AUTHORIZATION_FAILED` |
| 404 (order/mandate) | `ORDER_NOT_FOUND` or `REFUND_NOT_FOUND` |
| 409 / 422 (already-refunded, invalid state) | `INVALID_ORDER_STATE` |
| 429 | `RATE_LIMITED` |
| 5xx (any) | `PSP_UNAVAILABLE` |
| `httpx.ConnectError` / network failure | `PSP_UNAVAILABLE` |

Use `httpx.MockTransport` returning those status codes. The `_map_http_error` helper covers
most 4xx branches; test them parametrically (minimum: 400, 401, 403, 404, 409, 429, one 5xx).

### Required tests for shared `core/` modules

**`core/status.py` — failure-substring mapper** (typically 24% coverage without direct tests):

The `map_failure_reason` function maps free-text PSP failure messages to
`(PaymentFailureCode, FailureClass | None)` via ordered substring matching. It must be tested
directly, not just through connector flows:

```python
import pytest
from lens.connectors.<psp>.core.status import map_failure_reason
from lens.enums import PaymentFailureCode, FailureClass, FAILURE_CLASS

@pytest.mark.parametrize("text,expected_code", [
    ("payment declined by bank",         PaymentFailureCode.CARD_DECLINED),
    ("insufficient funds in account",    PaymentFailureCode.INSUFFICIENT_FUNDS),
    ("mandate revoked by customer",      PaymentFailureCode.MANDATE_REVOKED),
    ("debit limit exceeded for upi",     PaymentFailureCode.DEBIT_LIMIT_EXCEEDED),
    ("authentication failed",            PaymentFailureCode.AUTHENTICATION_FAILED),
])
def test_map_failure_reason_substrings(text: str, expected_code: PaymentFailureCode) -> None:
    code, fc = map_failure_reason(text)
    assert code is expected_code
    assert fc is FAILURE_CLASS.get(expected_code)

def test_map_failure_reason_unknown_default() -> None:
    code, fc = map_failure_reason("unrecognised gibberish xyz")
    assert code is PaymentFailureCode.UNKNOWN
    assert fc is None

def test_map_failure_reason_none_input() -> None:
    code, _ = map_failure_reason(None)
    assert code is PaymentFailureCode.UNKNOWN
```

**`core/models.py`** — the shared wire models (`CashfreeErrorBody`, `CashfreeWebhookEnvelope`,
etc.) are used by the connector at runtime. If these models are **not imported and instantiated
anywhere in the generated tests**, their lines appear as 0% in coverage reports. Ensure at
least one test instantiates each shared wire model, OR (if the model is genuinely unused by
any flow) remove it from the package.

### Required tests for `_classify` (compose surface, `webhooks.py`)

`_classify(raw: bytes) -> WebhookFamily` is the webhook-family discriminator. It must be
tested directly (in addition to the router integration test):

```python
from lens.connectors.<psp>.webhooks import _classify
from lens.webhook import WebhookFamily

def test_classify_payment_event() -> None:
    raw = b'{"type": "PAYMENT_SUCCESS", "data": {}}'
    assert _classify(raw) is WebhookFamily.PAYMENT

def test_classify_mandate_event() -> None:
    raw = b'{"type": "SUBSCRIPTION_PAYMENT_SUCCESS", "data": {}}'
    assert _classify(raw) is WebhookFamily.MANDATE

def test_classify_unknown_event_falls_back_to_payment() -> None:
    raw = b'{"type": "SOME_UNRECOGNISED_EVENT", "data": {}}'
    # Unknown types must fall back to PAYMENT (safe default) — not raise
    assert _classify(raw) is WebhookFamily.PAYMENT

def test_classify_malformed_json_falls_back_to_payment() -> None:
    raw = b"not json at all"
    assert _classify(raw) is WebhookFamily.PAYMENT
```

### Required tests for `status_map.py` fallbacks

Each `status_map.py` (orders and subscriptions) has a fallback branch that fires when the PSP
sends an unmapped status string. These must be tested:

```python
from lens.connectors.<psp>.orders.status_map import map_payment_status, map_order_status, map_refund_status
from lens.enums import PaymentAttemptStatus, PaymentFailureCode, OrderStatus, RefundStatus

def test_map_payment_status_unknown_falls_back() -> None:
    status, code = map_payment_status("COMPLETELY_UNKNOWN_STATUS")
    assert status is PaymentAttemptStatus.FAILED
    assert code is PaymentFailureCode.UNKNOWN

def test_map_order_status_unknown_falls_back() -> None:
    status = map_order_status("COMPLETELY_UNKNOWN_STATUS")
    assert status is OrderStatus.FAILED  # or UNKNOWN per the connector's fallback

def test_map_refund_status_unknown_falls_back() -> None:
    status = map_refund_status("COMPLETELY_UNKNOWN_STATUS")
    assert status is RefundStatus.FAILED  # or PENDING per the connector's fallback
```

Similarly for `subscriptions/status_map.py`:

```python
from lens.connectors.<psp>.subscriptions.status_map import map_subscription_status, map_debit_status
from lens.enums import MandateStatus, MandateDebitStatus

def test_map_subscription_status_unknown_falls_back() -> None:
    status = map_subscription_status("COMPLETELY_UNKNOWN_STATUS")
    assert status is MandateStatus.FAILED  # or the documented fallback

def test_map_debit_status_unknown_falls_back() -> None:
    status = map_debit_status("COMPLETELY_UNKNOWN_STATUS")
    assert status is MandateDebitStatus.FAILED
```

**Finality / suspend mapping (lens guarantee — assert explicitly).** Beyond the `UNKNOWN`
fallback above, the *suspend/hold* finality outcome lens guarantees Orbit must be asserted on
**both** subscription mapping surfaces — never left to incidental coverage. Use the PSP's
hold/suspend term from `connector_docs/<psp>.md` §6 (`ON_HOLD` for Cashfree):

```python
from lens.connectors.<psp>.subscriptions.status_map import (
    map_subscription_status,
    map_status_changed_event,   # name varies: the fn mapping the PSP suspend signal -> WebhookEventType
)
from lens.enums import MandateStatus, WebhookEventType

def test_hold_status_maps_to_suspended() -> None:
    assert map_subscription_status("<HOLD_TERM>") is MandateStatus.SUSPENDED

def test_hold_event_maps_to_mandate_suspended() -> None:
    assert map_status_changed_event("<HOLD_TERM>") is WebhookEventType.MANDATE_SUSPENDED
```

Why mandatory: in periodic mode there is no `*_FAILED_FINAL` event, so the `MANDATE_SUSPENDED`
mapping is the signal Orbit relies on to call a subscription permanently failed
(`status_mapping.md` §5). A happy-path sync test does not exercise it.

---

## Coverage discipline

- `status_map.py` per domain: one parametrized test per map entry + the `UNKNOWN`/fallback
  branch.
- `core/auth.py`: `verify_signature` direct unit test (correct → `True`, tampered → `False`,
  missing headers → `False`).
- `core/status.py`: direct tests of `map_failure_reason` — representative substrings → expected
  `(PaymentFailureCode, FailureClass)` + `UNKNOWN` default for no-match + `None` input.
- Every `except` branch, every `if status == X:` in `_map_http_error`, every fallback path
  in `_map_*` helpers must have at least one test exercising it.
- Test functions and all helpers need `-> None` (or appropriate return type) annotations for
  `mypy --strict`.
