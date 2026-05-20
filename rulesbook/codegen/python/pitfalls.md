# Common pitfalls (read first, re-read at the end)

Every deviation listed here costs rubric points. The fixes are concrete and unambiguous — there is no PSP for which the *wrong* version is correct.

## 1. Class naming

| ✗ Wrong | ✓ Right |
|---|---|
| `class CashfreeConnector(Connector)` | `class Cashfree(Connector)` |
| `class CashfreeClient(Connector)` | `class Cashfree(Connector)` |
| `class CashfreePaymentConnector(Connector)` | `class Cashfree(Connector)` |

The class name is the PSP name in PascalCase, **no suffix**. The registry key (the first arg to `ConnectorFactory.register`) is the same string in lowercase. The rubric's public-surface scorer does a case-insensitive name match against the PSP name — `connector.py: no class named <psp>` is a 4-point dock per missing element.

## 1b. The four abstract `@property`s

`Connector` has four abstract `@property` declarations on top of the six async methods. **All ten must be present**, or `ConnectorFactory.register(...)` raises at import time with:

```
Can't instantiate abstract class Cashfree without an implementation for abstract methods
  'base_url', 'name', 'supported_methods', 'supports_idempotency_key'
```

and your tests can't even collect — `test_coverage` lands at 0/25.

```python
# CORRECT shape — properties FIRST, then __init__, then async methods.
class Cashfree(Connector):
    @property
    def name(self) -> str:
        return "cashfree"

    @property
    def base_url(self) -> str:
        return "https://sandbox.cashfree.com/pg"

    @property
    def supported_methods(self) -> set[PaymentMethod]:
        return {PaymentMethod.CARD, PaymentMethod.UPI}

    @property
    def supports_idempotency_key(self) -> bool:
        return True

    def __init__(self, config: ConnectorConfig) -> None: ...

    async def create_order(self, request: CreateOrderRequest) -> CreateOrderResponse: ...
    # ... and the other four async methods
```

```python
# WRONG — properties missing. Class is concrete by line count but
# abstract by Python; instantiation fails.
class Cashfree(Connector):
    def __init__(self, config: ConnectorConfig) -> None: ...

    async def create_order(self, request): ...
    # ... no @property at all
```

## 2. Import paths

| ✗ Wrong | ✓ Right |
|---|---|
| `from lens.connector_abc import Connector` | `from lens.connector import Connector` |
| `from lens.types import ...` | `from lens.domain_types import ...` |
| `from lens.models import ...` | `from lens.domain_types import ...` |
| `from lens.errors import ConnectorError` | `from lens.common import ConnectorError` |
| `from lens.domain_types import Money` | `from lens.domain_types import Amount` |

There is **no `Money` type**. Money is represented by `Amount(minor_units: int, currency: Currency)` — int minor units only (ground rule 10).

## 3. Sync vs async

| ✗ Wrong | ✓ Right |
|---|---|
| `def create_order(self, request): ...` | `async def create_order(self, request): ...` |
| `httpx.Client(...)` | `httpx.AsyncClient(...)` |
| `self._client.post(...)` | `await self._client.post(...)` |
| (in tests) `def test_create_order():` | `async def test_create_order():` |

Every public method on `Connector` is `async def`. Ground rule 3. Tests use `pytest-asyncio` with `asyncio_mode = "auto"`, so a top-level `async def test_*` runs as a coroutine.

## 4. Request field access

The locked `CreateOrderRequest` (and siblings) have a **flat** field set inherited from `RequestCommon`. There is no nested `customer` object.

| ✗ Wrong | ✓ Right |
|---|---|
| `request.customer.id` | `request.customer_id` |
| `request.customer.email` | (not on the domain request — PSPs that need email read it from `metadata` or just omit) |
| `request.amount.value` | `request.amount.minor_units` |
| `float(request.amount.value)` | `Decimal(request.amount.minor_units) / 100` (only inside the wire-level builder, never crossing back out) |

If the PSP requires a customer email/phone/name and the domain request doesn't carry it, **pass a placeholder or omit the field** — do NOT invent additional request fields. Orbit owns the customer record.

## 4a. Field-name reference (LOCKED — verify every kwarg against this table)

Every single one of these has been gotten wrong in past generations. The Pydantic models are `extra="forbid"`, so any deviation crashes at construction time with `[call-arg]` or `[attr-defined]` mypy errors.

### `ConnectorConfig` (`lens.factory`)

```python
class ConnectorConfig(BaseModel):
    name: str
    api_key: Maskable[str]
    secret_key: Maskable[str] | None = None
    webhook_secret: Maskable[str] | None = None
    base_url_override: HttpUrl | None = None
    additional: dict[str, Any] = Field(default_factory=dict)
```

