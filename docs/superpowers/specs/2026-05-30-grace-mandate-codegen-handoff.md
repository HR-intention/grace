---
name: Grace Handoff — Mandate-Capable Connector Codegen
description: What Grace must generate now that the lens mandate interface is LOCKED in lens 0.2.0. The as-built capability-interface ABCs, the concrete WebhookHandlers/register_webhook mechanism, the Cashfree→lens normalization tables, and the regeneration plan.
type: design / grace-handoff
status: Ready for Grace — interface LOCKED in lens 0.2.0 (committed on feat/lens). Generate against the as-built ABCs in §3–§4.
created: 2026-05-30
updated: 2026-05-30 (rev 2 — lens 0.2.0 shipped; shapes are now as-built/authoritative)
authors: Sarthak (lens)
related:
  - docs/superpowers/specs/lens/SUBPROJECT_GRACE_CODEGEN.md
  - docs/superpowers/specs/lens/SUBPROJECT_LENS.md
  - docs/superpowers/specs/lens/ORBIT_CONSTITUTION.md
  - "[[2026-05-30-lens-mandate-contract-for-orbit]]"
---

# Grace Handoff — Mandate-Capable Connector Codegen

## 1. Status & what's needed from Grace now

**The interface is LOCKED.** Lens shipped the capability ABCs + mandate domain types
+ the shared `WebhookRouter` in **lens 0.2.0** (committed on `feat/lens`; 137 tests
green, `mypy --strict` clean, 94% coverage, public surface snapshot-pinned). The shapes
in §3–§4 below are **as-built and authoritative** — generate against them, not against
a guess. The generated package pins **`requires_lens = "^0.2"`**.

Because the Cashfree connector is **Grace-generated** (constitution-§4 DO-NOT-EDIT
marker; §4/§8 forbid hand-edits) and the `Connector` ABC reshape made the old generated
connector invalid, the Cashfree implementation must be **produced by Grace**, not
hand-written.

### What is needed from Grace (summary)

1. **Extend the rulebook/templates** to emit:
   - **capability-interface** connectors — `class <Psp>(PaymentsConnector[, MandateConnector])`, **never** bare `Connector`;
   - the **mandate lifecycle** methods (create w/ inline plan, sync, cancel, pause, resume=ACTIVATE) + the four introspection methods;
   - a **`WebhookHandlers` builder** + `register_webhook` call (§4) — the concrete shared-webhook mechanism.
   This is a **major Grace bump** (rulebook/template shape change). The CLI, pipeline, and `ClaudeCodeRunner` are unaffected.
2. **Seed `connector_docs/cashfree/`** with the Cashfree **Subscriptions** pages (§7).
3. **Regenerate Cashfree fresh** as `class Cashfree(PaymentsConnector, MandateConnector)`.
   The previous connector + its tests were **quarantined** to
   `packages/lens/legacy/cashfree_pending_regen/` and `legacy/tests_cashfree_pending_regen/`
   (the `Connector` reshape, the removed `handle_webhook`, and the `requires_lens="^0.1"`
   pin made them invalid). Use them as the **payment-side reference**; both the payment
   side and the mandate side are generated in one pass.
4. The package `__init__.py` registers **both** the connector (`ConnectorFactory.register`)
   **and** a webhook-handlers builder (`ConnectorFactory.register_webhook`).
5. Pass the gates (§9) + sandbox tests — including confirming the **UPI-Autopay `ON_HOLD`**
   failure→suspension path (lens guarantees `MANDATE_SUSPENDED` normalization on both rails;
   sandbox closes the open L9 item).

**Sequencing:** dependency order is unchanged (lock the interface, then generate) — and
the interface is now locked, so Grace can begin.

## 2. The connector model — capability interfaces over a thin base

Previously Grace emitted `class <Psp>(Connector)`. **That is now forbidden.** The
monolithic `Connector` ABC was split into a thin base + per-domain capability interfaces:

```
Connector(ABC)                       # internal base — name, base_url, close ONLY (verify lives in WebhookHandlers, §4)
  PaymentsConnector(Connector)       # create_order / sync_payment / refund / sync_refund (+ 2 props)
  MandateConnector(Connector)        # create_subscription / sync / cancel / pause / resume (+ 4 introspection)
  S2SConnector(Connector)            # FUTURE — authorize / capture / void (additive)
<Psp>(PaymentsConnector[, MandateConnector, ...])   # concrete generated class
```

**Rules Grace must follow:**

1. **Never emit a class that subclasses bare `Connector`.** Concrete connectors always implement **≥1 capability interface**.
2. A PSP supporting payments + mandates → `class Cashfree(PaymentsConnector, MandateConnector)`.
3. A PSP supporting only payments → `class <Psp>(PaymentsConnector)` (mandate methods simply absent).
4. Register the concrete class per PSP name via `ConnectorFactory.register("<psp>", <PspClass>)`
   (one class implementing N capability interfaces). A webhook-capable PSP **also** registers a
   webhook-handlers builder via `ConnectorFactory.register_webhook("<psp>", build_webhook_handlers)`
   (§4). Both calls live in the package `__init__.py`.

**Enforcement (already live in lens 0.2.0 — generated code that violates it won't load):**

- `ConnectorFactory.register` raises `ConnectorError(INVALID_REQUEST)` for a class that is a
  `Connector` but implements **no** capability interface (`isinstance(c, (PaymentsConnector, MandateConnector))`).
- The rubric (§8) adds the matching check.

**Typing:** lens targets **Python 3.11** and uses **modern typing** (`dict[str, str]`,
`X | None`, `set[...]`, `StrEnum`) — NOT the repo-wide 3.9 `Dict`/`Optional` style. Generated
code must match (mypy `--strict`, no bare generics).

## 3. The locked capability interfaces (as-built in lens 0.2.0) — implement these

**Verbatim** from `lens/connector.py`, `lens/payments_connector.py`,
`lens/mandate_connector.py`. Cashfree implements both capability interfaces.

```python
# lens/connector.py — thin base (NEVER subclassed directly by a generated class)
class Connector(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    @property
    @abstractmethod
    def base_url(self) -> str: ...
    @abstractmethod
    async def close(self) -> None: ...

# lens/payments_connector.py — payment capability (regenerate the Cashfree payment side against this)
class PaymentsConnector(Connector):
    @property
    @abstractmethod
    def supported_methods(self) -> set[PaymentMethod]: ...
    @property
    @abstractmethod
    def supports_idempotency_key(self) -> bool: ...
    @abstractmethod
    async def create_order(self, request: CreateOrderRequest) -> CreateOrderResponse: ...
    @abstractmethod
    async def sync_payment(self, request: SyncPaymentRequest) -> SyncPaymentResponse: ...
    @abstractmethod
    async def refund(self, request: RefundRequest) -> RefundResponse: ...
    @abstractmethod
    async def sync_refund(self, request: SyncRefundRequest) -> SyncRefundResponse: ...

# lens/mandate_connector.py — mandate capability (introspection are plain methods, NOT @property,
# because max_mandate_amount takes an argument)
class MandateConnector(Connector):
    @abstractmethod
    def supported_mandate_rails(self) -> set[MandateRail]: ...
    @abstractmethod
    def supports_pause(self) -> bool: ...
    @abstractmethod
    def supported_intervals(self) -> set[MandateIntervalType]: ...
    @abstractmethod
    def max_mandate_amount(self, rail: MandateRail) -> Amount | None: ...
    @abstractmethod
    async def create_subscription(self, request: CreateSubscriptionRequest) -> CreateSubscriptionResponse: ...
    @abstractmethod
    async def sync_subscription(self, request: SyncSubscriptionRequest) -> SyncSubscriptionResponse: ...
    @abstractmethod
    async def cancel_subscription(self, request: ManageMandateRequest) -> ManageMandateResponse: ...
    @abstractmethod
    async def pause_subscription(self, request: ManageMandateRequest) -> ManageMandateResponse: ...
    @abstractmethod
    async def resume_subscription(self, request: ManageMandateRequest) -> ManageMandateResponse: ...
```

**Do NOT generate** `execute_mandate_debit` or `notify_pre_debit` — periodic mode is
PSP-driven (Cashfree fires debits + sends pre-debit notifications). Those are on-demand, deferred.
**No webhook method on the connector** — webhook is the shared concern in §4.

The exact request/response **domain types** (`CreateSubscriptionRequest`, …,
`MandateDebitOutcome`, `MandateWebhookEvent`, etc., with their field lists + frozen/extra
config) are locked in `lens.domain_types` and enumerated in the orbit contract
`2026-05-30-lens-mandate-contract-for-orbit.md` §3.3. Import them from `lens.domain_types` /
`lens` — do not redeclare them.

**Mapping notes for the implementation:**
- `resume_subscription` → Cashfree Manage `ACTIVATE` (no separate RESUME verb);
  `ManageMandateRequest.effective_at` → `action_details.next_scheduled_time`.
- `create_subscription` **inlines the plan** (`plan_details` inline, not a pre-created `plan_id`) — orbit is pricing-agnostic.
- Forward `idempotency_key` as Cashfree's idempotency token on every state-changing call.

## 4. Webhook — the shared `WebhookRouter`, fed by a generated `WebhookHandlers` builder

A Cashfree merchant has **one webhook endpoint + one signature scheme** carrying both
payment and subscription events. The router is **lens-core**; what Grace generates is the
**`WebhookHandlers` builder** (verify + classify + the two parsers) and its registration.

**Lens-core types (already shipped — generate against them, do not redeclare):**

```python
# lens/webhook.py  (lens 0.2.0, verbatim)
class WebhookFamily(StrEnum):
    PAYMENT = "PAYMENT"
    MANDATE = "MANDATE"

@dataclass(frozen=True)
class WebhookHandlers:
    verify: Callable[[bytes, dict[str, str]], bool]            # closes over the PSP secret
    classify: Callable[[bytes], WebhookFamily]                 # reads the event "type" -> family
    parse_payment: Callable[[bytes], PaymentWebhookEvent] | None = None
    parse_mandate: Callable[[bytes], MandateWebhookEvent] | None = None

class WebhookRouter:
    def __init__(self, handlers: WebhookHandlers) -> None: ...
    async def handle(self, raw_payload: bytes, headers: dict[str, str]) -> PaymentWebhookEvent | MandateWebhookEvent:
        # verify -> WEBHOOK_SIGNATURE_FAILED on bad sig; classify; dispatch to the family parser;
        # raise NOT_SUPPORTED if the classified family has no parser.
        ...
```

**Factory entry points (lens-core, already shipped):**

```python
ConnectorFactory.register_webhook(name: str, build_handlers: Callable[[ConnectorConfig], WebhookHandlers]) -> None
ConnectorFactory.create_webhook_router(config: ConnectorConfig) -> WebhookRouter   # orbit calls this
```

**What Grace MUST generate for the PSP package** (e.g. `connectors/cashfree/webhooks.py`):

```python
def build_webhook_handlers(config: ConnectorConfig) -> WebhookHandlers:
    return WebhookHandlers(
        verify=lambda raw, headers: verify_signature(config, raw, headers),   # shared HMAC; family-agnostic
        classify=_classify,            # SUBSCRIPTION_* -> MANDATE ; PAYMENT_*/REFUND_*/ORDER_* -> PAYMENT
        parse_payment=_parse_payment_webhook,   # bytes -> PaymentWebhookEvent
        parse_mandate=_parse_mandate_webhook,   # bytes -> MandateWebhookEvent
    )
```
and register it in `connectors/cashfree/__init__.py`:
`ConnectorFactory.register_webhook("cashfree", build_webhook_handlers)`.

Notes:
- **Verification is shared/family-agnostic** (the `auth.verify_signature` HMAC scheme) — confirm
  it holds for the **latest** subscription webhook version; the older `subscriptionsv1` embedded
  the signature in the body and must **not** be used.
- **Parsing is domain-owned** — `_parse_payment_webhook` returns `PaymentWebhookEvent` (the
  renamed-from-`WebhookEvent` model), `_parse_mandate_webhook` returns `MandateWebhookEvent`.
- The router is **not** a method on either connector class (neither can parse the other's events).
- Orbit ingests via a single call: `ConnectorFactory.create_webhook_router(config).handle(raw, headers)`,
  then branches on the returned type.

## 5. What to generate for Cashfree (file-by-file)

```
connectors/cashfree/
  __init__.py     # requires_lens = "^0.2"
                  # ConnectorFactory.register("cashfree", Cashfree)
                  # ConnectorFactory.register_webhook("cashfree", build_webhook_handlers)
  connector.py    # class Cashfree(PaymentsConnector, MandateConnector): payment flows + mandate lifecycle
  auth.py         # build_auth_headers + verify_signature (shared; latest subscription webhook scheme)
  models.py       # + subscription / plan / subscription-webhook wire models
  status_map.py   # subscription_status→MandateStatus, subscription events→WebhookEventType,
                  #   Cashfree failure free-text→(PaymentFailureCode, FailureClass)   (per §6)
  webhooks.py     # build_webhook_handlers + _classify + _parse_payment_webhook + _parse_mandate_webhook
```

- Generate the **payment side fresh too** (the old `Cashfree(Connector)` is invalid). The
  quarantined `legacy/cashfree_pending_regen/{connector,auth,models,status_map}.py` are the
  payment-side reference; the regenerated payment connector should diff from them only where the
  base class changed (`Connector` → `PaymentsConnector`) and where `handle_webhook` moved out to
  `webhooks.py`/the router.
- Per-PSP tests land at `tests/integration/connectors/cashfree/` (the quarantined
  `legacy/tests_cashfree_pending_regen/` are the payment-test reference).
- Whether mandate methods live in `connector.py` or a sibling `mandates.py` is Grace's call;
  one registered class per PSP either way.

## 6. Cashfree → lens normalization tables (authoritative — drive `status_map.py`)

**Subscription status → `MandateStatus`:**

| Cashfree `subscription_status` | `MandateStatus` |
|---|---|
| `INITIALIZED`, `BANK_APPROVAL_PENDING` | `PENDING_AUTHORIZATION` |
| `ACTIVE` | `ACTIVE` |
| `PAUSED` (merchant), `CUSTOMER_PAUSED` (customer) | `PAUSED` |
| `ON_HOLD` | `SUSPENDED` |
| `COMPLETED` | `COMPLETED` |
| `CANCELLED`, `CUSTOMER_CANCELLED` | `CANCELLED` |
| `EXPIRED` | `EXPIRED` |
| `CARD_EXPIRED` | `SUSPENDED` (instrument dead; needs re-auth) |
| `LINK_EXPIRED` | `FAILED` (auth link lapsed pre-approval) |
| auth `FAILED` (on `SUBSCRIPTION_AUTH_STATUS`) | `FAILED` |

**Webhook event → `WebhookEventType`:**

| Cashfree event (condition) | `WebhookEventType` |
|---|---|
| `SUBSCRIPTION_AUTH_STATUS` (authorization_status=ACTIVE) | `MANDATE_AUTHORIZED` |
| `SUBSCRIPTION_AUTH_STATUS` (FAILED) | `MANDATE_REJECTED` |
| `SUBSCRIPTION_PAYMENT_SUCCESS` | `MANDATE_DEBIT_SUCCESS` |
| `SUBSCRIPTION_PAYMENT_FAILED` | `MANDATE_DEBIT_FAILED` (`psp_attempt = retry_attempts`) |
| `SUBSCRIPTION_PAYMENT_CANCELLED` | `MANDATE_DEBIT_FAILED` (`failure_code=USER_CANCELLED`) |
| `SUBSCRIPTION_PAYMENT_NOTIFICATION_INITIATED` | `MANDATE_DEBIT_NOTIFIED` *(orbit accepted — emit)* |
| `SUBSCRIPTION_STATUS_CHANGED` → `ACTIVE` (from paused) | `MANDATE_RESUMED` |
| `SUBSCRIPTION_STATUS_CHANGED` → `CUSTOMER_PAUSED` | `MANDATE_PAUSED` |
| `SUBSCRIPTION_STATUS_CHANGED` → `ON_HOLD` | `MANDATE_SUSPENDED` |
| `SUBSCRIPTION_STATUS_CHANGED` → `CANCELLED` | `MANDATE_CANCELLED` |
| `SUBSCRIPTION_STATUS_CHANGED` → `CUSTOMER_CANCELLED` | `MANDATE_REVOKED` |
| `SUBSCRIPTION_STATUS_CHANGED` → `EXPIRED` / `CARD_EXPIRED` | `MANDATE_EXPIRED` |
| `SUBSCRIPTION_STATUS_CHANGED` → `COMPLETED` | `MANDATE_COMPLETED` |
| `SUBSCRIPTION_CARD_EXPIRY_REMINDER` | `MANDATE_EXPIRING_SOON` *(orbit accepted — emit)* |
| `SUBSCRIPTION_REFUND_STATUS` | auth-amount refund — reuse refund handling; out of core mandate scope |

> There is **no** Cashfree "retries-exhausted / final-failure" event. Finality is derived by the
> consumer from `MANDATE_SUSPENDED` (← `ON_HOLD`) plus `psp_attempt`. Do not synthesize a
> `*_FAILED_FINAL` event.
>
> `ON_HOLD` is **payment-failure-only** (merchant/customer pauses are `PAUSED`/`CUSTOMER_PAUSED`),
> so `MANDATE_SUSPENDED` unambiguously means a payment-failure suspension — no reason field exists
> or is needed. Documented for NACH + Card SI; **normalize UPI Autopay debit failure to
> `MANDATE_SUSPENDED` too** (confirm the exact UPI path in sandbox).

**Rail → Cashfree `payment_methods`:** `UPI_AUTOPAY → [upi]`, `CARD_EMANDATE → [card]`
(eNACH/pNACH bank rails are out of scope this phase).

**Create-request field mapping:**

| lens field | Cashfree field |
|---|---|
| `amount` (`Amount`) | `plan_details.plan_recurring_amount` |
| `max_amount` (`Amount`) | `plan_details.plan_max_amount` |
| `interval_type` / `interval_count` | `plan_interval_type` / `plan_intervals` |
| `max_cycles` | `plan_max_cycles` |
| `first_charge_at` | `subscription_first_charge_time` (PERIODIC only) |
| `expires_at` | `subscription_expiry_time` |
| `customer_contact.email` / `.phone` | `customer_details.customer_email` / `customer_phone` (both required) |
| `return_url` | `subscription_meta.return_url` |
| (notification) | `subscription_meta.notification_channel = [SMS, EMAIL]` |
| `rail` | `authorization_details.payment_methods` |
| `idempotency_key` | Cashfree idempotency token header |

**Failure free-text → `(PaymentFailureCode, FailureClass)`** (Cashfree
`failure_details.failure_reason` is free text; map on substring, default `UNKNOWN`):

| signal | code | class |
|---|---|---|
| insufficient funds | `INSUFFICIENT_FUNDS` | RETRIABLE |
| network / timeout | `NETWORK_ERROR` | RETRIABLE |
| psp / system error | `PSP_ERROR` | RETRIABLE |
| card declined | `CARD_DECLINED` | TERMINAL |
| invalid instrument | `INVALID_INSTRUMENT` | TERMINAL |
| mandate revoked at bank/UPI | `MANDATE_REVOKED` | TERMINAL |
| mandate paused | `MANDATE_PAUSED` | TERMINAL |
| mandate expired | `MANDATE_EXPIRED` | TERMINAL |
| mandate/subscription not found | `MANDATE_NOT_FOUND` | TERMINAL |
| amount exceeds cap | `DEBIT_LIMIT_EXCEEDED` | TERMINAL |
| (unmatched) | `UNKNOWN` (+ raw in `failure_reason`) | — |

> `FailureClass`/`FAILURE_CLASS` are **published data only** — lens never branches on them.
> The connector sets `MandateDebitOutcome.failure_code`; orbit reads `FAILURE_CLASS[code]`.

## 7. Source docs to add to `connector_docs/cashfree/`

Add the latest Subscriptions pages so Grace has the source (keep alongside the existing payments docs):

- `subscription/overview`, `subscription/plans/create` + `plans/fetch`
- `subscription/mandate/create`, `mandate/fetch`, `mandate/manage`, `mandate/payment-methods`
- `subscription/payment/fetch`, `payment/fetch-payments-for-mandate`
- the **latest** subscription **webhooks** page (event names: `SUBSCRIPTION_AUTH_STATUS`,
  `SUBSCRIPTION_PAYMENT_SUCCESS/FAILED/CANCELLED`, `SUBSCRIPTION_PAYMENT_NOTIFICATION_INITIATED`,
  `SUBSCRIPTION_STATUS_CHANGED`, `SUBSCRIPTION_CARD_EXPIRY_REMINDER`, `SUBSCRIPTION_REFUND_STATUS`)

> Pin the **latest webhook version** when configuring; the older `subscriptionsv1` webhooks use
> different event names (`SUBSCRIPTION_NEW_PAYMENT`, …) and a body-embedded signature.

## 8. Rulebook + rubric updates

Rulebook/templates:
- Target capability interfaces (`PaymentsConnector` / `MandateConnector`), never bare `Connector`.
- Mandate-flow templates (create with inline plan, sync, cancel, pause, resume=ACTIVATE).
- A `build_webhook_handlers` + `register_webhook` template (§4); mandate + payment parsers.
- `status_map.py` extended per §6.
- Modern typing (Python 3.11; no `Dict`/`Optional`/bare generics) + `requires_lens = "^0.2"`.

Rubric (`SUBPROJECT_GRACE_CODEGEN.md` §5, "Public-surface conformance"):
- Generated class implements ≥1 capability interface, **not** bare `Connector`.
- Mandate methods + the four introspection methods present for mandate-capable PSPs.
- `__init__.py` calls **both** `register` and `register_webhook`; `build_webhook_handlers` present.
- Mandate + debit webhook events covered by tests; `status_map.py` maps every documented subscription
  status + event (unmapped → `MandateStatus`/`UNKNOWN` fallbacks with a warning).

Marker format (§4 of the constitution) unchanged.

## 9. Acceptance

- `grace generate cashfree` emits `class Cashfree(PaymentsConnector, MandateConnector)` with
  `requires_lens = "^0.2"`, registered once via `register`, **and** a `build_webhook_handlers`
  registered via `register_webhook`. No bare-`Connector` subclassing.
- `mypy --strict` clean (modern typing); `pytest --cov` ≥ 80%; rubric ≥ 60/100 with the new checks.
- Mandate flow tests pass (create both rails, sync, cancel, pause, resume) + webhook tests
  (authorize, debit-success, debit-decline retriable, `ON_HOLD`→suspended, tampered→`WEBHOOK_SIGNATURE_FAILED`,
  single-entry router dispatch across both families).
- The regenerated package **un-quarantines** Cashfree: `connectors/cashfree/` exists again and the
  legacy-isolation test (`tests/unit/test_legacy_isolation.py`) is updated/removed accordingly.
- Sandbox (L9): authorize + debit-success + debit-decline simulated for both rails; the UPI-Autopay
  `ON_HOLD`→`MANDATE_SUSPENDED` path confirmed (the one open normalization item owed to orbit).
