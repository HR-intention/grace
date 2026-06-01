# Domain types (locked)

These types live in `lens.domain_types` and `lens.enums`. **Import them; do not redefine
them. Never widen an enum locally.** Lens 0.2.0 adds mandate types alongside the existing
payment types.

---

## Payment types (`lens.domain_types`)

```python
from lens.domain_types import (
    Amount,
    RequestCommon,
    CreateOrderRequest, CreateOrderResponse,
    PaymentAttempt,
    SyncPaymentRequest, SyncPaymentResponse,
    RefundRequest, RefundResponse,
    SyncRefundRequest, SyncRefundResponse,
    RefundEvent,
    PaymentWebhookEvent,
)
```

All payment request/response models have `extra="forbid"` — incorrect kwargs raise a
`ValidationError` at runtime. **Exact field inventory** (do not guess; wrong names cause
`AttributeError` on access or `ValidationError` on construction):

```
CreateOrderRequest:  merchant_id, order_id, customer_id, idempotency_key,
                     amount, return_url, allowed_methods, expires_at, metadata

SyncPaymentRequest:  merchant_id, order_id, customer_id, idempotency_key,
                     psp_order_id        ← ONLY THIS TYPE carries psp_order_id

RefundRequest:       merchant_id, order_id, customer_id, idempotency_key,
                     psp_payment_id, refund_id, amount_to_refund, reason
                     • amount_to_refund: int | None  (None = full refund)
                     • NO psp_order_id — use request.order_id for order-scoped PSP URLs

SyncRefundRequest:   merchant_id, order_id, customer_id, idempotency_key,
                     psp_refund_id
                     • NO psp_order_id — use request.order_id for order-scoped PSP URLs
                     • NO refund_id
```

**Response fields** (locked — no invented extras):

```
CreateOrderResponse:   psp_order_id, payment_link, status, expires_at
SyncPaymentResponse:   psp_order_id, status, paid_amount (int minor-units), attempts
RefundResponse:        psp_refund_id, status, refunded_amount (int minor-units)
SyncRefundResponse:    psp_refund_id, status, refunded_amount (int minor-units), failure_reason
PaymentAttempt:        psp_payment_id, status, method_used, amount (Amount|None),
                       failure_code, failure_reason, attempted_at (required), raw
```

`paid_amount` and `refunded_amount` are **`int` minor-units** (e.g. paise), never `Amount`.
`PaymentAttempt.amount` is `Amount | None` — the only `Amount` on the response side.

### `PaymentWebhookEvent` — exact fields (no more, no less)

```python
class PaymentWebhookEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    event_type: WebhookEventType        # from PAYMENT_* range
    psp_event_id: str
    psp_order_id: str
    attempt: PaymentAttempt | None = None
    refund: RefundEvent | None = None
    raw_payload: dict[str, Any]         # ← `raw_payload` (NOT `raw`, NOT `raw_event`)
```

**Critical field rules:**
- `raw_payload` (NOT `raw`, NOT `raw_event`) — the raw PSP payload dict.
- `occurred_at` does **NOT** exist on `PaymentWebhookEvent` — do not add it.
- Build: `PaymentWebhookEvent(event_type=…, psp_event_id=…, psp_order_id=…, raw_payload=…)`

---

## Mandate types (`lens.domain_types`)

The mandate types are also exported from `lens.domain_types` (re-exported from
`lens.domain_types.mandates`). Never import from `lens.domain_types.mandates` directly.

```python
from lens.domain_types import (
    CustomerContact,
    MandateRequestCommon,
    CreateSubscriptionRequest,
    CreateSubscriptionResponse,
    ApprovalHandle,
    SyncSubscriptionRequest,
    SyncSubscriptionResponse,
    MandateDebitOutcome,
    ManageMandateRequest,
    ManageMandateResponse,
    MandateWebhookEvent,
)
```

### Key mandate request/response shapes