| ✗ Don't write | ✓ Write |
|---|---|
| `config.credentials` (no such attribute) | `config.api_key.expose()` |
| `config.merchant_id` (lives on request, not config) | `request.merchant_id` |
| `ConnectorConfig(credentials=...)` | `ConnectorConfig(name="cashfree", api_key=Maskable("..."), secret_key=Maskable("..."))` |
| `ConnectorConfig(merchant_id=...)` | merchant_id is **never** on ConnectorConfig. It comes from the request. |
| `ConnectorConfig(client_id=..., client_secret=...)` | `api_key=Maskable(client_id), secret_key=Maskable(client_secret)` |

### `RequestCommon` (the base of every request)

```python
class RequestCommon(BaseModel):
    merchant_id: str            # REQUIRED
    order_id: str               # REQUIRED — Orbit's UUID
    customer_id: str | None = None
    idempotency_key: str | None = None
```

Every concrete request inherits these four. **`merchant_id` and `order_id` are required** — tests that omit them fail with `Missing named argument` at mypy time and `ValidationError` at runtime.

### `CreateOrderRequest`

```python
class CreateOrderRequest(RequestCommon):
    amount: Amount
    return_url: HttpUrl          # REQUIRED
    allowed_methods: list[PaymentMethod] | None = None
    expires_at: datetime | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
```

| ✗ Don't write | ✓ Write |
|---|---|
| `request.amount.value` | `request.amount.minor_units: int` |
| `request.customer.email` | `request.customer_id: str \| None` (no nested customer) |
| `CreateOrderRequest(amount=500, currency="INR")` | `CreateOrderRequest(amount=Amount(minor_units=500, currency=Currency.INR), ...)` |

### `CreateOrderResponse`

```python
class CreateOrderResponse(BaseModel):
    psp_order_id: str
    payment_link: HttpUrl         # NOT str — coerce via HttpUrl(str_value)
    status: OrderStatus
    expires_at: datetime | None = None
```

| ✗ Don't write | ✓ Write |
|---|---|
| `CreateOrderResponse(order_id=...)` | `psp_order_id=...` |
| `CreateOrderResponse(connector_order_id=...)` | `psp_order_id=...` |
| `CreateOrderResponse(payment_link="https://...")` | `payment_link=HttpUrl("https://...")` (or use a typed Pydantic source) |
| `CreateOrderResponse(raw={...})` | `raw` lives on `PaymentAttempt` and `raw_payload` on `WebhookEvent`, **nowhere else** |

### `SyncPaymentRequest`

```python
class SyncPaymentRequest(RequestCommon):
    psp_order_id: str
```

### `SyncPaymentResponse`

```python
class SyncPaymentResponse(BaseModel):
    psp_order_id: str
    status: OrderStatus
    paid_amount: int | None = None     # MINOR UNITS, not Amount
    attempts: list[PaymentAttempt] = Field(default_factory=list)
```

| ✗ Don't write | ✓ Write |
|---|---|
| `SyncPaymentResponse(paid_amount=Amount(...))` | `paid_amount=attempt.amount.minor_units` (an `int`) |
| `SyncPaymentResponse(payment_attempts=[...])` | `attempts=[...]` |

### `PaymentAttempt`

```python
class PaymentAttempt(BaseModel):
    psp_payment_id: str
    status: PaymentAttemptStatus
    method_used: PaymentMethod | None = None
    amount: Amount | None = None        # Amount here, but ONLY here
    failure_code: PaymentFailureCode | None = None
    failure_reason: str | None = None
    attempted_at: datetime              # REQUIRED, non-optional
    raw: dict[str, Any] = Field(default_factory=dict)
```

| ✗ Don't write | ✓ Write |
|---|---|
| `PaymentAttempt(attempted_at=psp_value or None)` | `attempted_at` is required — provide a real datetime, never None |
| `PaymentAttempt(payment_method=...)` | `method_used=...` |
| `PaymentAttempt(failure=...)` | `failure_code=PaymentFailureCode.X` + `failure_reason="..."` |

### `RefundRequest`

```python
class RefundRequest(RequestCommon):
    psp_payment_id: str
    refund_id: str                # Orbit's refund id (NOT PSP's)
    amount_to_refund: int | None = None
    reason: str | None = None
```

| ✗ Don't write | ✓ Write |
|---|---|
| `request.amount` (no such field) | `request.amount_to_refund: int \| None` |
| `request.refund_amount` | `request.amount_to_refund` |
| `RefundRequest(psp_refund_id=...)` | `RefundRequest(refund_id=...)` — psp_refund_id is on RESPONSE, not REQUEST |

### `RefundResponse`

```python
class RefundResponse(BaseModel):
    psp_refund_id: str
    status: RefundStatus
    refunded_amount: int | None = None    # MINOR UNITS, not Amount
```

