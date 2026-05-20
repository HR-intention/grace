# Sub-project: Lens

**Inherits from**: `ORBIT_CONSTITUTION.md`. Conflicts resolve in favor of the constitution.
**Owner**: TBD per implementing agent.
**Location**: `/Users/sarthak/PycharmProjects/references/lens/`
**Status**: v0.4 — Order + PaymentAttempt entity model, simplified statuses, locked failure-code taxonomy.

---

## §1. Purpose & scope

Lens is a stateless Python library that gives Orbit a single, provider-agnostic API for payment service providers (PSPs). It exposes a `PaymentsFacade` (the thing Orbit calls), a `Connector` ABC (the thing each PSP implements), a `ConnectorFactory` (the registry that wires PSP name → Connector class), and the domain types that flow across the boundary — including the **`PaymentAttempt`** model, which represents one individual attempt by a payer against an Order.

Lens **takes inspiration from juspay-prism** for the registry pattern and the discipline of normalized errors. It does **not** mirror juspay-prism's Rust trait generics. One Python class per PSP, four async flow methods.

**In scope for v1**

- Four PSP flows tailored to hosted-checkout: `create_order`, `sync_payment`, `refund`, `sync_refund`. Plus webhook handling (`handle_webhook`) and lifecycle (`close`).
- Hosted-checkout / session-based PSP integration only (constitution §7).
- One PSP: Cashfree.
- The `PaymentAttempt` domain model + three separate status enums (`OrderStatus`, `PaymentAttemptStatus`, `RefundStatus`) + the locked `PaymentFailureCode` taxonomy.

**Out of scope for v1**

- Direct-API / server-to-server flows (`authorize` / `capture` / `void` with raw instrument data). Future-scope design lives in `FUTURE_S2S_INTERFACE.md`.
- A second PSP in production (Razorpay is a Grace-side generation test only).
- Any HTTP/gRPC server exposing Lens externally.
- Persistent state of any kind.
- Promoting `USER_DROPPED` / `CANCELLED` / `FLAGGED` to first-class `PaymentAttemptStatus` values.

---

## §2. Glossary

- **PSP** — Payment Service Provider (Cashfree, Razorpay, Stripe, …).
- **Order** (a.k.a. PaymentRequest) — *entity 1*. The merchant's intent to receive a payment. Created in Orbit; mirrored to the PSP via `create_order`. One PSP order corresponds to 1 Orbit Order. Owns the `payment_link`, the `allowed_methods`, the TTL.
- **PaymentAttempt** (a.k.a. Transaction) — *entity 2*. One specific attempt by the payer against an Order. Created when the PSP signals a payment was initiated. One Order can have 0..N PaymentAttempts. Returned in lists from `sync_payment` and individually inside `WebhookEvent`.
- **Refund** — *entity 3*. A merchant-initiated reversal against the successful PaymentAttempt of an Order. Created via `refund`. Status updates arrive via webhook or `sync_refund`.
- **Flow** — A logical interaction with the PSP. v1 has four flows:
  - **`create_order`** — Tell the PSP to create a hosted-checkout session for this amount and these allowed methods. Returns an `psp_order_id` and a `payment_link`. No PaymentAttempt yet.
  - **`sync_payment`** — Poll the PSP for the order's current state. Returns the overall `OrderStatus` and the list of `PaymentAttempt`s observed so far.
  - **`refund`** — Initiate a refund against the successful PaymentAttempt of an order (full or partial). Returns a `psp_refund_id`.
  - **`sync_refund`** — Poll for refund status.
