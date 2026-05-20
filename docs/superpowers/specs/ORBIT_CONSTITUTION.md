# Orbit Constitution

**Status**: v0.4 — Order + PaymentAttempt two-entity model; Orbit-first creation; simplified status enums.
**Date**: 2026-05-20.
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

**Out of scope for v1** but on the longer-term roadmap: subscriptions and recurring mandates, billing-cycle logic, invoice generation, **direct-API / server-to-server payment flows** (`authorize`, `capture`, `void` with raw instrument data — see `FUTURE_S2S_INTERFACE.md`). Each lands as a follow-up product slice gated by v1 stability. Anything else (payouts, disputes, tax, KYC, settlement reconciliation) is also out of scope until explicitly added by a future revision.

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
- Location: `/Users/sarthak/PycharmProjects/references/lens/`
- Role: a stateless Python library. Exposes `PaymentsFacade`, `ConnectorFactory`, a `Connector` ABC, and the domain types (request/response models per flow, the `PaymentAttempt` model, `WebhookEvent`, error types). Hosts the per-PSP `Connector` implementations (Cashfree first). Talks to PSPs via httpx. No DB. No HTTP server. No global mutable state.
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
        │  • Janitor (in-flight Order recovery)   │
        │  • Persistence (Postgres)               │
        └─────────────────┬───────────────────────┘
                          │ in-process Python import
                          ▼
        ┌─────────────────────────────────────────┐
        │ Lens (library, stateless)               │
        │  • PaymentsFacade  (thin wrapper:       │
        │     logging + error normalization)      │
        │  • Connector ABC                        │
        │     - create_order                      │
        │     - sync_payment                      │
        │     - refund                            │
        │     - sync_refund                       │
        │     - handle_webhook                    │
        │     - close                             │
        │  • ConnectorFactory (registry)          │
        │  • Domain types incl. PaymentAttempt    │
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
- One `Connector` class per PSP. Each class owns its own httpx client and implements the four async flow methods plus `handle_webhook` and `close`.
- Cross-cutting concerns (structured logging, retries, error normalization, PII masking) are applied via:
  - `PaymentsFacade` (thin wrapper around the `Connector`): binds request id, logs start/end, normalizes any leaking exceptions into `ConnectorError`.
  - The httpx client (configured per Connector): retry transport, timeout, event hooks for masked logging.
  - The `Maskable[T]` type wrapper: any PII field declared `Maskable[...]` stringifies as `***`, so it can't accidentally leak into a log line.
- Orbit is the only process boundary. All HTTP ingress (consumer requests + PSP webhooks) terminates at Orbit.
- **Orbit-first persistence.** Every external state-changing action (PSP `create_order`, `refund`) is preceded by writing an Orbit row. The Orbit record is the source of truth for "did we already start this?". See `SUBPROJECT_ORBIT_PRODUCT.md` for the recovery flow.
- Webhook flow: PSP → Orbit's public webhook endpoint → Orbit calls `PaymentsFacade.incoming_webhook(raw_payload, headers)` → Lens verifies signature + parses payload → returns a `WebhookEvent` carrying a `PaymentAttempt` and/or `RefundEvent` → Orbit dedups against its own store → Orbit updates the relevant entity.

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

**`PaymentsFacade`** (Lens → Orbit). The class Orbit holds and calls. Async methods: `create_order`, `sync_payment`, `refund`, `sync_refund`, `incoming_webhook`, `close`. Thin wrapper that adds request-id binding, structured logging, and error normalization around a `Connector`. Signatures pinned in `SUBPROJECT_LENS.md`.

**`ConnectorFactory`** (Lens → Orbit). Class-method API: `register(name, connector_cls)`, `create(config) -> Connector`, `list_connectors() -> list[str]`. Generated connector modules self-register via `register` on import. `register` validates that `connector_cls().name == name` and that `connector_cls.requires_lens` (semver constraint) is satisfied by the running Lens version; otherwise raises `ConnectorError(reason=INCOMPATIBLE_VERSION)` or `ConnectorError(reason=INVALID_REQUEST)`.