| ✗ Don't write | ✓ Write |
|---|---|
| `RefundResponse(refunded_amount=Amount(...))` | `refunded_amount=int_value_in_minor_units` |

### `SyncRefundRequest`

```python
class SyncRefundRequest(RequestCommon):
    psp_refund_id: str            # PSP's refund id, NOT Orbit's
```

| ✗ Don't write | ✓ Write |
|---|---|
| `SyncRefundRequest(refund_id=...)` | `SyncRefundRequest(psp_refund_id=...)` |
| `SyncRefundRequest(psp_order_id=...)` | no such field — this request takes only the refund id + RequestCommon |

### `SyncRefundResponse`

```python
class SyncRefundResponse(BaseModel):
    psp_refund_id: str
    status: RefundStatus
    refunded_amount: int | None = None    # MINOR UNITS, not Amount
    failure_reason: str | None = None
```

### `RefundEvent` (lives inside WebhookEvent.refund)

```python
class RefundEvent(BaseModel):
    psp_refund_id: str             # REQUIRED
    psp_payment_id: str             # REQUIRED — easy to forget; refund hangs off a payment
    psp_order_id: str | None = None
    status: RefundStatus
    refunded_amount: int | None = None    # MINOR UNITS
    failure_reason: str | None = None
```

| ✗ Don't write | ✓ Write |
|---|---|
| `RefundEvent(...)` without `psp_payment_id` | both `psp_refund_id` AND `psp_payment_id` are required |

### `WebhookEvent`

```python
class WebhookEvent(BaseModel):
    event_type: WebhookEventType
    psp_event_id: str
    psp_order_id: str | None = None
    attempt: PaymentAttempt | None = None          # ← "attempt" not "payment_attempt"
    refund:  RefundEvent     | None = None         # ← "refund"  not "refund_event"
    raw_payload: dict[str, Any]
```

| ✗ Don't write | ✓ Write |
|---|---|
| `WebhookEvent(payment_attempt=...)` | `WebhookEvent(attempt=...)` |
| `WebhookEvent(refund_event=...)` | `WebhookEvent(refund=...)` |
| `event.payment_attempt` (in tests) | `event.attempt` |
| `event.refund_event` (in tests) | `event.refund` |

## 4b. Response field names are locked

Every domain response model has `extra="forbid"` — passing a keyword arg the model doesn't declare raises a Pydantic `ValidationError` and mypy will refuse to compile because it's `[call-arg]`. Don't invent fields.

```python
# CORRECT — exactly the locked fields:
return CreateOrderResponse(
    psp_order_id=psp_resp.cf_order_id,
    payment_link=psp_resp.payment_link,
    status=OrderStatus.CREATED,
    expires_at=psp_resp.order_expiry_time,
)
```

```python
# WRONG — `order_id`, `connector_order_id`, `raw` are not on CreateOrderResponse:
return CreateOrderResponse(
    order_id=...,                  # ← no such field; mypy [attr-defined]
    connector_order_id=...,        # ← invented
    raw={...},                     # ← not on the response (raw lives on PaymentAttempt only)
)
```

Same applies to `RefundResponse`, `SyncPaymentResponse`, `SyncRefundResponse`. The locked fields are listed in `domain_types.md` — paste-from-spec, don't paraphrase.

`raw: dict[str, Any]` exists on `PaymentAttempt` (for debug/replay), and `raw_payload` on `WebhookEvent`. Those are the ONLY two places. Do not add it to other responses.

## 5. `__init__.py` self-registration

The generated `__init__.py` must declare the Lens version constraint **and** register the class with the factory:

```python
# CORRECT:
requires_lens = "^0.1"

from .connector import Cashfree
from lens.factory import ConnectorFactory
ConnectorFactory.register("cashfree", Cashfree)
```

```python
# WRONG — common mistake: only an __all__ export, no registration:
from .connector import Cashfree
__all__ = ["Cashfree"]
```

The rubric's public-surface scorer greps for both literal strings; the second style scores 8/20 instead of 20/20.

## 6. Credentials in `auth.py`

```python
# CORRECT:
from lens.common import Maskable
from lens.factory import ConnectorConfig

def build_auth_headers(config: ConnectorConfig) -> dict[str, str]:
    return {
        "x-client-id": config.api_key.expose(),
        "x-client-secret": config.secret_key.expose() if config.secret_key else "",
    }
```

```python
# WRONG — bare strings, no Maskable, custom config dataclass:
@dataclass(frozen=True)
class CashfreeConfig:
    client_id: str            # ← no Maskable
    client_secret: str        # ← no Maskable
```

**Do not define a `<Psp>Config` dataclass.** The credentials shape is `lens.factory.ConnectorConfig` (api_key, secret_key, webhook_secret, base_url_override, additional). Auth helpers take that and produce headers.