- **Webhook (in Lens)** — `Connector.handle_webhook` verifies the PSP's signature on a raw payload and parses it into a `WebhookEvent` carrying a `PaymentAttempt` (for payment-level events) or a `RefundEvent` (for refund-level events). Dedup of webhooks is Orbit's job.
- **Hosted Checkout / Session-based** — The integration model where the PSP renders its own page for the payer to enter card/UPI/wallet details. v1 uses only this model.
- **Idempotency Key** — A client-supplied identifier passed to `create_order` and `refund` so PSP retries don't double-create. Lens passes it through; doesn't store it.
- **Connector** — A Python class (one per PSP) that implements the `Connector` ABC. Owns its httpx client; translates between our domain types and the PSP's wire-level types.
- **merchant_id** — The PSP-side identifier for the Symplora merchant account configured on this `Connector`. Sourced from `ConnectorConfig` (typically derived from credentials or `additional`); passed through on every `RequestCommon`-bearing call so the PSP can scope the request. Distinct from Orbit's `api_key_id` (which identifies the *consumer app*, not the PSP merchant).
- **ConnectorFactory** — The registry that maps PSP names (e.g., `"cashfree"`) to Connector classes.
- **PaymentsFacade** — The class Orbit holds. A thin wrapper around one Connector that adds request-id binding, structured logging, and error normalization.
- **Maskable[T]** — A wrapper type that signals "this field is PII." Stringifies as `***`.
- **Amount** — A composite of `minor_units: int` (paise, cents) and `currency: Currency`. The only money type that crosses public boundaries.
- **OrderStatus** — PSP-side state of an Order: `CREATED`, `PAID`, `PARTIALLY_REFUNDED`, `REFUNDED`, `EXPIRED`, `FAILED`.
- **PaymentAttemptStatus** — State of an individual attempt: `PENDING`, `SUCCESS`, `FAILED`. The *granularity* of failure (user dropped, card declined, fraud, etc.) lives on `PaymentFailureCode`.
- **RefundStatus** — State of a refund: `PENDING`, `SUCCESS`, `FAILED`.
- **PaymentFailureCode** — Locked taxonomy for *why* an attempt failed. v1 set: `USER_DROPPED`, `USER_CANCELLED`, `CARD_DECLINED`, `INSUFFICIENT_FUNDS`, `AUTHENTICATION_FAILED`, `FRAUD_BLOCKED`, `FRAUD_REVIEW_PENDING`, `INVALID_INSTRUMENT`, `PSP_ERROR`, `NETWORK_ERROR`, `UNKNOWN`. Carried on `PaymentAttempt.failure_code`. Additive-only (new codes are minor bumps).
- **ConnectorError** — The single typed exception raised by anything Lens does that fails. Carries `reason: ConnectorErrorReason`.

---

## §3. Ground rules

Plain-English rules every implementer of Lens follows.

