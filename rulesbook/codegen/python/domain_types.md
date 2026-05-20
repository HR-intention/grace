# Domain types (locked)

These types live in `lens.domain_types` and `lens.enums`. **Import them; do not redefine them. Never widen an enum locally.** Verbatim from `SUBPROJECT_LENS.md` §4.4 + §4.6.

## Request/response models

```python
# lens/domain_types/__init__.py

# Money.
class Amount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    minor_units: int
    currency: Currency

# Shared request fields used by every flow.
class RequestCommon(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    merchant_id: str
    order_id: str                                  # Orbit's order id (UUID)
    customer_id: str | None = None
    idempotency_key: str | None = None


# create_order
class CreateOrderRequest(RequestCommon):
    amount: Amount
    return_url: HttpUrl
    allowed_methods: list[PaymentMethod] | None = None
    expires_at: datetime | None = None             # PSP-side TTL
    metadata: dict[str, str] = Field(default_factory=dict)

class CreateOrderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)
    psp_order_id: str
    payment_link: HttpUrl
    status: OrderStatus                            # typically OrderStatus.CREATED
    expires_at: datetime | None = None


# Per-attempt model — returned in lists by sync_payment, individually by webhooks.
class PaymentAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    psp_payment_id: str
    status: PaymentAttemptStatus                   # PENDING | SUCCESS | FAILED
    method_used: PaymentMethod | None = None       # populated post-attempt
    amount: Amount | None = None                   # PSP may not report until SUCCESS
    failure_code: PaymentFailureCode | None = None # populated on FAILED (or PENDING-in-review)
    failure_reason: str | None = None              # human-readable; PSP raw text
    attempted_at: datetime                         # PSP-reported timestamp
    raw: dict[str, Any] = Field(default_factory=dict)


# sync_payment
class SyncPaymentRequest(RequestCommon):
    psp_order_id: str

class SyncPaymentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)
    psp_order_id: str
    status: OrderStatus                            # the order's overall status
    paid_amount: int | None = None                 # populated when at least one attempt succeeded
    attempts: list[PaymentAttempt] = Field(default_factory=list)


# refund
class RefundRequest(RequestCommon):
    psp_payment_id: str                            # the successful attempt to refund against
    refund_id: str                                 # Orbit's refund id
    amount_to_refund: int | None = None            # None ⇒ full
    reason: str | None = None

class RefundResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)
    psp_refund_id: str
    status: RefundStatus
    refunded_amount: int | None = None


# sync_refund
class SyncRefundRequest(RequestCommon):
    psp_refund_id: str

class SyncRefundResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)
    psp_refund_id: str
    status: RefundStatus
    refunded_amount: int | None = None
    failure_reason: str | None = None


# Refund-side event for webhooks.
class RefundEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    psp_refund_id: str
    psp_payment_id: str                            # which attempt was refunded
    psp_order_id: str | None = None
    status: RefundStatus
    refunded_amount: int | None = None
    failure_reason: str | None = None


# Webhook — one event from the PSP, normalized.
class WebhookEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    event_type: WebhookEventType
    psp_event_id: str                              # for dedup (Orbit-side)
    psp_order_id: str | None = None
    attempt: PaymentAttempt | None = None          # populated for PAYMENT_* events
    refund:  RefundEvent     | None = None         # populated for REFUND_* events
    raw_payload: dict[str, Any]
```

## Enums (all locked, additive-only)

```python
# lens/enums/__init__.py

class Currency(StrEnum):
    INR = "INR"; USD = "USD"; EUR = "EUR"; GBP = "GBP"
    # additive

class PaymentMethod(StrEnum):
    CARD = "CARD"
    UPI = "UPI"
    WALLET = "WALLET"
    BANK_TRANSFER = "BANK_TRANSFER"
    BANK_REDIRECT = "BANK_REDIRECT"

class OrderStatus(StrEnum):
    CREATED = "CREATED"
    PAID = "PAID"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    REFUNDED = "REFUNDED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"

class PaymentAttemptStatus(StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class RefundStatus(StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class PaymentFailureCode(StrEnum):
    USER_DROPPED = "USER_DROPPED"
    USER_CANCELLED = "USER_CANCELLED"
    CARD_DECLINED = "CARD_DECLINED"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    FRAUD_BLOCKED = "FRAUD_BLOCKED"
    FRAUD_REVIEW_PENDING = "FRAUD_REVIEW_PENDING"   # status=PENDING during review
    INVALID_INSTRUMENT = "INVALID_INSTRUMENT"
    PSP_ERROR = "PSP_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN = "UNKNOWN"

class WebhookEventType(StrEnum):
    PAYMENT_INITIATED = "PAYMENT_INITIATED"        # rare; some PSPs emit pending events
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    ORDER_EXPIRED = "ORDER_EXPIRED"
    REFUND_SUCCESS = "REFUND_SUCCESS"
    REFUND_FAILED = "REFUND_FAILED"

class ConnectorErrorReason(StrEnum):
    INVALID_REQUEST = "INVALID_REQUEST"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    PSP_UNAVAILABLE = "PSP_UNAVAILABLE"
    PSP_TIMEOUT = "PSP_TIMEOUT"
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    PAYMENT_NOT_FOUND = "PAYMENT_NOT_FOUND"
    REFUND_NOT_FOUND = "REFUND_NOT_FOUND"
    INVALID_ORDER_STATE = "INVALID_ORDER_STATE"
    WEBHOOK_SIGNATURE_FAILED = "WEBHOOK_SIGNATURE_FAILED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    INCOMPATIBLE_VERSION = "INCOMPATIBLE_VERSION"
    INTERNAL = "INTERNAL"
```

## Common types

```python
# lens/common/__init__.py

T = TypeVar("T")
class Maskable(Generic[T]):
    def __init__(self, value: T): ...
    def expose(self) -> T: ...
    def __repr__(self) -> str: return "***"
    def __str__(self) -> str: return "***"


class ConnectorError(Exception):
    def __init__(
        self,
        reason: ConnectorErrorReason,
        *,
        psp_code: str | None = None,
        psp_message: str | None = None,
    ): ...
```

## Rules

- **All money fields on the public surface are integer minor units.** `amount.minor_units` is an `int`. `paid_amount`, `refunded_amount`, `amount_to_refund` are `int`. PSP wire-level transformations may use `decimal.Decimal` inside the connector method, but Decimal never crosses back into a domain type. (Ground rule 10.)
- **No `Any` in domain payloads** — the `raw` and `raw_payload` `dict[str, Any]` fields are the only exceptions, kept for debug/replay only.
- **`extra="forbid"` everywhere** so unexpected wire-level fields fail validation at the boundary.
- **`PaymentMethod` is an allow-list constraint**, not a per-method request builder. v1 hosted-checkout never sees raw card/UPI/wallet payloads.
