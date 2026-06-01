# Orbit Constitution

**Status**: v0.6 — Connector version gate removed (connectors ship bundled with lens). Periodic subscription-mandate support (Phase 3); capability-interface model; shared WebhookRouter.
**Date**: 2026-06-01.
**Owner**: Sarthak (engineering@symplora.com).
**Scope**: governs all sub-projects under the Orbit umbrella. Sub-project specs inherit by cross-reference; conflicts resolve in favor of this document until revised.

Changes to this document require a dated changelog entry at the bottom and, for any section marked **locked**, the coordination steps described in §8.

---

## §1. Purpose & scope

**Orbit** is Symplora's unified financial-operations product. Apps (Symplora ATS, Hikara, future products) talk to Orbit whenever money needs to move.

**v1 scope** centers on payments through PSP hosted checkout. Two first-class entities:

- **Order** (a.k.a. PaymentRequest) — the merchant's expression of intent: "I want this amount from a payer, for this purpose, with these allowed methods." One Order corresponds 1:1 to a PSP-side order. Owns the payment_link and the timeline of attempts against it.
- **PaymentAttempt** (a.k.a. Transaction) — one specific attempt by the payer to pay against an Order. Created when the PSP tells us a payment was initiated. One Order has 0..N PaymentAttempts. The Order is `PAID` iff at least one PaymentAttempt is `SUCCESS`.

Plus a third entity that hangs off the successful attempt:

- **Refund** — initiated by the merchant against the successful PaymentAttempt under an Order. One Order has 0..N Refunds. Cumulative refund amount can be at most the paid amount.

**Phase 3 (now in scope)**: periodic subscription mandates — UPI Autopay and card e-mandate, INR, periodic/PSP-scheduled debit mode. Lens is stateless; Cashfree owns the debit schedule, retry, and notification. On-demand / merchant-triggered debit (`execute_mandate_debit` / `notify_pre_debit`) remains out of scope.

**Out of scope for v1** but on the longer-term roadmap: on-demand mandate debit, billing-cycle logic, invoice generation, **direct-API / server-to-server payment flows** (`authorize`, `capture`, `void` with raw instrument data — see `FUTURE_S2S_INTERFACE.md`). Each lands as a follow-up product slice gated by v1 stability. Anything else (payouts, disputes, tax, KYC, settlement reconciliation) is also out of scope until explicitly added by a future revision.

To deliver Orbit, two supporting sub-projects exist underneath:

- a stateless **Lens** library that gives Orbit a single Python API across all PSPs,
- a build-time tool called **Grace** that generates new PSP connectors from API documentation.

Each has a full spec of its own (`SUBPROJECT_*.md` (sibling files)). This constitution governs them collectively.

---

## §2. Three sub-projects

Orbit is composed of three named sub-projects. Each has its own home, owner, and locked-spec file. Implementation agents own at most one sub-project at a time.

**Orbit (the product)** — Layer 3.
- Location: `/Users/sarthak/PycharmProjects/symplora/orbit/`
- Role: the HTTP/business API consumer apps call. Owns: HTTP server, Order + PaymentAttempt + Refund ledger, state machines, webhook receiver, idempotency store, persistence, business validation. Grows to host subscriptions/billing/invoices later.
- Spec: `SUBPROJECT_ORBIT_PRODUCT.md`

**Lens (the unified PSP library)** — Layer 2.
- Location: `/Users/sarthak/PycharmProjects/symplora/sylibs/packages/lens/` — a package inside the `sylibs` monorepo. Published to Symplora's private PyPI (SyPI) as `lens`.
- Role: a stateless Python library. Exposes `PaymentsFacade`, `MandatesFacade`, `ConnectorFactory`, a `Connector` thin-base ABC with `PaymentsConnector` / `MandateConnector` capability interfaces, a shared `WebhookRouter`, and the domain types (request/response models per flow, the `PaymentAttempt` model, mandate domain types, `PaymentWebhookEvent` / `MandateWebhookEvent`, error types). Hosts the per-PSP connector implementations (Cashfree first). Talks to PSPs via httpx. No DB. No HTTP server. No global mutable state.
- **References juspay-prism's `crates/` for inspiration on the registry pattern and error normalization — but does not mirror it line-for-line.** Juspay-prism's Rust trait generics (`ConnectorIntegrationV2<Flow, RCD, Req, Resp>`, `RouterData`, phantom flow types) are deliberately not ported. Pythonic equivalent: one `Connector` class per PSP with four async flow methods + webhook + close. Detailed in `SUBPROJECT_LENS.md`.
- Spec: `SUBPROJECT_LENS.md`

**Grace (the codegen tool)** — Layer 1, build-time only.
- Location: `/Users/sarthak/PycharmProjects/references/grace/` — the team's fork (`github.com/HR-intention/grace`) of `juspay-prism/grace/` (`github.com/juspay/hyperswitch-prism`). Same project, different remote.
- Role: CLI tool that reads a PSP's API documentation and generates a Python connector implementing Lens's `Connector` ABC. Upstream Grace already does this for Rust. The team's fork extends Grace to emit Python (via the `python-support` branch). **v1 ships with one code-generation backend: Claude Code, invoked via the local CLI session.** No other AI providers, no abstraction layer over the AI vendor.
- Spec: `SUBPROJECT_GRACE_CODEGEN.md`

Sub-project boundaries are **locked**. A change crossing a boundary requires updating this constitution AND the sub-project specs on both sides.