1. **Stateless library.** No database. No file I/O beyond httpx. No global mutable state except `ConnectorFactory._registry` (write-once at import).
2. **No HTTP server.** Pure Python library; never opens a listening socket.
3. **Async everywhere.** Every public method on `PaymentsFacade` and `Connector` is `async def`. CPU work via `asyncio.to_thread`.
4. **One class per PSP.** Each `Connector` subclass implements all four flow methods + `handle_webhook` + `close`. No per-(PSP × Flow) class splits.
5. **Each Connector owns its httpx client.** Created in `__init__`, closed in `close()`. Configured with timeouts, retries, and a structured-logging event hook. Tests pass `httpx.MockTransport` at construction.
6. **No business logic in Connectors.** A Connector's job is: take a domain request, build the PSP-shaped HTTP request, call the PSP, parse the response into a domain response, return it. Business decisions (state transitions on Orders, idempotency dedup, ledger updates) belong to Orbit.
7. **Hosted-checkout only in v1.** Connectors never receive raw card numbers, UPI VPAs, or wallet IDs. `PaymentMethod` is an allow-list constraint passed to the PSP and a value read back; not a per-method request builder.
8. **Pydantic v2 at every boundary.** Requests are `frozen=True`, responses `frozen=False`. All models use `extra="forbid"`.
9. **`mypy --strict` mandatory.** No `Any`. Every public function annotated.
10. **All money is integer minor units at our boundaries.** No floats in our domain types, no floats in our DB schemas, no floats on our public surface. PSP wire-level transformations (where a specific PSP's API takes a different unit, e.g., rupees-as-string with two decimal places) may use `decimal.Decimal` *inside* the connector method to format the request — but the Decimal value never escapes back into our domain types. Example: `Decimal(amount.minor_units) / 100` is fine when building a Cashfree request body; the response's `paid_amount` field on `PaymentAttempt` is always `int`.
11. **PII through `Maskable[T]`.** Any secret-bearing field is typed `Maskable[str]`. `expose()` is the only way to read.
12. **All errors are `ConnectorError`.** PSP-specific exceptions are caught and translated inside the Connector method.
13. **Idempotency keys pass through, never persist.** Lens forwards the caller-supplied key to the PSP. Dedup is Orbit's job.
14. **Webhook = verify + parse, nothing else.** `Connector.handle_webhook` verifies the signature, parses the body into a `WebhookEvent` (with `attempt` or `refund` populated), returns it.
15. **The `__init__.py` in each `connectors/<psp>/` package self-registers with `ConnectorFactory` on import.**
16. **Map all PSP-specific outcome terms into the locked `PaymentFailureCode` taxonomy.** PSPs use varying vocabulary (`USER_DROPPED`, `NOT_ATTEMPTED`, `cancelled_by_user`, `payment_did_not_complete`, …). Each Connector translates them to our taxonomy. If no value fits, use `UNKNOWN` and capture the PSP-original in `failure_reason`.

---

## §4. Public interfaces (locked)

### 4.1 `PaymentsFacade`

```python
# lens/facade.py

class PaymentsFacade:
    def __init__(self, connector: Connector): ...

    async def create_order(self,  request: CreateOrderRequest)  -> CreateOrderResponse: ...
    async def sync_payment(self,  request: SyncPaymentRequest)  -> SyncPaymentResponse: ...
    async def refund(self,        request: RefundRequest)       -> RefundResponse: ...
    async def sync_refund(self,   request: SyncRefundRequest)   -> SyncRefundResponse: ...

    async def incoming_webhook(
        self, raw_payload: bytes, headers: dict[str, str]
    ) -> WebhookEvent: ...

    async def close(self) -> None: ...
```

Implementation is a thin wrapper around the held `Connector`. Each method:

1. Binds `request_id`, `connector_name`, `flow` to structlog context.
2. Emits a `start` log record.
3. Calls the equivalent method on `self.connector`.
4. Catches any non-`ConnectorError` exception and re-raises as `ConnectorError(reason=INTERNAL)`.
5. Emits an `end` log record with `latency_ms` and `outcome`.
6. Returns the result.

### 4.2 `Connector` ABC

```python
# lens/connector.py

class Connector(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...                              # e.g., "cashfree"

    @property
    @abstractmethod
    def base_url(self) -> str: ...

    @property
    @abstractmethod
    def supported_methods(self) -> set[PaymentMethod]: ...

    @property
    @abstractmethod
    def supports_idempotency_key(self) -> bool: ...

    @abstractmethod
    async def create_order(self, request: CreateOrderRequest) -> CreateOrderResponse:
        """Create a hosted-checkout session/order. Returns psp_order_id and payment_link."""
        ...

    @abstractmethod
    async def sync_payment(self, request: SyncPaymentRequest) -> SyncPaymentResponse:
        """Poll the PSP for the order's current OrderStatus and the list of
        PaymentAttempts observed under it."""
        ...

    @abstractmethod
    async def refund(self, request: RefundRequest) -> RefundResponse:
        """Initiate a refund against the successful PaymentAttempt of an order."""
        ...

    @abstractmethod
    async def sync_refund(self, request: SyncRefundRequest) -> SyncRefundResponse:
        """Poll the PSP for the refund's current status."""
        ...

    @abstractmethod
    async def handle_webhook(
        self, raw_payload: bytes, headers: dict[str, str]
    ) -> WebhookEvent:
        """Verify the signature and parse the body. The WebhookEvent carries either
        a PaymentAttempt (for payment-level events) or a RefundEvent (for refund-level).
        Raises ConnectorError(reason=WEBHOOK_SIGNATURE_FAILED) on bad signature."""
        ...

    @abstractmethod
    async def close(self) -> None: ...
```

### 4.3 `ConnectorFactory`

```python
# lens/factory.py

class ConnectorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str                                      # "cashfree", "razorpay", ...
    api_key: Maskable[str]
    secret_key: Maskable[str] | None = None
    webhook_secret: Maskable[str] | None = None
    base_url_override: HttpUrl | None = None       # for sandbox / staging
    additional: dict[str, Any] = Field(default_factory=dict)


class ConnectorFactory:
    _registry: dict[str, type[Connector]] = {}

    @classmethod
    def register(cls, name: str, connector_cls: type[Connector]) -> None:
        """Registers a Connector class under `name`. Validates:
          1. `connector_cls(stub_config).name == name` — the class's `name`
             property must match the registry key.
          2. `connector_cls.requires_lens` (semver string declared
             on the class or its module) is satisfied by the running
             Lens version. Use packaging.version.SpecifierSet.

        Raises ConnectorError(reason=INVALID_REQUEST) on (1) mismatch;
        raises ConnectorError(reason=INCOMPATIBLE_VERSION) on (2) mismatch.
        """

    @classmethod
    def create(cls, config: ConnectorConfig) -> Connector: ...

    @classmethod
    def list_connectors(cls) -> list[str]: ...
```

Each `connectors/<psp>/__init__.py` declares `requires_lens` (e.g., `requires_lens = "^0.1"`) at module scope and ends with `ConnectorFactory.register("<psp>", <PspClass>)`.

### 4.4 Domain types

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
    expires_at: datetime | None = None             # PSP-side TTL; PSP may impose its own min/max
    metadata: dict[str, str] = Field(default_factory=dict)

class CreateOrderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)
    psp_order_id: str
    payment_link: HttpUrl
    status: OrderStatus                            # typically OrderStatus.CREATED
    expires_at: datetime | None = None