**`Connector`** ABC (Lens → per-PSP implementations). One class per PSP. Async methods: `create_order`, `sync_payment`, `refund`, `sync_refund`, `handle_webhook`, `close`. Properties: `name`, `base_url`, `supported_methods`, `supports_idempotency_key`. Each Connector owns its own `httpx.AsyncClient`.

**Domain types** (Lens → Orbit, Lens → Grace). Frozen Pydantic models that flow across the Orbit ↔ Lens boundary. Key types:

- Per-flow request/response models: `CreateOrderRequest`/`CreateOrderResponse`, `SyncPaymentRequest`/`SyncPaymentResponse`, `RefundRequest`/`RefundResponse`, `SyncRefundRequest`/`SyncRefundResponse`.
- `PaymentAttempt` — one attempt by a payer against an Order. Returned in lists from `sync_payment` and individually inside `WebhookEvent`.
- `RefundEvent` — one refund-status update, carried inside `WebhookEvent` for refund-related events.
- `WebhookEvent` — the parsed, normalized form of an inbound PSP event; carries `attempt: PaymentAttempt | None` and `refund: RefundEvent | None` depending on the event type.
- Three separate status enums (no overloaded "AttemptStatus"):
  - `OrderStatus`: `CREATED`, `PAID`, `PARTIALLY_REFUNDED`, `REFUNDED`, `EXPIRED`, `FAILED`.
  - `PaymentAttemptStatus`: `PENDING`, `SUCCESS`, `FAILED`.
  - `RefundStatus`: `PENDING`, `SUCCESS`, `FAILED`.
- `PaymentFailureCode` enum — a locked taxonomy for *why* a payment attempt failed (`USER_DROPPED`, `USER_CANCELLED`, `CARD_DECLINED`, `INSUFFICIENT_FUNDS`, `AUTHENTICATION_FAILED`, `FRAUD_BLOCKED`, `FRAUD_REVIEW_PENDING`, `INVALID_INSTRUMENT`, `PSP_ERROR`, `NETWORK_ERROR`, `UNKNOWN`). Carried on `PaymentAttempt.failure_code`.
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
- **Structured logging only** (`structlog`). PII fields typed `Maskable[T]` so they stringify as `***`. Forbidden in logs even masked: full PAN, CVV, full bank account numbers.
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
- Orbit-first creation flow with janitor recovery for orders stuck in flight.
- Idempotency on every state-mutating endpoint.
- Webhook receiver endpoint that delegates verification + parsing to Lens, dedups locally, and updates the relevant entity.
- One configured PSP (Cashfree) wired end-to-end.

*Lens:*

- `Connector` ABC + `PaymentsFacade` + `ConnectorFactory` + domain types (including `PaymentAttempt`, the three status enums, `PaymentFailureCode`).
- One PSP: Cashfree (existing in Plan C, restructured to match the ABC).
- **Hosted-checkout / session-based integration only.** v1 does not accept raw card, UPI, wallet, or other instrument data at the Lens boundary.
- Four flow methods: `create_order`, `sync_payment`, `refund`, `sync_refund`. Plus `handle_webhook` and `close`.
- `sync_payment` returns the order's overall `OrderStatus` and the list of `PaymentAttempt`s the PSP knows about.
- `handle_webhook` returns a `WebhookEvent` carrying a `PaymentAttempt` (for payment-level events) or `RefundEvent` (for refund-level events).
- httpx-based HTTP execution with timeouts, retries (configurable, idempotency-key passthrough), structured logging.

*Grace:*

- `python-support` branch landed: emits Python conforming to Lens's ABC.
- One AI backend: **Claude Code** (invoked via the local CLI session).
- End-to-end demo: regenerate Cashfree and generate Razorpay; both pass quality gates.