## 7. Webhook signature failure

```python
# CORRECT:
from lens.common import ConnectorError
from lens.enums import ConnectorErrorReason

async def handle_webhook(self, raw_payload: bytes, headers: dict[str, str]) -> WebhookEvent:
    if not verify_signature(self._config, raw_payload, headers):
        raise ConnectorError(reason=ConnectorErrorReason.WEBHOOK_SIGNATURE_FAILED)
    ...
```

```python
# WRONG — bare exception, untyped, undiscoverable by callers:
if not verify_signature(...):
    raise ValueError("signature verification failed")
```

The rubric's error-handling scorer greps for `WEBHOOK_SIGNATURE_FAILED` and for `ConnectorError`. Both must appear in `connector.py`.

## 8. Status enum values (LOCKED — only these exist)

`PaymentAttemptStatus`: `PENDING`, `SUCCESS`, `FAILED` — three values, **nothing else**.

| ✗ Invented values | ✓ Locked equivalent |
|---|---|
| `PaymentAttemptStatus.CAPTURED` | `PaymentAttemptStatus.SUCCESS` |
| `PaymentAttemptStatus.AUTHORIZED` | `PaymentAttemptStatus.SUCCESS` (for hosted checkout — capture happens at the PSP) |
| `PaymentAttemptStatus.CANCELLED` | `PaymentAttemptStatus.FAILED` + `PaymentFailureCode.USER_CANCELLED` |
| `PaymentAttemptStatus.VOID` | `PaymentAttemptStatus.FAILED` + `PaymentFailureCode.USER_CANCELLED` (or `UNKNOWN`) |
| `PaymentAttemptStatus.REJECTED` | `PaymentAttemptStatus.FAILED` + `PaymentFailureCode.CARD_DECLINED` |

`PaymentFailureCode` values (the only ones that exist):
`USER_DROPPED`, `USER_CANCELLED`, `CARD_DECLINED`, `INSUFFICIENT_FUNDS`, `AUTHENTICATION_FAILED`, `FRAUD_BLOCKED`, `FRAUD_REVIEW_PENDING`, `INVALID_INSTRUMENT`, `PSP_ERROR`, `NETWORK_ERROR`, `UNKNOWN`.

| ✗ Invented codes | ✓ Locked equivalent |
|---|---|
| `PAYMENT_DECLINED` | `CARD_DECLINED` |
| `CUSTOMER_CANCELLED` | `USER_CANCELLED` |
| `EXPIRED_CARD` | `INVALID_INSTRUMENT` (or `CARD_DECLINED` per PSP signal) |
| `TIMEOUT` | `NETWORK_ERROR` |
| `INVALID_CARD` | `INVALID_INSTRUMENT` |

If you find yourself wanting a value that's not here, fall back to `UNKNOWN` and capture the PSP-original term in `failure_reason: str`.

## 9. Marker block duplication

Grace prepends the constitution §4 marker to every emitted file. **Do not also write a second marker** like `# Code generated by grace ... DO NOT EDIT.\n# source: lens.connectors.cashfree`. That ends up duplicated and confusing.

The first thing after the marker should be `from __future__ import annotations`, then the module docstring (optional), then imports.

## 10. httpx client

```python
# CORRECT — async client, owned by Connector, closed in close():
def __init__(self, config: ConnectorConfig):
    self._config = config
    self._client = httpx.AsyncClient(
        base_url=str(config.base_url_override) if config.base_url_override else self.base_url,
        timeout=30.0,
    )

async def close(self) -> None:
    await self._client.aclose()
```

```python
# WRONG — sync client + lazy build inside flow methods:
def __init__(self, config):
    self._config = config

def _client(self):
    return httpx.Client(...)   # rebuilt every call, sync, never closed
```

## Final self-check

Before exiting, grep your output for each of these and confirm:

```
grep -E '^class [A-Z][a-z]+\(Connector\)' connector.py        # exactly 1 match
grep 'from lens.connector import Connector' connector.py       # present
grep 'ConnectorFactory.register' __init__.py                   # present
grep 'requires_lens' __init__.py                                # present
grep -c 'async def' connector.py                                # >= 6
grep 'Maskable' auth.py                                         # >= 1
grep 'WEBHOOK_SIGNATURE_FAILED' connector.py                    # >= 1
grep -E 'Money|float\(' connector.py models.py                  # 0 matches
grep -E 'PaymentAttemptStatus\.(CAPTURED|AUTHORIZED|CANCELLED|VOID|REJECTED)' status_map.py   # 0 matches
grep -E 'PaymentFailureCode\.(PAYMENT_DECLINED|CUSTOMER_CANCELLED|EXPIRED_CARD|TIMEOUT)' status_map.py  # 0 matches
```

If any of these don't match the expected count, fix before writing the file out.