# Per-attempt model — returned in lists by sync_payment, and individually by webhooks.
class PaymentAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    psp_payment_id: str
    status: PaymentAttemptStatus                   # PENDING | SUCCESS | FAILED
    method_used: PaymentMethod | None = None       # populated post-attempt
    amount: Amount | None = None                   # PSP may not report this until SUCCESS
    failure_code: PaymentFailureCode | None = None # populated on FAILED (or on PENDING-in-review)
    failure_reason: str | None = None              # human-readable; PSP's raw text
    attempted_at: datetime                         # PSP-reported timestamp of the attempt
    raw: dict[str, Any] = Field(default_factory=dict)


# sync_payment
class SyncPaymentRequest(RequestCommon):
    psp_order_id: str

class SyncPaymentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)
    psp_order_id: str
    status: OrderStatus                            # the order's overall status as PSP sees it
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
    psp_order_id: str | None = None                # if PSP includes it
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

### 4.5 Common / utility types

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

### 4.6 Enums (all locked)

```python
# lens/enums/__init__.py

class Currency(StrEnum): INR = "INR"; USD = "USD"; EUR = "EUR"; GBP = "GBP"; ...

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
    FRAUD_REVIEW_PENDING = "FRAUD_REVIEW_PENDING"   # used when status=PENDING during review
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
    NOT_SUPPORTED = "NOT_SUPPORTED"             # method not supported by this PSP
                                                  # (or by this v1 Connector — e.g.,
                                                  #  authorize/capture/void from the
                                                  #  future s2s ABC)
    INCOMPATIBLE_VERSION = "INCOMPATIBLE_VERSION"  # connector's required Lens
                                                    # version doesn't match runtime
    INTERNAL = "INTERNAL"
```

### 4.7 Public-surface snapshot

`tests/snapshot/public_surface.py` lists every public symbol and its signature. CI fails on drift.

---

## §5. Internal architecture

### 5.1 File layout

```
lens/
  __init__.py            # re-exports public surface
  facade.py              # PaymentsFacade
  factory.py             # ConnectorFactory + ConnectorConfig
  connector.py           # Connector ABC
  domain_types/          # request/response models + PaymentAttempt + Amount + WebhookEvent + RefundEvent
    __init__.py
  common/                # Maskable, ConnectorError
    __init__.py
  enums/                 # Currency, PaymentMethod, OrderStatus, PaymentAttemptStatus,
                         # RefundStatus, PaymentFailureCode, WebhookEventType, ConnectorErrorReason
    __init__.py
  http/                  # internal httpx client factory
    __init__.py
  connectors/
    __init__.py
    cashfree/
      __init__.py        # ends with ConnectorFactory.register("cashfree", Cashfree)
      connector.py       # class Cashfree(Connector): ...
      auth.py
      models.py          # Cashfree wire-level Pydantic models
      status_map.py      # Cashfree-specific term → (PaymentAttemptStatus, PaymentFailureCode)
      tests/
  legacy/                # archived from Plan C; NOT shipped in v1
    cashfree_s2s/
    cashfree_authorize/
```

### 5.2 Mapping PSP terms to our taxonomy — Cashfree example

Cashfree's payment statuses (and Orbit's resulting interpretation):