**Out of scope for v1** (later product slices)

- Subscriptions, recurring mandates.
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

Locked things: every type and method named in §5; the four v1 flows; the three status enums and their values; the `PaymentFailureCode` taxonomy; the file-header marker format in §4; the dependency order in §9.

**Compatibility rules**

- *Lens:* additive (optional field, new facade method that doesn't replace an existing one, new `PaymentFailureCode` value, new registered connector, **adding the s2s flows from `FUTURE_S2S_INTERFACE.md`**) = **minor**. Rename / signature change / field removal / constraint tightening = **major** + migration plan. Each generated connector declares `requires_lens = "^N"`; Lens refuses to load incompatible versions.
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
        - WebhookEvent (carries attempt/refund)
        - OrderStatus, PaymentAttemptStatus, RefundStatus enums
        - PaymentFailureCode taxonomy
        - Amount, PaymentMethod, Currency, Maskable, ConnectorError
    - Connector ABC (4 async flow methods + handle_webhook + close)
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
  receiver + async worker, Orbit-first creation flow, janitor
  job for in-flight orders. Integrate Lens.
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

**OQ-10. Janitor cadence + recovery policy.** Orders with `psp_order_id IS NULL` and `created_at < now() - 5 minutes` need either re-attempt or terminal `FAILED` marking.

- **Default**: janitor runs every minute; recovers by re-calling `create_order` with the same idempotency key (PSP dedups). After 3 failed recovery attempts, marks order `FAILED`.
- **Impact if wrong**: if cadence is too aggressive, we hit PSP rate limits; too slow, consumers see latency on retries.
- **Resolved by**: `SUBPROJECT_ORBIT_PRODUCT.md`.

---

## Changelog

- **2026-05-20 v0.1** — initial lock-in (§1–§10 ratified after brainstorming session).
- **2026-05-20 v0.2** — simplification pass. Lens no longer mirrors juspay-prism's generic trait machinery; `Connector` ABC is a flat per-PSP class. Grace ships with Claude Code only. OQ-5 and OQ-7 closed.
- **2026-05-20 v0.3** — drop direct-API / server-to-server flows from v1. The four v1 flow methods are `create_order`, `sync_payment`, `refund`, `sync_refund`. `authorize` / `capture` / `void` moved to `FUTURE_S2S_INTERFACE.md`.
- **2026-05-20 v0.4** — introduce the two-entity model: **Order** (entity 1) + **PaymentAttempt** (entity 2). Split the overloaded `AttemptStatus` into three enums: `OrderStatus`, `PaymentAttemptStatus`, `RefundStatus`. Simplify `PaymentAttemptStatus` to three states (`PENDING`, `SUCCESS`, `FAILED`) with a locked `PaymentFailureCode` taxonomy carrying the granularity. Lock in **Orbit-first persistence** as a cross-cutting rule. Rename Orbit's HTTP namespace from `/v1/transactions` to `/v1/orders`. New OQ-10 covers the janitor's recovery cadence.
- **2026-05-20 v0.4 (consistency pass)** — applied 17 findings from cross-doc review: add `USER_CANCELLED` to the `PaymentFailureCode` list in §5; tighten `ConnectorFactory.register` signature + name/version validation; resolve python-support branch lifecycle (merges into main on v1 acceptance); add `IDEMPOTENCY_IN_FLIGHT` / `NOT_SUPPORTED` / `INCOMPATIBLE_VERSION` error reasons; add `merchant_id` column + `psp_merchant_id` semantics; make `customer_id` `NOT NULL`; echo `amount` + `currency` in `POST /v1/orders` 201; remove the per-file 60% coverage requirement from Lens (keep package ≥ 80%); add `Maskable[T]` requirement and PII enumeration to Orbit §5; carve out the Decimal exception for PSP wire-level transforms in Ground Rule 10; fix `Cashfree.name` to `@property`; correct s2s state count in `FUTURE_S2S` (three → five).