```python
class CustomerContact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    email: str
    phone: str


class MandateRequestCommon(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    merchant_id: str    # NOTE: NO order_id (mandates are not orders)


class CreateSubscriptionRequest(MandateRequestCommon):
    idempotency_key: str           # REQUIRED — forward as PSP idempotency token
    rail: MandateRail
    customer_ref: str
    customer_contact: CustomerContact   # REQUIRED — email + phone both required
    amount: Amount
    max_amount: Amount
    interval_type: MandateIntervalType
    interval_count: int = 1
    first_charge_at: datetime | None = None   # periodic-only: first debit time
    expires_at: datetime
    max_cycles: int | None = None
    description: str
    return_url: HttpUrl
    upi_vpa: Maskable[str] | None = None


class CreateSubscriptionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)
    psp_mandate_ref: str           # PSP's mandate/subscription reference
    status: MandateStatus
    approval: ApprovalHandle       # REDIRECT / UPI_INTENT / UPI_COLLECT / UPI_QR
    raw: dict[str, Any] | None = None


class SyncSubscriptionRequest(MandateRequestCommon):
    psp_mandate_ref: str


class SyncSubscriptionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)
    status: MandateStatus
    next_charge_at: datetime | None = None
    last_debit: MandateDebitOutcome | None = None
    raw: dict[str, Any] | None = None


class ManageMandateRequest(MandateRequestCommon):
    idempotency_key: str           # REQUIRED on all three lifecycle ops
    psp_mandate_ref: str
    reason: str | None = None
    effective_at: datetime | None = None   # resume: schedule activation time


class ManageMandateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)
    status: MandateStatus
    raw: dict[str, Any] | None = None


class MandateDebitOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    psp_debit_id: str
    psp_mandate_ref: str
    status: MandateDebitStatus
    amount: Amount
    failure_code: PaymentFailureCode | None = None
    occurred_at: datetime
    psp_attempt: int | None = None   # retry count for periodic-mode finality


class MandateWebhookEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    event_type: WebhookEventType        # from MANDATE_* range
    psp_mandate_ref: str
    psp_event_id: str
    occurred_at: datetime
    mandate_status: MandateStatus | None = None
    debit: MandateDebitOutcome | None = None
    raw: dict[str, Any]
```

---

## Enums (`lens.enums`)

All enums are locked and additive-only. Import from `lens.enums`; never redefine locally.

```python
from lens.enums import (
    Currency, PaymentMethod, OrderStatus,
    PaymentAttemptStatus, RefundStatus,
    PaymentFailureCode, WebhookEventType,
    ConnectorErrorReason,
    # Mandate-specific:
    MandateRail, MandateStatus, MandateIntervalType, MandateDebitStatus,
    FailureClass, FAILURE_CLASS,
)
```

### `PaymentMethod` — locked members (exact set, do NOT invent others)

```python
class PaymentMethod(StrEnum):
    CARD          = "CARD"
    UPI           = "UPI"
    WALLET        = "WALLET"
    BANK_TRANSFER = "BANK_TRANSFER"
    BANK_REDIRECT = "BANK_REDIRECT"
```

`NET_BANKING`, `EMI`, `PAY_LATER` do **NOT** exist. `mypy --strict` will fail on any unknown
member access.

**PSP method-group → `PaymentMethod` mapping table:**

| PSP group | Use |
|---|---|
| `card`, `credit_card`, `debit_card` | `PaymentMethod.CARD` |
| `upi` | `PaymentMethod.UPI` |
| `wallet` | `PaymentMethod.WALLET` |
| `bank_transfer`, `neft`, `rtgs`, `imps` | `PaymentMethod.BANK_TRANSFER` |
| `net_banking`, `netbanking` | `PaymentMethod.BANK_REDIRECT` |
| `emi`, `paylater`, `buy_now_pay_later` | pick closest locked member or omit |

`supported_methods` must return only locked `PaymentMethod` members. Never fabricate a member.

### Mandate-specific enums (new in lens 0.2.0)

```python
class MandateRail(StrEnum):
    UPI_AUTOPAY = "UPI_AUTOPAY"
    CARD_EMANDATE = "CARD_EMANDATE"

class MandateStatus(StrEnum):
    PENDING_AUTHORIZATION = "PENDING_AUTHORIZATION"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class MandateIntervalType(StrEnum):
    DAY = "DAY"; WEEK = "WEEK"; MONTH = "MONTH"; YEAR = "YEAR"

class MandateDebitStatus(StrEnum):
    PENDING = "PENDING"; SUCCESS = "SUCCESS"; FAILED = "FAILED"

class FailureClass(StrEnum):
    RETRIABLE = "RETRIABLE"
    TERMINAL = "TERMINAL"
```