| Cashfree term | PaymentAttemptStatus | PaymentFailureCode | Notes |
|---|---|---|---|
| `SUCCESS` | `SUCCESS` | — | Happy path. |
| `FAILED` | `FAILED` | `CARD_DECLINED` (or per error_code mapping) | Look at Cashfree's `payment_message` for nuance. |
| `USER_DROPPED` | `FAILED` | `USER_DROPPED` | Cashfree-specific signal. |
| `CANCELLED` | `FAILED` | `USER_CANCELLED` | Rare; explicit cancel. |
| `FLAGGED` | `PENDING` | `FRAUD_REVIEW_PENDING` | Non-terminal; resolved by follow-up webhook. |
| `PENDING` | `PENDING` | — | Async method awaiting outcome (UPI etc.). |
| `NOT_ATTEMPTED` | (no PaymentAttempt is created — PSP signals nothing happened) | — | We don't create an attempt for this. |

The Cashfree Connector contains a `status_map.py` (per §5.1) with this mapping. Same pattern repeats for every PSP.

### 5.3 How a Connector implements a flow

Concrete pattern, using Cashfree's `create_order` as the example:

```python
# lens/connectors/cashfree/connector.py

class Cashfree(Connector):
    @property
    def name(self) -> str:
        return "cashfree"

    def __init__(self, config: ConnectorConfig):
        self._config = config
        self._client = build_http_client(
            base_url=config.base_url_override or self.base_url,
            connector_name=self.name,
        )

    @property
    def base_url(self) -> str:
        return "https://sandbox.cashfree.com/pg"

    @property
    def supported_methods(self) -> set[PaymentMethod]:
        return {PaymentMethod.CARD, PaymentMethod.UPI}

    @property
    def supports_idempotency_key(self) -> bool:
        return True

    async def create_order(self, request: CreateOrderRequest) -> CreateOrderResponse:
        # Cashfree's API takes order_amount in major units as a decimal string
        # (e.g., "500.00" for 50000 paise). Per Ground Rule 10, Decimal is used
        # inside the connector method to format the PSP request; the value never
        # crosses back into our domain types.
        psp_req = CashfreeCreateOrderRequest(
            order_id=request.order_id,        # Orbit's id as Cashfree's reference
            order_amount=str(Decimal(request.amount.minor_units) / 100),
            order_currency=request.amount.currency.value,
            customer_details=CashfreeCustomerDetails(...),
            order_meta=CashfreeOrderMeta(return_url=str(request.return_url), ...),
            payment_methods=_format_methods(request.allowed_methods),
        )
        headers = sign_request(self._config, psp_req)
        if request.idempotency_key and self.supports_idempotency_key:
            headers["x-idempotency-key"] = request.idempotency_key

        try:
            resp = await self._client.post("/orders", json=psp_req.model_dump(), headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise _map_http_error(e) from e
        except httpx.HTTPError as e:
            raise ConnectorError(reason=ConnectorErrorReason.PSP_UNAVAILABLE) from e

        psp_resp = CashfreeCreateOrderResponse.model_validate(resp.json())
        return CreateOrderResponse(
            psp_order_id=psp_resp.cf_order_id,
            payment_link=psp_resp.payment_link,
            status=OrderStatus.CREATED,
            expires_at=psp_resp.order_expiry_time,
        )

    async def sync_payment(self, request: SyncPaymentRequest) -> SyncPaymentResponse:
        # Cashfree: GET /orders/{psp_order_id}/payments returns the list of attempts.
        # Cashfree: GET /orders/{psp_order_id} returns the order. We may need both.
        order_resp = await self._get_order(request.psp_order_id)
        payments_resp = await self._get_payments(request.psp_order_id)

        attempts = [_payment_to_attempt(p) for p in payments_resp]  # uses status_map.py
        return SyncPaymentResponse(
            psp_order_id=request.psp_order_id,
            status=_map_order_status(order_resp),
            paid_amount=_compute_paid_amount(attempts),
            attempts=attempts,
        )

    async def handle_webhook(self, raw_payload, headers) -> WebhookEvent:
        # 1. Verify signature.
        if not _verify_cashfree_signature(self._config, raw_payload, headers):
            raise ConnectorError(reason=ConnectorErrorReason.WEBHOOK_SIGNATURE_FAILED)

        # 2. Parse the PSP event.
        psp_event = CashfreeWebhookEvent.model_validate_json(raw_payload)

        # 3. Build the WebhookEvent, populating attempt OR refund based on type.
        if psp_event.type.startswith("PAYMENT_"):
            attempt = _payment_to_attempt(psp_event.data.payment)
            return WebhookEvent(
                event_type=_map_event_type(psp_event.type),
                psp_event_id=psp_event.event_id,
                psp_order_id=psp_event.data.order.cf_order_id,
                attempt=attempt,
                raw_payload=psp_event.model_dump(),
            )
        elif psp_event.type.startswith("REFUND_"):
            refund = _to_refund_event(psp_event.data.refund)
            return WebhookEvent(
                event_type=_map_event_type(psp_event.type),
                psp_event_id=psp_event.event_id,
                psp_order_id=psp_event.data.order.cf_order_id if psp_event.data.order else None,
                refund=refund,
                raw_payload=psp_event.model_dump(),
            )
        elif psp_event.type == "ORDER_EXPIRED":
            return WebhookEvent(
                event_type=WebhookEventType.ORDER_EXPIRED,
                psp_event_id=psp_event.event_id,
                psp_order_id=psp_event.data.order.cf_order_id,
                raw_payload=psp_event.model_dump(),
            )
        else:
            # Unknown event type — log + still return a benign event Orbit can ignore.
            ...

    async def close(self) -> None:
        await self._client.aclose()
```

