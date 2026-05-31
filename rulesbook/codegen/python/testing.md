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

Per `file_layout.md`, the test tree is domain-split:

```
tests/integration/connectors/<psp>/
  orders/
    test_create_order.py
    test_sync_payment.py
    test_refund.py
    test_sync_refund.py
  subscriptions/
    test_create_subscription.py
    test_sync_subscription.py
    test_cancel_subscription.py
    test_pause_subscription.py
    test_resume_subscription.py
  test_webhook_router.py
```

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

## Coverage discipline

- `status_map.py` per domain: one parametrized test per map entry + the `UNKNOWN`/fallback
  branch.
- `core/auth.py`: `verify_signature` direct unit test (correct → `True`, tampered → `False`,
  missing headers → `False`).
- Every `except` branch, every `if status == X:` in `_map_http_error`, every fallback path
  in `_map_*` helpers must have at least one test exercising it.
- Test functions and all helpers need `-> None` (or appropriate return type) annotations for
  `mypy --strict`.
