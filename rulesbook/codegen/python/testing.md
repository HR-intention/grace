# Testing

The emitted package must have working pytest tests. Aim for ≥ 80% line coverage on the package; the rubric awards 0–25 points linearly.

## Framework

- `pytest >= 8.0`, `pytest-asyncio` (configured `asyncio_mode = "auto"` in the consumer's pyproject — your tests just declare `async def test_...`).
- `httpx.MockTransport` for **all** HTTP-touching tests. **Never** hit a live PSP from a unit test.

## Required test files

Per `file_layout.md`, five test files are mandatory:

```
tests/test_create_order.py
tests/test_sync_payment.py
tests/test_refund.py
tests/test_sync_refund.py
tests/test_webhook.py
```

## Required cases per file

> Each defensive branch your connector code writes (every `except`, every
> `if status == X:` in the HTTP error mapper, every `_map_*` fallback
> for unknown PSP enum values) MUST be exercised by at least one test.
> Coverage drops below the 80% gate fast when the connector grows a
> 7-case HTTP-error mapper but tests only cover the 400 branch. The
> required cases below are the minimum that brings every error branch
> the rulebook permits into the test suite.

### `test_create_order.py`
- **Happy path**: PSP returns 200 with `psp_order_id` + `payment_link`; assert `CreateOrderResponse` round-trips.
- **4xx path**: PSP returns 400 with an error body; assert `ConnectorError(reason=INVALID_REQUEST)`.
- **5xx path**: PSP returns 503 (or any 5xx); assert `ConnectorError(reason=PSP_UNAVAILABLE)`. Hits the `500 <= status < 600` branch of the HTTP-error mapper.
- **Network-error path**: the `MockTransport` handler raises `httpx.ConnectError("dns")` (or any non-`HTTPStatusError` `httpx.HTTPError` subclass); assert `ConnectorError(reason=PSP_UNAVAILABLE)`. This covers the `except httpx.HTTPError` branch that wraps transport-level failures distinct from HTTP status errors.
- **HTTP error mapping coverage**: a single parametrized test (or a loop) that calls the connector's `_map_http_error` (or whatever the module-level helper is called) once per status code the helper handles — at minimum 400, 401, 403, 404, 409, 429, and one 5xx — and asserts the `ConnectorErrorReason` matches the mapping in `connector.py`. One file in the suite must own this; `test_create_order.py` is the home because it's where `_map_http_error` was introduced. Without this test, 6+ branches in the mapper land outside the test gap and tank coverage on `connector.py`.

### `test_sync_payment.py`
- **Single-attempt path**: order has one `SUCCESS` attempt; assert `attempts` has one entry, `paid_amount` populated.
- **Multi-attempt path**: order has two attempts, first `FAILED` then `SUCCESS`; assert `attempts` list contains both in observation order with the correct statuses, and `paid_amount` reflects the success.
- **5xx path**: order endpoint returns 503; assert `ConnectorError(reason=PSP_UNAVAILABLE)`.
- **Unknown PSP order-status path**: order endpoint returns `order_status: "WEIRD_NEW_STATUS"` (a string that's not in your `_PAYMENT_STATUS_MAP` / `_ORDER_STATUS_MAP`); assert the call succeeds (does NOT raise) and `response.status` is the documented fallback (typically `OrderStatus.FAILED` or `UNKNOWN`). Exercises the `_log.warning("unknown_*_status", ...)` fallback path that's otherwise dead code.

### `test_refund.py`
- **Happy path**: PSP returns a `psp_refund_id` + `PENDING` (or `SUCCESS`) status.
- **Already-refunded path**: PSP returns 4xx-equivalent ("refund already exists" / "amount exceeds remaining"); assert `ConnectorError(reason=INVALID_ORDER_STATE)` or the relevant typed error.
- **5xx path**: refund endpoint returns 502; assert `ConnectorError(reason=PSP_UNAVAILABLE)`.

### `test_sync_refund.py`
- **PENDING path**: PSP returns `pending`; assert `RefundStatus.PENDING`.
- **SUCCESS path**: PSP returns `success` + `refunded_amount`; assert `RefundStatus.SUCCESS` and the amount echoes.
- **Not-found path**: PSP returns 404 with an error body; assert `ConnectorError(reason=REFUND_NOT_FOUND)` (or whatever the connector's explicit 404 branch maps to — usually distinct from `ORDER_NOT_FOUND` here).
- **Malformed-response path**: handler returns 200 with a body missing one of the wire model's required fields (e.g., omit `refund_status`); assert `ConnectorError(reason=INTERNAL)`. Exercises the `except ValidationError` branch where Pydantic rejects the PSP's response shape — a class of bug that's been the source of real production incidents.

### `test_webhook.py`
- **Signed PAYMENT_SUCCESS**: build a valid signed payload; assert `WebhookEvent.attempt.status == PaymentAttemptStatus.SUCCESS`.
- **Signed PAYMENT_FAILED**: assert `attempt.status == FAILED` and `failure_code` populated (e.g., `CARD_DECLINED` or `USER_DROPPED` depending on PSP signal).
- **Signed REFUND_SUCCESS**: assert `refund.status == SUCCESS`.
- **Tampered payload**: mutate the payload bytes after signing so the bytes *actually* differ, then assert `ConnectorError(reason=WEBHOOK_SIGNATURE_FAILED)`. See pattern §8 below — the obvious-looking `payload[:-1] + b"}"` is a no-op because JSON always ends with `}`.
- **Unknown event type**: signed payload with `type: "UNKNOWN_FUTURE_EVENT_TYPE"`; assert `handle_webhook` does NOT raise and returns a `WebhookEvent` whose `event_type` is the documented fallback (typically `WebhookEventType.PAYMENT_INITIATED` or your equivalent). Covers the `_log.warning("unknown_webhook_event_type", ...)` path.

## Test fixture pattern (USE THESE EXACT KWARGS — locked types are extra="forbid")

```python
import httpx
import pytest
from datetime import datetime, timezone
from pydantic import HttpUrl

from lens.connectors.cashfree.connector import Cashfree
from lens.factory import ConnectorConfig
from lens.common import Maskable
from lens.domain_types import (
    CreateOrderRequest,
    SyncPaymentRequest,
    RefundRequest,
    SyncRefundRequest,
    Amount,
)
from lens.enums import Currency, PaymentMethod


# ----- ConnectorConfig — flat fields, no `credentials` bag, no `merchant_id` here.
def _config() -> ConnectorConfig:
    return ConnectorConfig(
        name="cashfree",                          # registry key
        api_key=Maskable("test_key"),             # NOT `credentials=...`
        secret_key=Maskable("test_secret"),
        webhook_secret=Maskable("test_webhook"),
    )


def _build_connector(handler) -> Cashfree:
    transport = httpx.MockTransport(handler)
    c = Cashfree(_config())
    # Replace the connector's client with one using the mock transport.
    c._client = httpx.AsyncClient(transport=transport, base_url=c.base_url)
    return c


# ----- Requests — every flow needs RequestCommon (merchant_id + order_id).
def _create_order_request() -> CreateOrderRequest:
    return CreateOrderRequest(
        merchant_id="MERCHANT_123",               # REQUIRED — from RequestCommon
        order_id="orbit-uuid-123",                # REQUIRED
        customer_id="customer-1",                 # optional
        idempotency_key="idem-key-1",             # optional
        amount=Amount(minor_units=50000, currency=Currency.INR),
        return_url=HttpUrl("https://merchant.example/return"),
        allowed_methods=[PaymentMethod.CARD, PaymentMethod.UPI],
    )


def _sync_payment_request() -> SyncPaymentRequest:
    return SyncPaymentRequest(
        merchant_id="MERCHANT_123",
        order_id="orbit-uuid-123",
        psp_order_id="cf_order_abc",              # the PSP-side id
    )


def _refund_request() -> RefundRequest:
    return RefundRequest(
        merchant_id="MERCHANT_123",
        order_id="orbit-uuid-123",
        psp_payment_id="cf_pmt_xyz",              # the successful attempt's PSP id
        refund_id="orbit-refund-1",               # Orbit's id, NOT psp_refund_id
        amount_to_refund=50000,                   # int minor units, NOT `amount=`, NOT Amount
        reason="customer-cancel",
    )


def _sync_refund_request() -> SyncRefundRequest:
    return SyncRefundRequest(
        merchant_id="MERCHANT_123",
        order_id="orbit-uuid-123",
        psp_refund_id="cf_refund_qrs",            # the PSP-side refund id — that's the ONLY refund kwarg here
        # NOT `refund_id=` (that's Orbit's id, on RefundRequest)
        # NOT `psp_order_id=` (this request doesn't take it)
    )
```

Notes the past failure modes:

- `ConnectorConfig(credentials=..., merchant_id=...)` — wrong on TWO counts. Flat fields, no merchant_id.
- `SyncRefundRequest(psp_order_id=..., refund_id=...)` — both kwargs are wrong; only `psp_refund_id`.
- Missing `merchant_id=` / `order_id=` on any of the four requests — they're required by `RequestCommon`.
- Tests asserting `event.payment_attempt` or `event.refund_event` — the fields are `event.attempt` and `event.refund`.

(Yes — touching `_client` from the outside is intentional for tests. Production code uses the real httpx client. A cleaner injection seam is fine if the connector exposes one.)

## Test correctness: five patterns that have failed before

These are the EXACT failure modes from the last cashfree generation (10 of 12 tests
failed). Every one is a test-side bug — the connector code was fine but the test
asserted the wrong thing or set up the mock wrong. Get all five right and the
gates pass.

### 1. Mock-transport path assertions must include the `base_url` prefix

Cashfree's `base_url` is `https://sandbox.cashfree.com/pg`. When the connector
calls `self._client.post("/orders", ...)`, the request `url.path` is
**`/pg/orders`**, not `/orders`. Same for every other endpoint.

```python
# WRONG — strips the /pg prefix:
def handler(request: httpx.Request) -> httpx.Response:
    assert request.url.path == "/orders"                        # AssertionError: '/pg/orders' != '/orders'
```

```python
# CORRECT — match against the suffix, or include the prefix:
def handler(request: httpx.Request) -> httpx.Response:
    assert request.url.path.endswith("/orders")                  # robust to base_url
    # or, explicitly:
    assert request.url.path == "/pg/orders"
```

The general pattern: in tests, use `.endswith(...)` on path or method-+-path
together. Never assume the path equals just the path the connector source code
passed to `self._client`.

### 2. `_map_http_error` must differentiate 4xx from 5xx

Tests for `*_400_error` paths assert `ConnectorErrorReason.INVALID_REQUEST`, but
generic error handlers tend to map everything to `PSP_UNAVAILABLE`. Be explicit:

```python
# CORRECT _map_http_error in connector.py:
def _map_http_error(e: httpx.HTTPStatusError) -> ConnectorError:
    status = e.response.status_code
    if status == 400 or status == 422:
        return ConnectorError(reason=ConnectorErrorReason.INVALID_REQUEST, psp_code=str(status))
    if status == 401:
        return ConnectorError(reason=ConnectorErrorReason.AUTHENTICATION_FAILED, psp_code=str(status))
    if status == 403:
        return ConnectorError(reason=ConnectorErrorReason.AUTHORIZATION_FAILED, psp_code=str(status))
    if status == 404:
        return ConnectorError(reason=ConnectorErrorReason.ORDER_NOT_FOUND, psp_code=str(status))
    if status == 409:
        return ConnectorError(reason=ConnectorErrorReason.INVALID_ORDER_STATE, psp_code=str(status))
    if status == 429:
        return ConnectorError(reason=ConnectorErrorReason.RATE_LIMITED, psp_code=str(status))
    if 500 <= status < 600:
        return ConnectorError(reason=ConnectorErrorReason.PSP_UNAVAILABLE, psp_code=str(status))
    return ConnectorError(reason=ConnectorErrorReason.PSP_ERROR, psp_code=str(status))
```

### 3. `sync_payment` test handler must respond to BOTH endpoints

`sync_payment` typically hits `/orders/{id}` (order envelope) AND
`/orders/{id}/payments` (attempts list). A handler that only returns 200 for
the first endpoint gets a 404 on the second, the connector raises
`ORDER_NOT_FOUND` from `raise_for_status`, and the test fails.

```python
# WRONG — single 200 for any request:
def handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"order_status": "PAID"})    # second GET hits this with no /payments data
```

```python
# CORRECT — branch on path:
def handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/payments"):
        return httpx.Response(200, json=[{"cf_payment_id": "918812", "payment_status": "SUCCESS", ...}])
    # the order endpoint
    return httpx.Response(200, json={"cf_order_id": "abc", "order_status": "PAID", ...})
```

### 4. Webhook test fixtures must sign payloads the same way the connector verifies

The cashfree HMAC algorithm is HMAC-SHA256 over `timestamp + "." + body`, base64-encoded
(check the PSP's docs for the exact recipe). The test fixture MUST use the same
algorithm + the same secret to build a valid signature, otherwise the connector's
`verify_signature` will reject it as tampered.

```python
# CORRECT webhook test signing — mirror auth.py's verify exactly:
import base64, hashlib, hmac, json

def _sign_cashfree(secret: str, timestamp: str, payload: bytes) -> str:
    msg = (timestamp + payload.decode("utf-8")).encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")

async def test_webhook_payment_success() -> None:
    payload = json.dumps({"type": "PAYMENT_SUCCESS_WEBHOOK", ...}).encode("utf-8")
    timestamp = "1700000000"
    sig = _sign_cashfree("test_webhook", timestamp, payload)
    connector = _build_connector(lambda r: httpx.Response(200))
    event = await connector.handle_webhook(payload, {
        "x-webhook-timestamp": timestamp,
        "x-webhook-signature": sig,
    })
    assert event.event_type == WebhookEventType.PAYMENT_SUCCESS
```

The fixture's `webhook_secret=Maskable("test_webhook")` must match the secret
the signing helper uses.

### 5. Assertions must check mock-RESPONSE values, not request-INPUT values

```python
# WRONG — asserting the input ID, which the connector echoes back:
async def test_sync_refund_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"cf_refund_id": "1553338", "refund_status": "SUCCESS", ...})
    connector = _build_connector(httpx.MockTransport(handler))
    resp = await connector.sync_refund(_sync_refund_request())   # request.psp_refund_id == "cf_refund_qrs"
    assert resp.psp_refund_id == "cf_refund_qrs"                  # ← WRONG: that was the input
```

```python
# CORRECT — assert against what the PSP returned (the mock body):
    assert resp.psp_refund_id == "1553338"                         # matches handler's cf_refund_id
```

The connector returns the PSP-side id from the response body. The input `psp_refund_id`
on the request is just "which refund to look up"; the response is "what the PSP says
about that refund". They are different IDs in this test pattern.

### 6. Mock-response JSON must satisfy your own Pydantic wire models

The connector parses the mock's response JSON via Pydantic models in `models.py`. Those models default to `extra="forbid"` and every field declared without a default is **required**. If the test handler returns a response body missing those fields, Pydantic raises `ValidationError` inside the connector method, and the test fails with a long traceback like:

```
pydantic_core._pydantic_core.ValidationError: 2 validation errors for CashfreeCreateOrderResponse
  payment_session_id: Field required
  cf_order_id: Field required
```

```python
# WRONG — mock body missing required Cashfree response fields:
def handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"order_status": "ACTIVE"})    # missing 5 required fields
```

```python
# CORRECT — every required field on the wire model is present:
def handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={
        "cf_order_id": "2149460581",
        "order_id": "orbit-uuid-123",
        "order_status": "ACTIVE",
        "order_amount": 500.0,
        "order_currency": "INR",
        "payment_session_id": "session_abc123",
        "order_expiry_time": "2026-06-01T12:00:00+05:30",
    })
```

When writing the test, copy the response shape from the PSP's example response in the docs (or your own wire model's field list) into the mock JSON. Don't free-hand a minimal subset.

### 7. One payment wire model, two contexts

Cashfree (and most PSPs) return the same payment shape on `/orders/{id}/payments` (sync_payment) and inside webhook payloads (`data.payment`). Modeling these as two SEPARATE Pydantic classes (`CashfreePayment` and `CashfreeWebhookPayment`) means a helper like `_payment_to_attempt(p: CashfreePayment)` can't be reused from `handle_webhook` — mypy flags `incompatible type`.

```python
# WRONG — two parallel models for the same wire shape, helper is monomorphic:
class CashfreePayment(BaseModel):
    cf_payment_id: int
    payment_status: str
    payment_amount: float
    ...

class CashfreeWebhookPayment(BaseModel):    # same fields, different class
    cf_payment_id: int
    payment_status: str
    payment_amount: float
    ...

def _payment_to_attempt(p: CashfreePayment) -> PaymentAttempt: ...

# In handle_webhook:
attempt = _payment_to_attempt(psp_event.data.payment)   # CashfreeWebhookPayment — type error
```

```python
# CORRECT — single CashfreePayment, both sync_payment AND the webhook payload nest it:
class CashfreePayment(BaseModel):
    cf_payment_id: int
    payment_status: str
    ...

class CashfreeWebhookData(BaseModel):
    payment: CashfreePayment | None = None
    order: CashfreeOrder | None = None
    refund: CashfreeRefund | None = None

class CashfreeWebhookPayload(BaseModel):
    type: str
    event_id: str
    data: CashfreeWebhookData
```

Reuse the single payment model across contexts unless the PSP genuinely returns different shapes (rare). The same principle applies to refunds (`CashfreeRefund` covers sync_refund + webhook `data.refund`).

### 8. Tampering tests must actually mutate the payload bytes

The webhook tamper test is meant to confirm `verify_signature` rejects bodies that differ from what was signed. If the "tampered" bytes are byte-identical to the original, the HMAC still matches and the test fails with `DID NOT RAISE`.

```python
# WRONG — JSON always ends with `}`, so this is a no-op. payload == tampered.
payload = json.dumps(_payment_success_payload()).encode("utf-8")
sig = _sign(_WEBHOOK_SECRET, timestamp, payload)
tampered = payload[:-1] + b"}"                                   # ← no change
with pytest.raises(ConnectorError):                              # ← DID NOT RAISE
    await connector.handle_webhook(tampered, {...})
```

```python
# WRONG (also). `payload + b" "` keeps the original bytes intact at the
# front; some PSP verifiers strip trailing whitespace before HMAC-ing, so
# the signature can still validate.
tampered = payload + b" "
```

The safe pattern: flip a byte **inside** the JSON body where the change is unambiguous and survives any whitespace normalization.

```python
# CORRECT — replace a value-substring with something the verifier cannot
# explain away. Pick a literal you put into _payment_success_payload()
# yourself so the swap is deterministic.
tampered = payload.replace(b'"SUCCESS"', b'"FAILED"')
assert tampered != payload, "tampering must actually change the bytes"

with pytest.raises(ConnectorError) as exc_info:
    await connector.handle_webhook(tampered, {
        "x-webhook-timestamp": timestamp,
        "x-webhook-signature": sig,                              # signature of ORIGINAL payload
    })
assert exc_info.value.reason == ConnectorErrorReason.WEBHOOK_SIGNATURE_FAILED
```

Always include the `assert tampered != payload` guard. It catches the no-op mutation at the source instead of letting it masquerade as a flaky test.

## Coverage discipline

The 80% line-coverage gate fails when defensive branches go untested. The required cases above were chosen so that the most common gap-creators (HTTP error mapping, network errors, unknown PSP enum values, Pydantic ValidationError on response parsing, webhook fallback) each get at least one test. With those in place a typical 4-flow connector lands at ≥80% without needing further coverage padding.

A few extra disciplines on top:

- `status_map.py`: one parametrized test exercising every entry in your status-map dict, plus the `UNKNOWN`/fallback branch when the input is not present. These are pure functions — the test is cheap and pays for itself in coverage.
- `auth.py`: signing and verification helpers each get a direct unit test (correct-signature → True, tampered-signature → False, missing-headers → False). The webhook-handler test in `test_webhook.py` covers the integration path; `auth.py` tests cover the helper in isolation.
- Don't write code you don't intend to test. If a defensive branch isn't reachable in practice (e.g., a `else: assert False, "unreachable"` after an exhaustive enum match), don't emit it — it just sits in the test gap. Use a real enum match or `typing.assert_never` instead.

The combined effect is that the test suite mirrors the structure of `connector.py`: every public method has at least one error-path test, every helper has a direct test, and every fallback branch in the `_map_*` family is reached at least once.