### 5.4 The httpx client factory

`lens.http.build_http_client(...)` returns an `httpx.AsyncClient` pre-configured with:

- Default timeout (configurable per PSP via `ConnectorConfig.additional`).
- `httpx.AsyncHTTPTransport(retries=N)` for transport-level retries.
- Event hooks (`request`, `response`) for structured logging with `Maskable` masking.

Connectors never construct httpx directly. Tests inject `httpx.MockTransport`.

### 5.5 Cross-cutting concerns recap

| Concern | Location |
|---|---|
| Request-id, structured logging | `PaymentsFacade` |
| Retry on 5xx / network error | httpx transport in `build_http_client` |
| PII masking in logs | `Maskable[T]` `__str__` + structlog processor |
| Error normalization to `ConnectorError` | inside each `Connector` method |
| Mapping PSP-specific outcome terms → `PaymentAttemptStatus` + `PaymentFailureCode` | each `connectors/<psp>/status_map.py` |
| Webhook signature verification | inside `Connector.handle_webhook` |
| Webhook dedup, ledger updates | **Orbit**, not here |
| Idempotency key dedup | **Orbit**. Lens only passes the key through to the PSP. |

### 5.6 Cashfree restructure (constitution §9 Step 3)

1. Identify and move to `legacy/`:
   - Direct-API code (instrument handling, raw card/UPI).
   - Any `authorize` / `capture` / `void` methods or routes.
   - Anything that doesn't fit the four v1 flows.
2. Keep create-order / sync-payment / refund / sync-refund / webhook paths.
3. Refactor into the layout in §5.1.
4. Add `status_map.py` for Cashfree term mapping per §5.2.
5. Rename / reshape signatures to match §4. Run `mypy --strict` until clean.
6. Tests: `httpx.MockTransport`-backed unit tests per flow + an integration test that asserts a multi-attempt order (first attempt FAILED, second SUCCESS) is correctly surfaced in `sync_payment.attempts`.
7. Verify `connectors/cashfree/__init__.py` self-registers.

---

## §6. Dependencies

- Python ≥ 3.11
- `httpx >= 0.27`
- `pydantic >= 2.6`
- `structlog >= 24.0`
- `pytest`, `pytest-asyncio` (dev)

No DB driver. No web framework. No message queue client.

Upstream (build-time): Grace generates code targeting this module's ABC.
Downstream (runtime): Orbit imports this module.

---

## §7. Non-functional requirements

Inherits constitution §6. Additions:

- Per-PSP packages are independent.
- httpx client lifecycle: per `Connector`, closed via `Connector.close()`.
- Per-flow latency budget: default 5s, configurable per PSP.
- Retry policy: exponential backoff, max 3 attempts, only on `network_error`, `5xx`, `429`. State-mutating flows (`create_order`, `refund`) retry only when the caller passed an idempotency key.
- Rate limit: per-PSP, per-flow token bucket, configurable.

---

## §8. Acceptance criteria for v1

- [ ] All public symbols in §4 exist with the locked names.
- [ ] `tests/snapshot/public_surface.py` lists every public name; CI fails on drift.
- [ ] `mypy --strict` clean.
- [ ] `pytest --cov` ≥ 80% across the package.
- [ ] Cashfree implemented hand-written; all four flow tests pass via `httpx.MockTransport`:
    - `create_order` → PSP returns order_id + payment_link.
    - `sync_payment` → PSP returns `OrderStatus` + a list of `PaymentAttempt`s (test the multi-attempt case explicitly).
    - `refund` → PSP returns refund_id.
    - `sync_refund` → PSP returns refund status.