---

## §3. Runtime architecture

```
        ┌─────────────────────────────────────────┐
        │ Consumer apps (Symplora ATS, Hikara, …) │
        └─────────────────┬───────────────────────┘
                          │ HTTP/JSON
                          ▼
        ┌─────────────────────────────────────────┐
        │ Orbit                                   │
        │  • HTTP server (FastAPI)                │
        │  • Orders + PaymentAttempts + Refunds   │
        │    ledger and state machines            │
        │  • Webhook receiver (public endpoint)   │
        │  • Idempotency store                    │
        │  • Inline-resume + housekeeping cron    │
        │  • Persistence (Postgres)               │
        └─────────────────┬───────────────────────┘
                          │ in-process Python import
                          ▼
        ┌─────────────────────────────────────────┐
        │ Lens (library, stateless)               │
        │  • PaymentsFacade  (thin wrapper:       │
        │     logging + error normalization)      │
        │  • MandatesFacade  (same pattern)       │
        │  • Connector  (thin base ABC)           │
        │  • PaymentsConnector(Connector)         │
        │     - create_order / sync_payment       │
        │     - refund / sync_refund              │
        │  • MandateConnector(Connector)          │
        │     - create/sync/cancel/pause/resume   │
        │     - introspection (rails/intervals/…) │
        │  • WebhookRouter (verify once, route    │
        │     by family → PaymentWebhookEvent |   │
        │     MandateWebhookEvent)                │
        │  • ConnectorFactory (registry)          │
        │  • Domain types incl. PaymentAttempt,   │
        │    mandate types, FAILURE_CLASS         │
        └─────────────────┬───────────────────────┘
                          │ httpx (each Connector owns its client)
                          ▼
        ┌─────────────────────────────────────────┐
        │ PSP APIs (Cashfree, Razorpay, Stripe …) │
        └─────────────────────────────────────────┘
```

**Invariants**:

- Lens never opens a listening socket. Pure Python library.
- Lens never reads or writes a database. Stateless.
- One `Connector` class per PSP. Each class owns its own httpx client and implements at least one capability interface (`PaymentsConnector`, `MandateConnector`, or both). `ConnectorFactory.register` enforces this — bare `Connector` subclasses that implement no capability interface are rejected with `INVALID_REQUEST`. `handle_webhook` is no longer on any connector; webhook handling lives in the shared `WebhookRouter`.
- Cross-cutting concerns (structured logging, retries, error normalization, PII masking) are applied via:
  - `PaymentsFacade` (thin wrapper around the `Connector`): binds request id, logs start/end, normalizes any leaking exceptions into `ConnectorError`.
  - The httpx client (configured per Connector): retry transport, timeout, event hooks for masked logging.
  - The `Maskable[T]` type wrapper: any PII field declared `Maskable[...]` stringifies as `***`, so it can't accidentally leak into a log line.
- Orbit is the only process boundary. All HTTP ingress (consumer requests + PSP webhooks) terminates at Orbit.
- **Orbit-first persistence.** Every external state-changing action (PSP `create_order`, `refund`) is preceded by writing an Orbit row. The Orbit record is the source of truth for "did we already start this?". See `SUBPROJECT_ORBIT_PRODUCT.md` for the recovery flow.
- Webhook flow: PSP → Orbit's public webhook endpoint → Orbit calls `WebhookRouter.handle(raw_payload, headers)` (obtained via `ConnectorFactory.create_webhook_router(config)`) → the router verifies the PSP signature once and routes by event family → returns `PaymentWebhookEvent | MandateWebhookEvent` → Orbit dedups against its own store → Orbit updates the relevant entity (Order/PaymentAttempt/Refund for payment events; subscription record for mandate events). Migration note: `PaymentsFacade.incoming_webhook` has been removed; callers must obtain a `WebhookRouter` from the factory instead.

**Ruled out for v1**:

- Apps importing Lens directly. Only Orbit imports it.
- Lens maintaining dedup state.
- Lens exposing an HTTP service. The existing FastAPI scaffolding in Plan C is removed or relocated to a dev-only harness (see §10 OQ-2).
- **Direct-API / server-to-server flows.** Specified for future reference in `FUTURE_S2S_INTERFACE.md`; not implemented in v1.

---

## §4. Build-time architecture

```
   ┌───────────────────────────────────────────┐
   │ PSP API documentation                     │
   │  (URLs, OpenAPI specs, local files)       │
   └─────────────────┬─────────────────────────┘
                     │ (developer / CI runs)
                     ▼
   ┌───────────────────────────────────────────┐
   │ Grace (CLI tool)                          │
   │   1. Gather context (rulebooks + PSP docs)│
   │   2. Invoke Claude Code with the context  │
   │   3. Run quality gates on the output      │
   └─────────────────┬─────────────────────────┘
                     │ writes files into
                     ▼
   ┌───────────────────────────────────────────┐
   │ lens/                                     │
   │   lens/connectors/<psp>/                  │
   │    ├── connector.py  (the Connector impl) │
   │    ├── auth.py                            │
   │    ├── models.py                          │
   │    └── tests/                             │
   └─────────────────┬─────────────────────────┘
                     │
                     ▼
   ┌───────────────────────────────────────────┐
   │ Generated code is COMMITTED to git        │
   │ Reviewed like any other code              │
   │ Regenerated on PSP API changes (manual)   │
   └───────────────────────────────────────────┘
```

