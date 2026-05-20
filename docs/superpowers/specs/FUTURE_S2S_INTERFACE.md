# Future-scope: Server-to-Server (Direct API) Interface

**Status**: future scope — not in v1. Captured so the vocabulary, design intent, and existing-code archive are not lost.
**Triggered by**: constitution v0.3 (2026-05-20) which scoped v1 to hosted-checkout only. v0.4 added the Order + PaymentAttempt two-entity model; this doc updated to align.
**Owner**: TBD — to be revived when a consumer app needs s2s capability (see constitution OQ-9).

> **This document is a reference, not a spec.** Nothing here ships in v1. When s2s comes back into scope, this becomes the starting point for an `ORBIT_S2S_*.md` lock-in document; until then, treat the shapes below as design intent that may be revised.

---

## §1. Why this is parked

Hosted-checkout / session-based integration (constitution §7) covers the v1 consumer use case: an app calls `POST /v1/orders`, gets back a `payment_link`, redirects the user. The user enters their card / UPI / wallet details *on the PSP's hosted page*. The merchant never holds raw instrument data; PCI scope sits with the PSP.

Server-to-server (s2s) / direct-API flows require:

- The merchant collecting raw instrument data (card number, CVV, expiry, UPI VPA, wallet token) on its own UI.
- A different request shape per PSP — every PSP has its own card / UPI / wallet request schema.
- PCI scope expansion to the merchant.
- A separate authorize → capture lifecycle (most PSPs support two-step in s2s mode).
- A void step to cancel pre-capture authorizations.
- Often: tokenization, vaulting, 3DS challenge flows.

No v1 consumer (Symplora ATS, Hikara) has signaled a need for raw instrument capture. So we ship hosted-checkout, and park this work here.

## §2. When to bring this back

Trigger conditions (any one):

- A consumer app needs a payment surface that hosted-checkout can't cover. Concrete examples: charging a previously-stored card on file (recurring payment) where the PSP requires s2s API access; in-app instrument capture in a native mobile UX that doesn't redirect to a hosted page.
- A new PSP we want to add only supports s2s, no hosted checkout.
- A compliance / cost decision pushes us to handle tokenized cards directly (typically only worth it at large scale).

Until one of those is concrete, this document doesn't move out of "future scope".

## §3. The s2s flows (vocabulary)

These are additive to the v1 four-flow interface. They extend the `PaymentAttempt` model (entity 2 from constitution v0.4) with s2s-specific lifecycle states; the `Order` entity (entity 1) doesn't fundamentally change.

### 3.1 `authorize` (s2s)

**Conceptually**: "Charge this card (or other instrument) for this amount, on the merchant's behalf, holding the funds."

- The merchant provides the instrument (card data, UPI VPA, wallet token) — collected on the merchant's own UI.
- The PSP holds funds (two-step mode) or moves them (one-step / auto-capture).
- Creates a `PaymentAttempt` directly (no preceding hosted-page flow). Returns `psp_payment_id` + initial s2s status.

### 3.2 `capture` (s2s)

**Conceptually**: "Move the previously-authorized funds to the merchant's settlement account."

- Merchant provides the `psp_payment_id` from an earlier `authorize`.
- Optional partial amount.
- PSP returns the updated payment status.

### 3.3 `void` (s2s)

**Conceptually**: "Cancel an authorization before it's been captured."

- Merchant provides the `psp_payment_id` of an authorized-but-not-captured payment.
- PSP releases the held funds back to the payer's instrument.

### 3.4 Flows shared between hosted-checkout and s2s

These are unchanged from v1. The implementation may differ per PSP, but the abstract shape stays the same:

- `refund` — give money back from a captured payment.
- `sync_payment` — check current status of an Order (and its PaymentAttempts).
- `sync_refund` — check current status of a refund.
- `handle_webhook` — same; events expand to include `PAYMENT_AUTHORIZED`, `PAYMENT_CAPTURED`, `PAYMENT_VOIDED`.

## §4. Proposed shape when s2s ships

### 4.1 `Connector` ABC — additive

When s2s ships, the v1 ABC gains three new abstract methods. The base ABC stays as defined in `SUBPROJECT_LENS.md` §4.2:

```python
class Connector(ABC):
    # --- v1 (hosted) — unchanged ---
    async def create_order(self,  request: CreateOrderRequest)  -> CreateOrderResponse: ...
    async def sync_payment(self,  request: SyncPaymentRequest)  -> SyncPaymentResponse: ...
    async def refund(self,        request: RefundRequest)       -> RefundResponse: ...
    async def sync_refund(self,   request: SyncRefundRequest)   -> SyncRefundResponse: ...
    async def handle_webhook(self, raw_payload, headers)        -> WebhookEvent: ...
    async def close(self) -> None: ...

    # --- s2s — added when direct-API ships ---
    async def authorize(self, request: AuthorizeRequest) -> AuthorizeResponse: ...
    async def capture(self,   request: CaptureRequest)   -> CaptureResponse: ...
    async def void(self,      request: VoidRequest)      -> VoidResponse: ...
```

Per-PSP `Connector` classes that don't support s2s raise `ConnectorError(reason=NOT_SUPPORTED)` for the new methods. A new property `supports_direct_api: bool` is added so callers can check before invoking.

### 4.2 PaymentAttempt — extended

The v1 `PaymentAttempt` keeps its three states (`PENDING`, `SUCCESS`, `FAILED`). For s2s, five additional states are added below (`AUTHORIZED`, `PARTIALLY_CAPTURED`, `CAPTURED`, `VOIDED`, `AWAITING_3DS`):

```python
class PaymentAttemptStatus(StrEnum):
    # v1 (hosted) — unchanged
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

    # Added when s2s ships
    AUTHORIZED = "AUTHORIZED"           # auth done, awaiting capture
    PARTIALLY_CAPTURED = "PARTIALLY_CAPTURED"
    CAPTURED = "CAPTURED"               # equivalent to SUCCESS for s2s flows
    VOIDED = "VOIDED"
    AWAITING_3DS = "AWAITING_3DS"
```

`PaymentAttempt` gains fields:

- `captured_amount: int | None` — for two-step flows where capture amount differs from authorized.
- `challenge_url: HttpUrl | None` — for 3DS step-up redirects.
- `method_data_hash: str | None` — non-PII fingerprint of the instrument used (for audit / fraud-replay detection).