- [ ] Cashfree's `status_map.py` covers every Cashfree payment status documented in their API; unmapped values fall back to `PaymentFailureCode.UNKNOWN` and log a warning.
- [ ] Webhook tests:
    - Signed Cashfree `PAYMENT_SUCCESS_WEBHOOK` → `WebhookEvent` with `attempt.status == SUCCESS`.
    - Signed Cashfree `PAYMENT_FAILED_WEBHOOK` → `WebhookEvent` with `attempt.status == FAILED` and `failure_code` populated.
    - Signed Cashfree `PAYMENT_USER_DROPPED_WEBHOOK` → `WebhookEvent` with `attempt.status == FAILED` and `failure_code == USER_DROPPED`.
    - Signed Cashfree `REFUND_SUCCESS_WEBHOOK` → `WebhookEvent` with `refund.status == SUCCESS`.
    - Tampered payload → `ConnectorError(WEBHOOK_SIGNATURE_FAILED)`.
- [ ] Optional CI job against Cashfree sandbox passes for each of the four flows.
- [ ] Package builds, `pip install -e .` works in a fresh venv.
- [ ] Any direct-API / authorize / capture / void code in the existing Cashfree implementation moved to `legacy/` per constitution OQ-8.
- [ ] Old FastAPI scaffolding deleted or relocated per constitution OQ-2.

---

## §9. Roadmap

Maps to constitution §9 Steps 1 + 2 + 3.

1. **Write the locked interfaces** (constitution Step 1). ~2 days. Output: `domain_types/`, `enums/`, `common/`, `connector.py`, `factory.py`, `facade.py` (signature + skeleton), `http/`. Contract snapshot test first.
2. **Implement `PaymentsFacade` + factory** (Step 2). ~1.5 days. Wire request-id, structured logging, error normalization. Integration tests with a stub Connector.
3. **Audit + restructure Cashfree** (Step 3). ~3 days. Output: cleaned `connectors/cashfree/` with `status_map.py`; everything that doesn't fit v1 moved to `legacy/`. Mocked tests pass for the four flows + multi-attempt case + all webhook types.
4. **Packaging + contract-test wiring**. ~0.5 day.

Total: ~7 days single-agent. Steps 1 + 2 sequential; Step 3 can run in parallel with Step 2 once Step 1 ships.

---

## §10. Open questions for the implementing agent

- **Q1** (constitution OQ-4): naming. `Connector` (not `PaymentConnector`); `Order` and `PaymentAttempt` as the two first-class entities. First PR is a bulk rename.
- **Q2**: `WebhookEvent.raw_payload` — keep for debugging? **Yes** — useful for replay and PSP-bug forensics; never logged directly.
- **Q3** (constitution OQ-6): same idempotency key on retry. Confirmed.
- **Q4**: Should `PaymentAttempt.amount` always be populated, or only on `SUCCESS`? **Recommendation**: only on `SUCCESS` (PSPs vary; treat as optional everywhere else).
- **Q5**: Should Cashfree's `sync_payment` always make both calls (`/orders/{id}` + `/orders/{id}/payments`)? **Recommendation**: yes for v1 simplicity. Optimize to single call later if Cashfree adds an "include payments" parameter.
- **Q6**: For `FRAUD_REVIEW_PENDING` (an attempt sitting in PSP review), how do we ensure resolution arrives? **Recommendation**: rely on the PSP webhook for resolution (Cashfree emits a follow-up `PAYMENT_SUCCESS` or `PAYMENT_FAILED` after review). Orbit's janitor can also poll `sync_payment` for orders whose only attempt is `PENDING` + age > 1h, as a safety net.
- **Q7**: What if a PSP emits a webhook for a payment we haven't seen via `create_order`? **Recommendation**: still verify + parse + return the `WebhookEvent`. Orbit decides what to do with an orphan event (likely log + ignore, since we created the order so we should have a record).
- **Q8**: `PaymentAttempt` is `frozen=True` — but should it be? Each attempt has a fixed lifecycle once observed; we don't mutate the model itself, we create new instances when status updates arrive (or carry a single one in a WebhookEvent). **Recommendation**: keep `frozen=True`.