**Grace never runs in production.** All invocations happen on a developer machine or in CI. Generated code is treated as source: committed, reviewed, type-checked, tested. No "regenerate on the fly" at runtime.

**Generated-file marker** (**locked**). Every Python file Grace writes must begin with this header block (before the module docstring, after any encoding line):

```python
# ──────────────────────────────────────────────────────────────────────
#  DO NOT EDIT — autogenerated by Grace.
#  Source: <PSP name> <version/commit of the source API docs Grace used>
#  Generated: <UTC ISO-8601 timestamp>
#  Generator: grace <grace version>
#  Regenerate: grace generate <psp> --from <source>
# ──────────────────────────────────────────────────────────────────────
```

The marker is mandatory. Quality gates fail if it is missing or malformed. Hand-edits to files bearing this marker are forbidden by convention; if a generated file needs changes, fix Grace (the rulebook or the source spec) and regenerate.

**Quality gates** are non-negotiable on the generated package:

- `mypy --strict` — zero errors, no `Any`.
- `pytest --cov` — ≥ 80% line coverage on the generated connector package.
- Quality rubric — ≥ 60/100 across the dimensions defined in `SUBPROJECT_GRACE_CODEGEN.md`.

If any gate fails, Grace surfaces the failure and does not write the package to its final destination.

---

## §5. Public contracts

These are the named interfaces between sub-projects. **Locked** — SemVer-major bump to break.

**`PaymentsFacade`** (Lens → Orbit). The class Orbit holds and calls for payment flows. Async methods: `create_order`, `sync_payment`, `refund`, `sync_refund`, `close`. Thin wrapper that adds request-id binding, structured logging, and error normalization around a `PaymentsConnector`. `incoming_webhook` has been removed from this facade; webhook handling is now the shared `WebhookRouter` (see below). Signatures pinned in `SUBPROJECT_LENS.md`.

**`ConnectorFactory`** (Lens → Orbit). Class-method API: `register(name, connector_cls)`, `create(config) -> Connector`, `list_connectors() -> list[str]`, `create_payments_facade(config) -> PaymentsFacade`, `create_mandates_facade(config) -> MandatesFacade`, `create_webhook_router(config) -> WebhookRouter`, `register_webhook(name, build_handlers)`. Generated connector modules self-register via `register` and `register_webhook` on import. `register` validates that the class's `name` property matches the registry key and that the class implements at least one capability interface (`PaymentsConnector` or `MandateConnector`); raises `ConnectorError(reason=INVALID_REQUEST)` on failure. There is no connector-version gate: generated connectors ship bundled inside the `lens` wheel, so a connector cannot disagree with the running Lens version. `create_mandates_facade` raises `ConnectorError(reason=NOT_SUPPORTED)` if the registered connector does not implement `MandateConnector`.

**`Connector`** thin-base ABC (Lens → per-PSP implementations). Never implemented directly. Properties: `name`, `base_url`. Async method: `close`. Each PSP connector class implements one or more capability interfaces that extend this base:

- **`PaymentsConnector(Connector)`** — the payment-flow capability. Properties: `supported_methods`, `supports_idempotency_key`. Async methods: `create_order`, `sync_payment`, `refund`, `sync_refund`.
- **`MandateConnector(Connector)`** — the mandate/subscription capability. Plain methods (introspection, one takes a `rail` argument): `supported_mandate_rails`, `supports_pause`, `supported_intervals`, `max_mandate_amount`. Async methods (lifecycle): `create_subscription`, `sync_subscription`, `cancel_subscription`, `pause_subscription`, `resume_subscription`.

Webhook handling is no longer on any connector — it belongs to the shared `WebhookRouter` (see below). Each Connector owns its own `httpx.AsyncClient`.

**`MandatesFacade`** (Lens → Orbit). The class Orbit holds for mandate/subscription flows. Async lifecycle methods: `create_subscription`, `sync_subscription`, `cancel_subscription`, `pause_subscription`, `resume_subscription`, `close`. Sync introspection pass-throughs: `supported_mandate_rails`, `supports_pause`, `supported_intervals`, `max_mandate_amount`. Signatures pinned in `SUBPROJECT_LENS.md`.

**`WebhookRouter`** / **`WebhookHandlers`** / **`WebhookFamily`** (Lens → Orbit). The shared webhook handling surface. Orbit obtains a `WebhookRouter` via `ConnectorFactory.create_webhook_router(config)`. The router's single async method `handle(raw_payload: bytes, headers: dict[str, str]) -> PaymentWebhookEvent | MandateWebhookEvent` verifies the PSP signature once (via the `WebhookHandlers.verify` callable) and routes by event family (`WebhookFamily.PAYMENT` or `WebhookFamily.MANDATE`) to the appropriate parser. `WebhookHandlers` is a frozen dataclass holding the `verify`, `classify`, `parse_payment`, and `parse_mandate` callables supplied by the PSP package. Unknown family raises `ConnectorError(reason=NOT_SUPPORTED)`. Signatures pinned in `SUBPROJECT_LENS.md`.

**Domain types** (Lens → Orbit, Lens → Grace). Frozen Pydantic models that flow across the Orbit ↔ Lens boundary. Key types:

- Per-flow request/response models (payments): `CreateOrderRequest`/`CreateOrderResponse`, `SyncPaymentRequest`/`SyncPaymentResponse`, `RefundRequest`/`RefundResponse`, `SyncRefundRequest`/`SyncRefundResponse`.
- `PaymentAttempt` — one attempt by a payer against an Order. Returned in lists from `sync_payment` and individually inside `PaymentWebhookEvent`.
- `RefundEvent` — one refund-status update, carried inside `PaymentWebhookEvent` for refund-related events.
- `PaymentWebhookEvent` — the parsed, normalized form of an inbound PSP payment/refund event (renamed from `WebhookEvent`); carries `attempt: PaymentAttempt | None` and `refund: RefundEvent | None` depending on the event type.
- Per-flow request/response models (mandates): `CreateSubscriptionRequest`/`CreateSubscriptionResponse`, `SyncSubscriptionRequest`/`SyncSubscriptionResponse`, `ManageMandateRequest`/`ManageMandateResponse`. Common base: `MandateRequestCommon` (fields: `merchant_id` only — no `order_id`; mandates are not orders). Supporting types: `CustomerContact` (email + phone), `ApprovalHandle` (type/url/session_id/raw).
- `MandateDebitOutcome` — outcome of one PSP-scheduled debit attempt. Frozen. Carried on `MandateWebhookEvent.debit` and `SyncSubscriptionResponse.last_debit`.
- `MandateWebhookEvent` — the parsed, normalized form of an inbound PSP mandate/subscription event; carries `mandate_status`, `debit: MandateDebitOutcome | None`, and `psp_mandate_ref`.
- Three separate status enums (no overloaded "AttemptStatus"):
  - `OrderStatus`: `CREATED`, `PAID`, `PARTIALLY_REFUNDED`, `REFUNDED`, `EXPIRED`, `FAILED`.
  - `PaymentAttemptStatus`: `PENDING`, `SUCCESS`, `FAILED`.
  - `RefundStatus`: `PENDING`, `SUCCESS`, `FAILED`.
- `PaymentFailureCode` enum — a locked taxonomy for *why* a payment or mandate debit failed. Original values: `USER_DROPPED`, `USER_CANCELLED`, `CARD_DECLINED`, `INSUFFICIENT_FUNDS`, `AUTHENTICATION_FAILED`, `FRAUD_BLOCKED`, `FRAUD_REVIEW_PENDING`, `INVALID_INSTRUMENT`, `PSP_ERROR`, `NETWORK_ERROR`, `UNKNOWN`. Extended in v0.2.0 with mandate values: `MANDATE_REVOKED`, `MANDATE_PAUSED`, `MANDATE_EXPIRED`, `MANDATE_NOT_FOUND`, `DEBIT_LIMIT_EXCEEDED`. Carried on `PaymentAttempt.failure_code` and `MandateDebitOutcome.failure_code`.
- New mandate enums: `MandateRail` (`UPI_AUTOPAY`, `CARD_EMANDATE`), `MandateStatus` (8 values), `MandateIntervalType` (`DAY`, `WEEK`, `MONTH`, `YEAR`), `MandateDebitStatus` (`PENDING`, `SUCCESS`, `FAILED`). Extended `WebhookEventType` with 13 `MANDATE_*` values.
- `FailureClass` enum (`RETRIABLE`, `TERMINAL`) + `FAILURE_CLASS` (frozen `MappingProxyType[PaymentFailureCode, FailureClass]`) — published classification data; lens never acts on it. Orbit reads it to decide `charge_failed` vs `charge_failed_final`.
- Shared types: `Amount` (= minor units + currency), `Currency`, `PaymentMethod`, `Maskable[T]`, `ConnectorError`, `ConnectorErrorReason`.

`PaymentMethod` in v1 is used as an allow-list constraint passed to the PSP (for hosted-checkout method allow-listing) and as a value read back on a successful attempt. Never expanded into a per-method request builder.

Pinned in `SUBPROJECT_LENS.md`.

A breaking change in any contract requires:

1. A revision to this constitution (dated changelog entry).
2. A revision to both sub-project specs on the boundary.
3. A migration plan for all generated connectors and for Orbit.