### `FAILURE_CLASS` — published data, not logic

```python
from lens.enums import FAILURE_CLASS, FailureClass, PaymentFailureCode

# FAILURE_CLASS: Mapping[PaymentFailureCode, FailureClass]
# A frozen mapping published by lens. Import it; never redeclare it.
# The connector sets failure_code only. Orbit reads FAILURE_CLASS[code].
# Lens never branches on FailureClass.
```

`FAILURE_CLASS` maps each `PaymentFailureCode` to `RETRIABLE` or `TERMINAL`. The connector
sets `MandateDebitOutcome.failure_code`; Orbit looks up `FAILURE_CLASS[code]` to decide
charge-failed vs charge-failed-final. See `status_mapping.md` §4 for the methodology.

### Extended `WebhookEventType` (mandate events added)

```python
class WebhookEventType(StrEnum):
    # Payment events (unchanged)
    PAYMENT_INITIATED = "PAYMENT_INITIATED"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    ORDER_EXPIRED = "ORDER_EXPIRED"
    REFUND_SUCCESS = "REFUND_SUCCESS"
    REFUND_FAILED = "REFUND_FAILED"
    # Mandate lifecycle events (new in 0.2.0)
    MANDATE_AUTHORIZED = "MANDATE_AUTHORIZED"
    MANDATE_REJECTED = "MANDATE_REJECTED"
    MANDATE_PAUSED = "MANDATE_PAUSED"
    MANDATE_RESUMED = "MANDATE_RESUMED"
    MANDATE_CANCELLED = "MANDATE_CANCELLED"
    MANDATE_REVOKED = "MANDATE_REVOKED"
    MANDATE_SUSPENDED = "MANDATE_SUSPENDED"
    MANDATE_EXPIRED = "MANDATE_EXPIRED"
    MANDATE_COMPLETED = "MANDATE_COMPLETED"
    MANDATE_DEBIT_SUCCESS = "MANDATE_DEBIT_SUCCESS"
    MANDATE_DEBIT_FAILED = "MANDATE_DEBIT_FAILED"
    MANDATE_DEBIT_NOTIFIED = "MANDATE_DEBIT_NOTIFIED"
    MANDATE_EXPIRING_SOON = "MANDATE_EXPIRING_SOON"
```

### Extended `PaymentFailureCode` (mandate codes added)

```python
# New codes in 0.2.0 (mandate debit failures):
PaymentFailureCode.MANDATE_REVOKED
PaymentFailureCode.MANDATE_PAUSED
PaymentFailureCode.MANDATE_EXPIRED
PaymentFailureCode.MANDATE_NOT_FOUND
PaymentFailureCode.DEBIT_LIMIT_EXCEEDED
```

These new codes are used in `MandateDebitOutcome.failure_code`. The full list is in
`lens.enums` — import from there, never invent new values.

---

## Common types (`lens.common`)

```python
from lens.common import Maskable, ConnectorError, ConnectorErrorReason

class ConnectorError(Exception):
    def __init__(
        self,
        reason: ConnectorErrorReason,
        *,
        psp_code: str | None = None,
        psp_message: str | None = None,
    ): ...
```

`ConnectorErrorReason` is the same set as in 0.1; no new values in 0.2.0.

---

## Rules

- **All money fields on the public surface are integer minor units.** `Amount.minor_units`
  is an `int`. `MandateDebitOutcome.amount` is `Amount`. `Decimal` may be used inside a
  connector method for intermediate arithmetic but must never cross back into a domain type.
- **No `Any` in domain payloads** except the designated `raw` / `raw_payload` / `raw: dict`
  fields kept for debug/replay only.
- **`extra="forbid"` everywhere** — unexpected wire-level fields fail at the boundary.
- **`MandateRequestCommon` has no `order_id`** — mandates are not orders. Every mandate
  request inherits only `merchant_id` (plus its own fields).
- **`idempotency_key` is REQUIRED on `CreateSubscriptionRequest` and `ManageMandateRequest`**
  (cancel/pause/resume). It must be forwarded to the PSP as the idempotency token.
- **`CustomerContact.email` and `.phone` are both required** — PSPs need them for RBI
  pre-debit notifications. Do not omit either.