The `OrderStatus` enum may also gain `AUTHORIZED` (an Order where the s2s `authorize` succeeded but capture hasn't happened yet).

### 4.3 New domain types

PII-scoped — handle with care; never log; never persist in plain form. Apply Maskable wrappers per `SUBPROJECT_LENS.md` rules.

```python
class CardData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    number: Maskable[str]
    cvv: Maskable[str]
    expiry_month: int
    expiry_year: int
    cardholder_name: str

class UpiData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    vpa: Maskable[str]

class TokenizedInstrument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    token: Maskable[str]
    token_type: Literal["network_token", "psp_token"]
    last4: str | None = None  # display only

PaymentMethodData = CardData | UpiData | TokenizedInstrument


class AuthorizeRequest(RequestCommon):
    amount: Amount
    method_data: PaymentMethodData
    capture_method: CaptureMethod          # AUTOMATIC | MANUAL
    three_ds_required: bool = False
    return_url: HttpUrl | None = None      # only if 3DS challenge expected

class AuthorizeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)
    psp_payment_id: str
    status: PaymentAttemptStatus           # AUTHORIZED | CAPTURED | FAILED | AWAITING_3DS
    challenge_url: HttpUrl | None = None
    captured_amount: int | None = None


class CaptureRequest(RequestCommon):
    psp_payment_id: str
    amount_to_capture: int | None = None

class CaptureResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)
    psp_payment_id: str
    status: PaymentAttemptStatus
    captured_amount: int | None = None


class VoidRequest(RequestCommon):
    psp_payment_id: str

class VoidResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)
    psp_payment_id: str
    status: PaymentAttemptStatus
```

### 4.4 Orbit (product) — additive endpoints

```
POST /v1/orders/{id}/authorize          # for s2s mode; merchant supplies method_data
  body: { method_data, capture_method?, three_ds_required? }
  → 200 OK { order_id, attempt_id, status, challenge_url? }

POST /v1/orders/{id}/attempts/{attempt_id}/capture
  body: { amount?: int }
  → 200 OK { attempt_id, status }

POST /v1/orders/{id}/attempts/{attempt_id}/void
  → 200 OK { attempt_id, status }
```

Note: in s2s mode, the **payer's instrument data goes directly to the Orbit endpoint** — Orbit enters PCI scope (or relies on PSP tokenization to stay out of it).

Orbit's `OrderStatus` enum gains `AUTHORIZED` (s2s two-step intermediate state, before capture). The state machine extends:

```
CREATED → AUTHORIZED          (s2s authorize success, two-step mode)
AUTHORIZED → PAID             (capture success — terminal positive in s2s as well)
AUTHORIZED → FAILED           (void or capture failure)
```

Existing transitions (`CREATED → PAID`, `PAID → REFUNDED`, etc.) continue to work for both hosted and s2s.

### 4.5 Grace

When s2s ships, Grace's rulebook describes both modes. The generated `<Psp>(Connector)` class implements all seven methods (or raises `NOT_SUPPORTED` for s2s methods if the PSP only supports one mode).

Quality rubric's "Public-surface conformance" dimension updates to check for all seven flow methods.

## §5. PCI scope considerations

s2s touches raw card data. Before it ships:

- Determine if Symplora is willing to be in PCI scope (likely PCI-DSS SAQ A-EP at minimum; potentially D depending on storage).
- Decide on tokenization strategy. Options:
  - Network-level tokens (Visa / Mastercard network tokens via PSP).
  - PSP-vault tokens (Cashfree / Razorpay store the card, return a token; merchant only stores the token).
  - First-party vault (own card vault — strongly not recommended pre-scale).
- The `CardData` model in §4.3 should be considered an in-memory-only type; never persisted, never logged. The `Maskable` wrapper isn't sufficient for PCI — additional handling rules apply.

This is the single biggest reason s2s is parked: PCI scope expansion is a meaningful organizational decision, not just a code change.

## §6. Archived code

The `legacy/` directory under `lens/connectors/cashfree/` (and any analogous archive in other connectors) holds:

- Direct-API / raw card / raw UPI request building from Plan C's pre-v1 implementation.
- `authorize` / `capture` / `void` methods or routes from Plan C v0.x.
- Anything that doesn't fit the four v1 flows.

That code is reference material for whoever revives s2s. It is **not** maintained, not tested, not type-checked. Don't import from `legacy/` in production code.

## §7. Open questions for the future revisit

These are NOT v1 open questions. They are notes for whoever picks this up later.

- **Q1**: Token vault strategy — network tokens, PSP-vault tokens, or own vault?
- **Q2**: 3DS challenge flow — how does Orbit hand the challenge URL back to the consumer app? Redirect, modal iframe, native SDK?
- **Q3**: Does `POST /v1/orders` gain a body discriminator (`mode: "hosted" | "direct"`), or do separate endpoints (`POST /v1/orders` for hosted vs `POST /v1/orders/{id}/authorize` for s2s) keep them clean?
- **Q4**: Per-PSP support matrix — do we maintain a feature table (Cashfree supports CARD-s2s but not UPI-s2s, etc.)? Where does it live so apps can query?
- **Q5**: Capture method default — `AUTOMATIC` (one-step) or `MANUAL` (two-step) when not specified? Probably automatic for parity with hosted behavior; opt-in to manual for marketplace use cases.
- **Q6**: How do we test s2s in CI? PCI sandbox accounts have stricter access controls than typical PSP sandboxes.
- **Q7**: Should the s2s `authorize` create the Order implicitly (one round-trip from consumer's perspective) or require a prior `POST /v1/orders` (two round-trips)? Cashfree/Razorpay s2s typically create the Order under the hood; we may want the same.

---

## Changelog

- **2026-05-20** — created when constitution v0.3 narrowed v1 to hosted-checkout.
- **2026-05-20 v0.2** — updated naming and references to align with constitution v0.4 (Order + PaymentAttempt entity model; `PaymentAttemptStatus` enum). s2s shapes now describe how PaymentAttempt lifecycle states extend when s2s ships.