Non-breaking changes (additive fields, additive flows that don't replace existing ones — e.g., adding `authorize`/`capture`/`void` later for s2s support per `FUTURE_S2S_INTERFACE.md` — additive `PaymentFailureCode` values, additive registered connectors) follow the sub-project spec process directly.

---

## §6. Non-functional ground rules

Apply across all three sub-projects unless a sub-project spec is explicitly stricter.

- **Python ≥ 3.11.** Modern type syntax (`X | Y`, `list[X]`). Async everywhere on the request/response path; sync work via `asyncio.to_thread`.
- **`mypy --strict` mandatory.** No `Any`. `# type: ignore` requires a scoped, commented reason.
- **Pydantic v2 at every public boundary.** `ConfigDict(extra="forbid", frozen=True)` on requests; `frozen=False` only where post-creation field assignment is required. No raw dicts crossing public APIs.
- **Structured JSON logging only.** The logging library is a per-sub-project choice — Orbit uses stdlib `logging` with a `sykit`-based JSON formatter (not `structlog`). PII fields typed `Maskable[T]` so they stringify as `***`. Forbidden in logs even masked: full PAN, CVV, full bank account numbers.
- **State discipline.** Lens is stateless (no DB, no file I/O beyond httpx). Orbit owns persistent state. The only global mutable state allowed in Lens is `ConnectorFactory._registry` (write-once at import).
- **Errors.** Public APIs raise typed errors with `reason` enums (`ConnectorError`, `OrbitError`). Provider-specific errors are normalized inside each `Connector` method or by `PaymentsFacade`, never bubbled up raw.
- **Orbit-first persistence.** Every action that mutates external state (create_order at the PSP, refund at the PSP) is preceded by a local Orbit row write. Recovery and idempotency depend on this discipline.
- **Tests.** Unit + integration via `httpx.MockTransport`. Per-sub-project line coverage ≥ 80%. Contract tests pin each sub-project's public surface against snapshot files so accidental drift fails CI loudly. Live sandbox calls only in an optional CI job.
- **Observability.** Every flow invocation emits structured start/end records with `flow`, `connector_name`, `request_id`, latency, outcome.

---

## §7. v1 scope (in / out)

**In scope for v1**

*Orbit (product):*

- HTTP API anchored on the two first-class entities: Orders and PaymentAttempts (plus Refunds against the successful PaymentAttempt).
- Order ledger and state machine: `CREATED → PAID → (PARTIALLY_REFUNDED | REFUNDED)`, with `EXPIRED` and `FAILED` terminals.
- PaymentAttempt ledger and state machine: `PENDING → (SUCCESS | FAILED)`, with `failure_code` carrying granularity (`USER_DROPPED`, `CARD_DECLINED`, etc.).
- Refund ledger and state machine: `PENDING → (SUCCESS | FAILED)`.
- Orbit-first creation flow with inline-resume recovery for orders stuck in flight (a retry with the same idempotency key resumes against the same deterministic PSP key); an `orbit-housekeeping` cron sweeps expiries and prunes idempotency keys.
- Idempotency on every state-mutating endpoint.
- Webhook receiver endpoint that delegates verification + parsing to Lens, dedups locally, and updates the relevant entity.
- One configured PSP (Cashfree) wired end-to-end.

*Lens:*

- `Connector` thin-base ABC + `PaymentsConnector` / `MandateConnector` capability interfaces + `PaymentsFacade` + `MandatesFacade` + `ConnectorFactory` + `WebhookRouter` + domain types (including `PaymentAttempt`, the three payment status enums, `PaymentFailureCode`, mandate domain types, `FailureClass`, `FAILURE_CLASS`).
- One PSP: Cashfree (quarantined pending Grace regeneration against 0.2.0 ABCs).
- **Hosted-checkout / session-based integration only.** v1 does not accept raw card, UPI, wallet, or other instrument data at the Lens boundary.
- Four payment flow methods: `create_order`, `sync_payment`, `refund`, `sync_refund`. Five mandate lifecycle methods: `create_subscription`, `sync_subscription`, `cancel_subscription`, `pause_subscription`, `resume_subscription`. Lifecycle management: `close`.
- `sync_payment` returns the order's overall `OrderStatus` and the list of `PaymentAttempt`s the PSP knows about.
- `WebhookRouter.handle(raw_payload, headers)` verifies the signature once and returns `PaymentWebhookEvent | MandateWebhookEvent` by event family. (`PaymentsFacade.incoming_webhook` is retired.)
- Periodic mandate mode (UPI Autopay + card e-mandate, INR): Lens is stateless; Cashfree owns schedule, retry, and notification.
- httpx-based HTTP execution with timeouts, retries (configurable, idempotency-key passthrough), structured logging.

*Grace:*

- `python-support` branch landed: emits Python conforming to Lens's ABC.
- One AI backend: **Claude Code** (invoked via the local CLI session).
- End-to-end demo: regenerate Cashfree and generate Razorpay; both pass quality gates.

**Out of scope for v1** (later product slices)

- On-demand / merchant-triggered mandate debit (`execute_mandate_debit` / `notify_pre_debit`). Periodic mandates are now Phase 3 in-scope (see §1 and above).
- Billing-cycle logic and invoice document generation.
- 3DS-specific flows beyond what the PSP handles on its hosted page.
- **Direct-API / server-to-server payment flows.** Future-scope design captured in `FUTURE_S2S_INTERFACE.md`.
- Payouts, disputes/chargebacks, settlement reconciliation, tax computation, KYC, multi-currency conversion.
- Multi-tenancy in Orbit (single deployment per consumer for now).
- Apps importing Lens directly.
- Runtime code generation.
- Any AI backend other than Claude Code.
- A second PSP in production (Razorpay is a generation test, not a v1 deployable).
- Promoting `USER_DROPPED` / `CANCELLED` / `FLAGGED` to first-class `PaymentAttemptStatus` values. They live in `PaymentFailureCode` instead.

A sub-project spec MAY narrow this further; it MAY NOT widen it without a constitution revision.

---

## §8. Versioning & "locked" policy

Each sub-project ships independently with its own SemVer.

**"Locked"** means: change requires (1) a constitution revision with a dated changelog entry, (2) coordinated updates in every dependent sub-project, (3) a migration plan for affected generated connectors and persisted data.

Locked things: every type and method named in §5; the four payment flows (`create_order`, `sync_payment`, `refund`, `sync_refund`); the five mandate lifecycle flows (`create_subscription`, `sync_subscription`, `cancel_subscription`, `pause_subscription`, `resume_subscription`); the three payment status enums and their values; `MandateStatus`, `MandateRail`, `MandateIntervalType`, `MandateDebitStatus` and their values; the `PaymentFailureCode` taxonomy (including the five mandate-related codes added in v0.2.0); `FailureClass`, `FAILURE_CLASS`; `PaymentWebhookEvent`, `MandateWebhookEvent`, `MandateDebitOutcome`, `ApprovalHandle`, `CustomerContact`, `MandateRequestCommon`, and all mandate request/response models; `WebhookRouter`, `WebhookHandlers`, `WebhookFamily`; the capability-interface split (`Connector` thin base, `PaymentsConnector`, `MandateConnector`); `MandatesFacade`; the new `ConnectorFactory` methods (`create_payments_facade`, `create_mandates_facade`, `create_webhook_router`, `register_webhook`); the file-header marker format in §4; the dependency order in §9.

**Compatibility rules**

- *Lens:* additive (optional field, new facade method that doesn't replace an existing one, new `PaymentFailureCode` value, new registered connector, **adding the s2s flows from `FUTURE_S2S_INTERFACE.md`**) = **minor**. Rename / signature change / field removal / constraint tightening = **major** + migration plan. Generated connectors ship bundled inside the `lens` wheel (one distribution, versioned by `lens.__version__`), so there is no connector-version gate — a connector cannot disagree with the Lens contract it was generated against.
- *Grace:* changes to the rulebook or templates that change generated-code shape = **major**. The §4 marker records the Grace version used.
- *Orbit:* HTTP API uses standard REST versioning (`/v1/orders`). Additive endpoints/fields = **minor**; rename/remove = **major** with deprecation.

**Generated-connector regeneration policy.** When `Connector` ABC changes (any minor or major):

1. Bump Grace to the version targeting the new ABC.
2. Regenerate every committed connector.
3. Diff and review like normal code.
4. Run full quality gates; merge.

Hand-patching files marked by the §4 header is forbidden. Fix the source (PSP docs or Grace rulebook) and regenerate.

---

## §9. Dependency order

**Lock the interface first, then implement against it.**

```
Step 1 ─ Lock interface ──────────────────────────────────────────
  Write lens:
    - domain types
        - request/response models per flow
        - PaymentAttempt model
        - RefundEvent
        - PaymentWebhookEvent (carries attempt/refund; renamed from WebhookEvent in v0.5)
        - OrderStatus, PaymentAttemptStatus, RefundStatus enums
        - PaymentFailureCode taxonomy
        - Amount, PaymentMethod, Currency, Maskable, ConnectorError
    - Connector thin-base ABC + PaymentsConnector / MandateConnector
      capability interfaces (v0.5; webhook handling is the shared
      WebhookRouter, not a connector method)
    - ConnectorFactory (register / create / list_connectors)
    - PaymentsFacade signature (thin wrapper)
  Output is the locked spec; Lens and Grace both point
  here from now on.

Step 2 ─ Build PaymentsFacade + factory implementation ──────────
  Wire structured logging, request-id, error normalization. Stub
  Connector for integration tests.

Step 3 ─ Audit + restructure existing Cashfree ──────────────────
  The Cashfree code in Plan C predates the locked interface.
  Audit against the new Connector ABC AND §7's hosted-only scope.
  Keep the create-order / sync-payment / refund / sync-refund /
  webhook paths. Archive any direct-API / instrument-handling
  code AND any authorize/capture/void code under `legacy/` so it
  can be revived when direct-API enters scope — do not delete.
  Restructure what's kept to the locked layout. Map Cashfree's
  PSP-specific status terms (USER_DROPPED, FLAGGED, NOT_ATTEMPTED,
  CANCELLED) into our three-state PaymentAttemptStatus + the
  PaymentFailureCode taxonomy. Hand-written; later serves as the
  reference Grace must match.

Step 4 ─ Extend Grace ───────────────────────────────────────────
  python-support branch: teach Grace's rulebooks + templates to
  emit Python conforming to the locked Connector ABC.
  Add ClaudeCodeRunner: invoke local Claude Code with the
  context (rulebook + PSP docs) and capture output.
  Merge to main once stable.

Step 5 ─ End-to-end generation test ─────────────────────────────
  Regenerate Cashfree via Grace, diff against the hand-written
  reference from Step 3. Quality gates pass. Then generate
  Razorpay from scratch. Quality gates pass.

Step 6 ─ Build Orbit ────────────────────────────────────────────
  HTTP API on /v1/orders/*, Order + PaymentAttempt + Refund
  ledger, state machines, idempotency middleware, webhook
  receiver (inline processing), Orbit-first creation flow with
  inline-resume recovery, an orbit-housekeeping cron (expiry
  sweep + idempotency prune). Integrate Lens.
  End-to-end payment flows against a Cashfree sandbox.
```

Step 1 must finish before everything else. Steps 2 + 3 + 4 can run in parallel (different agents) once Step 1 is locked. Step 5 gates Step 6's go-live. Step 6 can begin its non-integration work (DB schema, HTTP scaffolding, state-machine logic) earlier, as soon as Step 2 publishes a usable `PaymentsFacade` interface — even a stub.

---

## §10. Open questions & risks

Each item: question, current default assumption (used by sub-project specs until resolved), and the impact if the default is wrong.

**OQ-1. Cashfree's origin.** Was the Cashfree code in `lens` hand-written or generated by an earlier Grace iteration?

- **Default**: hand-written.
- **Impact if wrong**: Step 3 doubles as a Grace regression test.
- **Resolved by**: Step 3 audit.

**OQ-2. Plan C's FastAPI scaffolding.** §3 says Lens is a pure library with no HTTP server. The existing repo is a FastAPI service.

- **Default**: delete the FastAPI service code; move any useful dev harness it provides into `scripts/` or `dev/`.
- **Impact if wrong**: if it has dependents we haven't seen, deletion breaks them.
- **Resolved by**: Step 3 audit.

**OQ-3. Grace fork upstream-sync policy.** When Juspay improves `juspay-prism/grace/`, do we merge?

- **Default**: track upstream. `python-support` is a feature branch off `main` *until merged*; v1 acceptance includes merging it into `main`. After merge, future Python work happens on `main` directly; subsequent upstream syncs from `juspay-prism/grace/` are subtree merges into `main` with conflicts resolved manually.
- **Impact if wrong**: if we'd rather hard-fork or keep `python-support` permanently separate, branch layout and rebase policy change.
- **Resolved by**: `SUBPROJECT_GRACE_CODEGEN.md`.

**OQ-4. Naming reconciliation.** v0.4 fixes naming: Order (entity 1), PaymentAttempt (entity 2), Connector (ABC). Plan C used `PaymentConnector`; v0.4 uses `Connector`.

- **Default**: locked names are `Order`, `PaymentAttempt`, `Connector`.
- **Impact if wrong**: rename pass in existing references.
- **Resolved by**: naming table in `SUBPROJECT_LENS.md` and `SUBPROJECT_ORBIT_PRODUCT.md`.

**OQ-5. ~~Connector × Flow class shape~~** — *Resolved in v0.2.* One class per PSP.

**OQ-6. Idempotency on retry.** When Lens retries a state-mutating flow, does it pass the same idempotency key?

- **Default**: same key on every retry. PSP is the source of truth for "did this order already exist?" / "did this refund already happen?".
- **Impact if wrong**: per-PSP test cases need to cover the alternative.
- **Resolved by**: `SUBPROJECT_LENS.md`.

**OQ-7. ~~AI provider credentials~~** — *Resolved in v0.2.* Claude Code only.

**OQ-8. Existing s2s + capture/void code in Plan C's Cashfree.**

- **Default**: archive direct-API code AND any authorize/capture/void code under `legacy/`. Don't delete.
- **Impact if wrong**: if Plan C is already pure hosted, no archive needed.
- **Resolved by**: Step 3 audit.

**OQ-9. Trigger for adding s2s back.** What product event would justify implementing `FUTURE_S2S_INTERFACE.md`?

- **Default**: a consumer app needs a payment surface that hosted-checkout can't cover (recurring with stored credentials, in-app instrument capture). Until that need surfaces concretely, s2s stays in the future-scope doc.
- **Resolved by**: product decision; revisit at every quarterly review.

**OQ-10. ~~Janitor cadence + recovery policy~~** — *Resolved in Orbit v1.* In-flight recovery is **inline-resume on create**, not a separate janitor job. `services/order_creation.py` commits the Orbit row before the PSP call and derives a deterministic PSP key (`orbit-create-order-{order_id}`); a caller retry with the same idempotency key resumes the same PSP call (PSP dedups). Consequences: no background re-attempt loop, no `recovery_attempts` column, no advisory-lock leadership election. A separate `orbit-housekeeping` Lambda (EventBridge `rate(1 minute)`) sweeps expired `CREATED` orders → `EXPIRED`, prunes idempotency keys, reconciles active mandates, and drains the consumer-webhook delivery queue; stuck in-flight orders that are never retried simply expire via that sweep.

---

## Changelog

- **2026-05-20 v0.1** — initial lock-in (§1–§10 ratified after brainstorming session).
- **2026-05-20 v0.2** — simplification pass. Lens no longer mirrors juspay-prism's generic trait machinery; `Connector` ABC is a flat per-PSP class. Grace ships with Claude Code only. OQ-5 and OQ-7 closed.
- **2026-05-20 v0.3** — drop direct-API / server-to-server flows from v1. The four v1 flow methods are `create_order`, `sync_payment`, `refund`, `sync_refund`. `authorize` / `capture` / `void` moved to `FUTURE_S2S_INTERFACE.md`.
- **2026-05-20 v0.4** — introduce the two-entity model: **Order** (entity 1) + **PaymentAttempt** (entity 2). Split the overloaded `AttemptStatus` into three enums: `OrderStatus`, `PaymentAttemptStatus`, `RefundStatus`. Simplify `PaymentAttemptStatus` to three states (`PENDING`, `SUCCESS`, `FAILED`) with a locked `PaymentFailureCode` taxonomy carrying the granularity. Lock in **Orbit-first persistence** as a cross-cutting rule. Rename Orbit's HTTP namespace from `/v1/transactions` to `/v1/orders`. New OQ-10 covers the janitor's recovery cadence.
- **2026-05-20 v0.4 (consistency pass)** — applied 17 findings from cross-doc review: add `USER_CANCELLED` to the `PaymentFailureCode` list in §5; tighten `ConnectorFactory.register` signature + name/version validation; resolve python-support branch lifecycle (merges into main on v1 acceptance); add `IDEMPOTENCY_IN_FLIGHT` / `NOT_SUPPORTED` / `INCOMPATIBLE_VERSION` error reasons; add `merchant_id` column + `psp_merchant_id` semantics; make `customer_id` `NOT NULL`; echo `amount` + `currency` in `POST /v1/orders` 201; remove the per-file 60% coverage requirement from Lens (keep package ≥ 80%); add `Maskable[T]` requirement and PII enumeration to Orbit §5; carve out the Decimal exception for PSP wire-level transforms in Ground Rule 10; fix `Cashfree.name` to `@property`; correct s2s state count in `FUTURE_S2S` (three → five).
- **2026-05-21 v0.4 (lens migration to sylibs)** — metadata-only update. Lens relocates from `/Users/sarthak/PycharmProjects/references/lens/` to `/Users/sarthak/PycharmProjects/symplora/sylibs/packages/lens/` as the 6th package in the `sylibs` monorepo. Published to SyPI (Symplora's private PyPI) as `lens`. No public-surface impact: `lens.__all__` is unchanged, the `Connector` ABC + `PaymentsFacade` + `ConnectorFactory` + every domain type and enum keep their locked names and signatures. The §9 Step ordering, the §4 generated-file marker format, and the §8 versioning policy are all unaffected. Updated `Location:` fields in §2 (Lens row), `SUBPROJECT_LENS.md` §1, and `SUBPROJECT_ORBIT_PRODUCT.md` §4 dependency description. Grace's `SUBPROJECT_GRACE_CODEGEN.md` §3.2 retains the per-PSP layout (`connectors/<psp>/`); only the absolute root path Grace writes to changes (now `<sylibs>/packages/lens/src/lens/connectors/<psp>/`).
- **2026-05-31 v0.5 (accuracy pass)** — doc-correctness sweep against the shipped Orbit implementation; no spec/contract changes. §6: replace the hard `structlog` mandate with "structured JSON logging" (library is a per-sub-project choice; Orbit uses stdlib `logging` + a `sykit` JSON formatter). §9 Step 1: fix stale `WebhookEvent` → `PaymentWebhookEvent` and the `Connector ABC (… + handle_webhook …)` line → the v0.5 capability split (`PaymentsConnector`/`MandateConnector`; webhook handling on the shared `WebhookRouter`). Reconcile the "janitor" recovery narrative (§3 box, §7, §9 Step 6, OQ-10) to the implemented **inline-resume on create** + `orbit-housekeeping` cron — there is no janitor job, no `recovery_attempts` column, and no advisory-lock election. `SUBPROJECT_ORBIT_PRODUCT.md` updated in the same pass.
- **2026-05-30 v0.5** — Periodic subscription-mandate support (Phase 3). Bring periodic mandates (UPI Autopay + card e-mandate, INR) into scope (§1/§7); on-demand debit remains out of scope. Add capability-interface model: `Connector` reshaped to thin base (`name`, `base_url`, `close`); `PaymentsConnector(Connector)` carries the four payment flows + `supported_methods`/`supports_idempotency_key`; `MandateConnector(Connector)` carries five lifecycle methods + four introspection methods. Add `MandatesFacade` (wraps a `MandateConnector`). Add shared `WebhookRouter` (obtained via `ConnectorFactory.create_webhook_router(config)`); its `handle(raw_payload, headers)` verifies the signature once and routes by `WebhookFamily` (PAYMENT / MANDATE), returning `PaymentWebhookEvent | MandateWebhookEvent`. Remove `PaymentsFacade.incoming_webhook` (migration: use `WebhookRouter`). Rename `WebhookEvent` → `PaymentWebhookEvent`. Add mandate domain types: `CreateSubscriptionRequest/Response`, `SyncSubscriptionRequest/Response`, `ManageMandateRequest/Response`, `CustomerContact`, `ApprovalHandle`, `MandateDebitOutcome`, `MandateWebhookEvent`, `MandateRequestCommon`. Add mandate enums: `MandateRail`, `MandateStatus`, `MandateIntervalType`, `MandateDebitStatus`, `FailureClass`; extend `WebhookEventType` (+13 `MANDATE_*` values) and `PaymentFailureCode` (+5 mandate values). Add `FAILURE_CLASS` (frozen `MappingProxyType`, published data only). Add `ConnectorFactory` methods: `create_payments_facade`, `create_mandates_facade`, `create_webhook_router`, `register_webhook`; add capability guard to `register`. All new symbols added to §5 and §8 locked set. lens bumped to 0.2.0 (breaking surface change); the Cashfree connector is quarantined pending Grace regeneration against the new ABCs.
- **2026-06-01 v0.6** — Remove the connector version gate. `ConnectorFactory.register` no longer validates `requires_lens` against the running Lens version, and generated connectors no longer declare `requires_lens`. **Rationale:** connectors ship bundled inside the `lens` wheel (one distribution, versioned by `lens.__version__`, regenerated in-tree by Grace), so a connector can never disagree with the Lens contract it was built against — the gate guarded a structurally unreachable condition (and had silently mis-fired: the discovery convention and discovery logic diverged once connectors went multi-file). `register` now validates only name agreement + capability interface (both → `INVALID_REQUEST`). The `INCOMPATIBLE_VERSION` `ConnectorErrorReason` is **retained** in the taxonomy (a connector or Orbit may still surface it) but is no longer raised by `register`. Coordinated updates: §5 `ConnectorFactory` contract + §8 compatibility rule (this doc), `SUBPROJECT_LENS.md` (register validation + connector-layout `requires_lens` line), `SUBPROJECT_GRACE_CODEGEN.md` (Grace stops emitting `requires_lens`), and lens `factory.py` + `test_factory.py` + CHANGELOG (folded into the unreleased 0.2.0); `packaging` dropped from lens runtime deps. **Non-breaking relaxation** — `register` accepts a strict superset of before; no migration required for Orbit or persisted data.
