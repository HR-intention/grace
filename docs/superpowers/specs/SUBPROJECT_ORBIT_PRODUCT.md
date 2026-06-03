# Sub-project: Orbit (product)

**Inherits from**: `ORBIT_CONSTITUTION.md`. Conflicts resolve in favor of the constitution.
**Owner**: TBD per implementing agent.
**Location**: `/Users/sarthak/PycharmProjects/symplora/orbit/`
**Status**: v0.5 — **shipped**. Order + PaymentAttempt two-entity model; Orbit-first creation flow with **inline-resume** recovery (no janitor); periodic subscription mandates **implemented** (Phase 3) against lens 0.2.0; outbound consumer-webhook delivery (Phase 2). Multi-tenant by API key with KMS-encrypted per-tenant PSP credentials. Runtime: FastAPI + Mangum on AWS Lambda, asyncpg + Postgres, dbmate plain-SQL migrations. API surface: OpenAPI 0.6.0. See the repo `CLAUDE.md` for the canonical operational picture; this spec is the design narrative.

---

## §1. Purpose & scope

Orbit is the consumer-facing payments product. It exposes an HTTP API that consumer apps (Symplora ATS, Hikara) call whenever money needs to move. Underneath, Orbit imports `lens` for PSP-level operations and owns all business state — the Order, PaymentAttempt, and Refund ledgers, idempotency, the state machines, webhook dedup, and persistence.

**Two first-class entities** (constitution §1, §5):

- **Order** — the merchant's payment request. Created when a consumer app calls `POST /v1/orders`. One Order corresponds 1:1 to a PSP-side order.
- **PaymentAttempt** — one specific attempt by the payer against an Order. Created by the PSP when the payer initiates a payment on the hosted page; observed by Orbit via webhook or `sync_payment`. One Order has 0..N PaymentAttempts.

Plus **Refund** as a third entity that hangs off the successful PaymentAttempt under an Order.

**In scope for v1**

- HTTP API for Orders + PaymentAttempts + Refunds at `/v1/orders/*`.
- Order state machine: `CREATED → PAID → (PARTIALLY_REFUNDED | REFUNDED)`, with `EXPIRED` and `FAILED` terminals.
- PaymentAttempt state machine: `PENDING → (SUCCESS | FAILED)`. Failure granularity in `failure_code`.
- Refund state machine: `PENDING → (SUCCESS | FAILED)`.
- **Orbit-first persistence**: every call to Lens is preceded by an Orbit row write.
- **Inline-resume** recovery for Orders stuck "in flight" (Orbit row exists, no `psp_order_id` yet): the create flow commits the Orbit row before the PSP call and uses a deterministic PSP key, so a caller retry with the same `Idempotency-Key` resumes the same PSP call (PSP dedups). A separate `orbit-housekeeping` cron expires un-resumed `CREATED` orders and prunes idempotency keys — there is no janitor re-attempt loop.
- Idempotency on every state-mutating endpoint.
- Webhook receiver endpoint that delegates verification + parsing to Lens, dedups locally, and updates the relevant entity **inline** (synchronously in the request).
- One wired PSP connector boundary (Cashfree, via lens). **Multi-tenant**: each consumer app gets its own API key and its own KMS-encrypted per-tenant PSP merchant config; all order / mandate / webhook data is isolated by `api_key_id`.
- **Phase 2 — outbound consumer webhooks**: tenants register signed delivery URLs (operator-provisioned) and receive `order.*` / `refund.*` / `mandate.*` events; inline-burst on the hot path + an `orbit-housekeeping` queue sweep for retries.
- **Phase 3 — periodic subscription mandates** (implemented): UPI Autopay + card e-mandate, INR, Cashfree via lens 0.2.0. Orbit offers trial → auto-debit → recurring billing. Cashfree owns the debit schedule, retries, and RBI pre-debit notifications; Orbit configures the mandate once at create and then reacts to webhooks. See §9 for the full implemented design (REST surface, data model, state machine, housekeeping).

**Out of scope for v1**

- Billing-cycle logic and invoice generation. Mandate schedule is Cashfree's.
- On-demand / merchant-triggered mandate debit (`execute_mandate_debit` / `notify_pre_debit`). Periodic mandates are now in scope; on-demand stays out.
- Tenant self-service onboarding. API keys, PSP configs, and webhook subscriptions are provisioned via operator-only `/admin/*` routes, not a public signup flow.
- Direct-API payment-method handling (constitution §7). Future scope: `FUTURE_S2S_INTERFACE.md`.
- `authorize` / `capture` / `void` endpoints. Hosted-checkout's auto-capture means there's no separate capture step.
- A second PSP in production.
- Apps importing Lens directly.

---

## §2. Public surface

REST API versioned at `/v1`. All requests and responses JSON. All state-mutating endpoints require an `Idempotency-Key` header — a free-form client-chosen string of up to 200 characters (it is *not* required to be a UUID; the only constraint is uniqueness within `(api_key_id, key)`).

Three authentication tiers (see §2.4): `/v1/*` (except webhooks) require a tenant API-key bearer token; `/v1/webhooks/*` carry no bearer and are verified by PSP signature; `/admin/*` require a shared admin bearer token.

### 2.1 Orders

```
POST /v1/orders
  body: {
    amount: { minor_units: int, currency: "INR" },
    customer_id: str,                        # required
    return_url: HttpUrl,
    psp: str,                                # required, e.g. "cashfree" — selects the
                                             #   tenant's active PSP merchant config
    allowed_methods?: ["CARD", "UPI", ...]
  }
  → 201 Created                              # lean shape — no nested children yet
    {
      order_id: str,                          # Orbit's id (UUID)
      status: "CREATED",
      amount: { minor_units: int, currency: "INR" },  # echo for client verification
      psp: str,                               # echo of the selected PSP
      payment_link: HttpUrl,                  # PSP-hosted page
      expires_at: ISO8601,
      created_at: ISO8601
    }


GET /v1/orders
  query: status?, customer_id?, limit? (default 50), cursor?   # opaque, versioned
  → 200 OK    # tenant-scoped list, newest first, keyset/cursor pagination
    {
      orders: [ { order_id, status, amount, psp, customer_id,
                  created_at, updated_at } ],   # lean list items
      next_cursor: str | null
    }


GET /v1/orders/{id}
  → 200 OK
    {
      order_id, customer_id, amount, currency, status,
      psp: { name, order_id, refund_ids[] },
      payment_link, expires_at,
      attempts: [                             # nested PaymentAttempt list (latest first)
        {
          attempt_id, psp_payment_id, status,
          method_used, amount,
          failure_code, failure_reason,
          attempted_at
        }
      ],
      refunds: [                              # nested Refund list (if any)
        { refund_id, psp_refund_id, amount, status, reason, created_at }
      ],
      timeline: [                             # status transitions on the Order
        { from_status, to_status, source, at }
      ],
      created_at, updated_at
    }


POST /v1/orders/{id}/sync
  → 200 OK    # force a PSP sync_payment; updates the order + attempts in DB
    { order_id, status, attempts: [...] }


POST /v1/orders/{id}/refund
  body: { amount?: int, reason?: str }      # amount? defaults to full remaining
  → 201 Created
    { refund_id, order_id, status, amount }

  # Resolution: Orbit looks up the successful PaymentAttempt under this Order
  # and refunds against it. 400 ORDER_NOT_PAID if no SUCCESS attempt exists.


GET /v1/orders/{id}/refunds/{refund_id}
  → 200 OK
    { refund_id, order_id, psp_refund_id, amount, status, reason, created_at }


POST /v1/orders/{id}/refunds/{refund_id}/sync
  → 200 OK    # force a PSP sync_refund
    { refund_id, status }
```

There is **no** `POST /v1/orders/{id}/capture` or `/void` in v1. Auto-capture hosted-checkout means there's nothing to capture, and abandons happen on the PSP's page without a void call.

There is **no** caller-supplied payment-attempt-id on `POST /v1/orders/{id}/refund`. Orbit resolves the target to the unique SUCCESS attempt under the order. If we ever need to refund a specific historical attempt, we add a query parameter then.

### 2.2 Webhooks

```
POST /v1/webhooks/{psp_name}/{config_id}
  (PSP-signed; {config_id} selects the tenant's psp_merchant_config so the per-tenant
   webhook secret can verify the signature. Orbit resolves
   ConnectorFactory.create_webhook_router(config).handle(raw, headers).)
  → 200 OK    # always (even on signature failure — see §3.6). Verify + dedup + entity
              # update happen INLINE in the request; body reports
              # {"status": "processed" | "duplicate" | "ignored"}.
```

### 2.3 Operational

```
GET /healthz                # liveness
GET /readyz                 # readiness (DB + Lens both ready)
GET /v1/connectors          # registered PSPs + their health
```

### 2.4 Authentication

Three tiers, enforced router-level via FastAPI `Depends(...)`:

- **Tenant API key** — `/v1/*` except webhooks. `Authorization: Bearer <key>`; the secret is verified by **HMAC-SHA256 over the presented key with a server-side pepper** (resolved from Secrets Manager at startup), compared against `api_keys.hmac_hash` (a `bytea`, not an argon2id string). There is **no argon2id** anywhere in Orbit. Old + new keys are both valid during a rotation window.
- **PSP signature** — `/v1/webhooks/{psp}/{config_id}`. No bearer; the PSP signature on the raw body is verified inside the handler using the per-config webhook secret (decrypted from `psp_merchant_configs` via KMS).
- **Admin token** — `/admin/*`. A single shared admin bearer token (`require_admin_token`), resolved from Secrets Manager at startup; provisions API keys, PSP configs, and webhook subscriptions. (Known limitation: single shared token, no per-actor identity — see the deployment runbook.)

### 2.5 Error response shape

```json
{
  "error": {
    "reason": "<OrbitErrorReason>",
    "message": "<human readable>",
    "request_id": "<uuid>",
    "details": { }
  }
}
```

`OrbitErrorReason` enum (20 values, from `domain/errors.py`): `INVALID_REQUEST`, `UNAUTHENTICATED`, `FORBIDDEN`, `IDEMPOTENCY_CONFLICT`, `IDEMPOTENCY_IN_FLIGHT`, `ORDER_NOT_FOUND`, `ORDER_NOT_PAID`, `ORDER_FULLY_REFUNDED`, `REFUND_NOT_FOUND`, `REFUND_AMOUNT_EXCEEDS_REMAINING`, `PSP_CONFIG_NOT_FOUND`, `WEBHOOK_SUBSCRIPTION_NOT_FOUND`, `MANDATE_NOT_FOUND`, `MANDATE_INVALID_STATE`, `PSP_ERROR`, `PSP_UNAVAILABLE`, `PSP_TIMEOUT`, `PSP_NOT_CONFIGURED`, `UNSUPPORTED_CURRENCY`, `INTERNAL`.

### 2.6 Admin & operator surface (`/admin/*`, admin-token-gated)

Operator-only provisioning, not consumer-facing. Excluded from `openapi-public.json`.

```
POST   /admin/api-keys                                # mint a tenant API key (plaintext returned once)
GET    /admin/api-keys                                # list
POST   /admin/api-keys/{id}/rotate                    # issue a new secret; old stays valid in window
POST   /admin/api-keys/{id}/revoke
POST   /admin/api-keys/{id}/psp-configs               # register a KMS-encrypted per-tenant PSP config
GET    /admin/api-keys/{id}/psp-configs
POST   /admin/api-keys/{id}/psp-configs/{cid}/rotate
POST   /admin/api-keys/{id}/psp-configs/{cid}/revoke
POST   /admin/api-keys/{id}/webhook-subscriptions     # register an outbound consumer-webhook URL (Phase 2)
GET    /admin/api-keys/{id}/webhook-subscriptions
POST   /admin/api-keys/{id}/webhook-subscriptions/{sid}/rotate
POST   /admin/api-keys/{id}/webhook-subscriptions/{sid}/revoke
POST   /admin/api-keys/{id}/webhook-subscriptions/{sid}/test   # send a synthetic signed event
```

### 2.7 Mandates

Periodic-subscription-mandate routes (`POST/GET /v1/mandates`, `GET /v1/mandates/{id}`, `POST /v1/mandates/{id}/{cancel,pause,resume}`, `GET /v1/mandates/{id}/charges`) are documented in full in §9.

---

## §3. Internal architecture

```
src/orbit/
  main.py                       # FastAPI app factory + lifespan (pool, KMS, pepper, admin token)
  handler.py                    # Lambda entry points: api_handler (Mangum) + housekeeping_handler
  config.py                     # pydantic-settings Settings + Secrets Manager helper
  docs.py                       # OpenAPI customization + gated docs router + public-spec filter
  logging.py                    # sykit-based JSON structured logger (stdlib logging; NO structlog)
  api/
    auth.py                     # require_api_key (HMAC+pepper) + require_admin_token
    errors.py                   # OrbitError → spec §2.5 JSON envelope; handler registration
    idempotency.py              # IdempotencyContext dependency (header + body hash)
    openapi_responses.py        # common_errors() helper for route decoration
    schemas.py                  # Pydantic v2 request/response models + ErrorEnvelope
    orders.py                   # /v1/orders/* (create, get, list, sync, refund, refund-sync)
    webhooks.py                 # /v1/webhooks/{psp_name}/{config_id} (inline processing)
    mandates.py                 # /v1/mandates/* (Phase 3 — §9)
    ops.py                      # /healthz, /readyz, /v1/connectors
    admin/api_keys.py           # /admin/api-keys/*
    admin/psp_configs.py        # /admin/api-keys/{id}/psp-configs/*
    admin/webhook_subscriptions.py   # /admin/.../webhook-subscriptions/* (Phase 2)
  domain/                       # Pure-Python aggregates + state machines (no SQL, no I/O)
    order.py                    # Order, derive_order_status, validate_order_transition
    payment_attempt.py
    refund.py
    mandate.py                  # Mandate + MandateCharge dataclasses + resolve_transition (§9)
    mandate_event_payload.py    # build_mandate_event → outbound MandateEvent (PII-stripped)
    api_key.py
    psp_merchant_config.py
    webhook_event.py
    idempotency.py              # canonical_request_hash
    status_map.py               # WebhookEvent → action classification
    errors.py                   # OrbitError + OrbitErrorReason (20 reasons)
  services/                     # Use-case orchestration (no SQL, no HTTP)
    order_creation.py           # §3.4 inline-resume create flow (phase-split transactions)
    order_sync.py
    refund_initiation.py        # deterministic-id refund with split-transaction phases
    refund_sync.py
    webhook_processor.py        # inline webhook handling (verify + dedup + dispatch)
    mandate_creation.py         # §9 create + inline-resume
    mandate_management.py       # cancel / pause / resume
    mandate_processor.py        # inbound MandateWebhookEvent → state machine
    mandate_housekeeping.py     # stuck-auth sweep + active-mandate reconcile
    consumer_webhook_delivery.py     # Phase 2 signed delivery (inline burst + queue attempt)
    housekeeping.py             # order-expiry sweep + idempotency prune + delivery-queue sweep
    idempotent.py               # claim_or_run() wrapper for single-step routes
  persistence/
    db.py                       # asyncpg pool wrapper (Database) — NO SQLAlchemy
    schema.sql                  # dbmate-dumped current schema
    migrations/                 # dbmate plain-SQL migrations (timestamp-prefixed; append-only)
    repositories/               # one module per table; NO SQL outside this layer
  integration/
    kms.py                      # KMS envelope encrypt/decrypt
    lens.py                     # resolve_facade / resolve_mandates_facade /
                                #   resolve_webhook_router (warm per-merchant cache)

tests/{unit,integration,e2e}/   # e2e drive the full ASGI app via httpx.AsyncClient + ASGITransport
```

### 3.1 Order state machine

`OrderStatus` is the enum from Lens (constitution §5). Same values, same names; Orbit doesn't redefine it.

Allowed transitions:

| From | To | Trigger |
|---|---|---|
| (new) | `CREATED` | `POST /v1/orders` inserts the Orbit row with `status=CREATED` (§3.4 step 4). `psp_order_id` may be NULL transiently between steps 4 and 6a; the row is only returned to consumers once §3.4 step 6a populates it. The `order_events` row recording this transition is written in step 6a. |
| `CREATED` | `PAID` | A PaymentAttempt under this Order becomes `SUCCESS` (via webhook or `sync_payment`). |
| `CREATED` | `EXPIRED` | `expires_at` passed AND no `SUCCESS` attempt exists. |
| `CREATED` | `FAILED` | PSP `create_order` call failed at API time, OR PSP later emits a terminal order-failure event (rare). |
| `PAID` | `PARTIALLY_REFUNDED` | First refund (any amount less than the paid amount) succeeds. |
| `PARTIALLY_REFUNDED` | `PARTIALLY_REFUNDED` | Another partial refund succeeds. |
| `PARTIALLY_REFUNDED` | `REFUNDED` | Cumulative refunded amount == paid amount. |
| `PAID` | `REFUNDED` | A single full refund succeeds. |

Terminal states: `REFUNDED`, `EXPIRED`, `FAILED`.

**Order status is derived.** Stored on the row for query efficiency, but reconstructable from the children (PaymentAttempts + Refunds + `expires_at`). Every webhook / sync / refund event recomputes the order's status before commit. Pseudocode:

```python
def derive_order_status(order, attempts, refunds_succeeded) -> OrderStatus:
    success_attempt = first(a for a in attempts if a.status == SUCCESS)
    if success_attempt is None:
        if order.expires_at < now():
            return EXPIRED
        if order.terminally_failed:    # set on PSP create_order failure
            return FAILED
        return CREATED
    paid = success_attempt.amount.minor_units
    refunded_total = sum(r.amount_minor for r in refunds_succeeded)
    if refunded_total == 0:    return PAID
    if refunded_total <  paid: return PARTIALLY_REFUNDED
    return REFUNDED            # refunded_total == paid
```

Every transition writes an `order_events` row (`from_status`, `to_status`, `source`, `at`). Source ∈ `{api, webhook, sync, housekeeping, admin}` (the expiry sweep writes `housekeeping`; there is no `janitor` source). This is the `timeline` field on `GET /v1/orders/{id}`.

### 3.2 PaymentAttempt state machine

`PaymentAttemptStatus`: `PENDING`, `SUCCESS`, `FAILED`. From Lens.

Lifecycle:

```
                  ┌──→ SUCCESS  (terminal)
                  │
   PENDING ───────┼──→ FAILED   (terminal; failure_code populated from PaymentFailureCode taxonomy)
                  │
                  └──→ (stays PENDING — e.g., FRAUD_REVIEW_PENDING; resolved by follow-up webhook)
```

- First time Orbit observes a `psp_payment_id`: INSERT row. Initial status is whatever Lens reports — usually `PENDING` (for in-flight async methods), but can be `SUCCESS` or `FAILED` directly if the PSP emits a terminal event as the first webhook.
- Subsequent observations for the same `psp_payment_id`: UPDATE the row.
- Once terminal (`SUCCESS` or `FAILED`), no further transitions. Late webhooks for the same attempt are deduped + logged.

Failure granularity lives in `failure_code` (`PaymentFailureCode` enum) + `failure_reason` (string). E.g., a Cashfree `PAYMENT_USER_DROPPED_WEBHOOK` produces a `PaymentAttempt` with `status=FAILED` and `failure_code=USER_DROPPED`.

### 3.3 Refund state machine

`RefundStatus`: `PENDING`, `SUCCESS`, `FAILED`. From Lens.

- `POST /v1/orders/{id}/refund` inserts a row with `status=PENDING`, then calls `PaymentsFacade.refund`. On PSP success: row stays `PENDING` (the refund is queued PSP-side) until a webhook or sync confirms.
- Webhook `REFUND_SUCCESS` → row to `SUCCESS`.
- Webhook `REFUND_FAILED` → row to `FAILED`.
- Order status recomputed after every change.

### 3.4 Orbit-first creation flow (`POST /v1/orders`)

```
1. Auth: validate API key from `Authorization: Bearer …`.
   Failure → 401 UNAUTHENTICATED.

2. Body validation. Failure → 400 INVALID_REQUEST.

3. Idempotency lookup on (api_key_id, Idempotency-Key header).
     - Found + response stored + request_hash matches → return stored response.
     - Found + response NULL (in-flight) → the create flow RESUMES inline:
       it re-issues create_order with the same deterministic PSP key (§3.4 6c)
       so the PSP dedups, rather than returning an error. (Single-step
       state-mutating routes that use the claim_or_run idempotency wrapper
       instead return 409 IDEMPOTENCY_IN_FLIGHT.)
     - Found + request_hash differs → 409 IDEMPOTENCY_CONFLICT.
     - Not found → continue.

4. Begin DB transaction T1:
     INSERT INTO orders (id, api_key_id, customer_id, amount_minor, currency,
                         status=CREATED, psp_name, psp_order_id=NULL,
                         payment_link=NULL, allowed_methods, expires_at=now()+TTL,
                         created_at=now(), updated_at=now()).
     INSERT INTO idempotency_keys (api_key_id, key, request_hash,
                                   response_json=NULL, status_code=NULL,
                                   order_id=<inserted id>,
                                   created_at=now(), expires_at=now()+24h).
   COMMIT T1.

5. Call Lens:
     resp = await facade.create_order(CreateOrderRequest(
         merchant_id=…, order_id=<Orbit's id>, customer_id=…,
         amount=Amount(…), return_url=…, allowed_methods=…,
         idempotency_key=<derived from Orbit order id, deterministic>,
         expires_at=…))

6. Handle result:

     6a. Success → Begin T2:
           UPDATE orders SET psp_order_id, payment_link, updated_at=now()
             WHERE id = <Orbit's id>.
           UPDATE idempotency_keys SET response_json=<the 201 body>,
                                       status_code=201
             WHERE (api_key_id, key) = (…, …).
           INSERT INTO order_events (…, from=NULL, to=CREATED, source='api').
         COMMIT T2.
         Return 201 to caller.

     6b. ConnectorError (PSP-rejected, terminal) → Begin T2:
           UPDATE orders SET status='FAILED', terminally_failed=TRUE,
                              failure_reason=<connector error>, updated_at=now()
             WHERE id = <Orbit's id>.
           UPDATE idempotency_keys SET response_json=<error body>,
                                       status_code=502
             WHERE (api_key_id, key) = (…, …).
           INSERT INTO order_events (…, from='CREATED', to='FAILED',
                                       source='api').
         COMMIT T2.
         Return 502 PSP_ERROR (or appropriate code) to caller. The FAILED row
         is terminal; subsequent retries with the SAME idempotency key get the
         stored 502 back.

     6c. ConnectorError — RETRIABLE class (PSP_TIMEOUT / PSP_UNAVAILABLE /
         RATE_LIMITED; outcome unknown) →
         DO NOT mutate the order's status. The phase-1 INSERTs already committed,
         so the Orbit row persists (psp_order_id=NULL, status=CREATED) and the
         idempotency row stays in-flight (response_json=NULL).
         Return the retriable error to the caller.
         Caller's retry with the SAME idempotency key re-enters this flow and
         RESUMES INLINE: it re-derives the SAME deterministic PSP key
         (orbit-create-order-{order_id}) and re-issues create_order, so the PSP
         dedups instead of double-creating. There is NO background janitor — an
         un-retried in-flight order is eventually swept to EXPIRED by
         orbit-housekeeping (§3.5.1) once expires_at passes.
```

### 3.5 `orbit-housekeeping` — the maintenance cron

**There is no janitor.** In-flight Order recovery is inline-resume (§3.4 6c). A second Lambda, `orbit-housekeeping`, is triggered by EventBridge `rate(1 minute)` and runs four sweeps per tick (`services/housekeeping.py` + `services/mandate_housekeeping.py`). Each tick is a single Lambda invocation, so there is **no advisory-lock leadership election**; concurrency safety for the delivery queue comes from `FOR UPDATE SKIP LOCKED`. There is **no `recovery_attempts` column** and no re-attempt loop for in-flight creates.

**3.5.1 Expired-order sweep.** Transition `CREATED` orders whose `expires_at` has passed (and that have no SUCCESS attempt) → `EXPIRED`, writing an `order_events` row with `source='housekeeping'`. Backed by `orders_expiry_idx` (partial index on `expires_at WHERE status='CREATED'`).

**3.5.2 Idempotency-key prune.** Delete idempotency rows past their `expires_at` (completed rows only — `response_json IS NOT NULL`). Backed by `idempotency_keys_expires_at_idx`.

**3.5.3 Mandate housekeeping** (Phase 3 — §9):
- *Stuck-authorization sweep*: `PENDING_AUTHORIZATION` mandates older than a threshold are confirmed via `sync_subscription`; ones the PSP still reports unauthorized transition → `FAILED`.
- *Active reconcile*: stale `ACTIVE` mandates (by `last_event_at`) are re-synced via `sync_subscription` as a backstop for missed PSP webhooks; a status change emits the corresponding app event (`mandate.cancelled` / `mandate.expired` / …) and a `mandate.reconciled` audit event. Backed by `mandates_active_recon_idx`.

**3.5.4 Consumer-webhook delivery sweep** (Phase 2): claims up to `SWEEP_LIMIT` due rows from `consumer_webhook_deliveries` (`FOR UPDATE SKIP LOCKED`), POSTs each signed payload, and resolves it to `delivered` / `failed_permanent` / re-queued (`pending`, next backoff bucket). Processed **sequentially** within a tick — the claimed rows share one asyncpg connection held open for the claim transaction, and asyncpg connections are not safe for concurrent use. Opt-in: only runs when the handler injects an `httpx.AsyncClient` + a KMS secret-decrypt function (the Lambda entrypoint builds both at cold start; unit tests that pass `db` only keep the two-sweep behaviour).

The expiry + idempotency sweeps and the mandate sweeps always run; the delivery sweep is gated on the HTTP/KMS dependencies being supplied.

### 3.6 Webhook receiver (inline)

`POST /v1/webhooks/{psp_name}/{config_id}` — all work happens **inline** in the request (`services/webhook_processor.py`). There is **no async worker and no `LISTEN/NOTIFY`**; the Lambda processes the event before returning. The path carries `{config_id}` so the per-tenant `psp_merchant_config` (and its webhook secret) can be resolved.

1. Resolve `ConnectorFactory.create_webhook_router(config).handle(raw_body, headers)` → `PaymentWebhookEvent | MandateWebhookEvent`. On signature failure: log internally, return 200 (don't trigger PSP retries on suspected attack traffic).
2. Dedup: look up `(psp_merchant_config_id, psp_event_id)` in `webhook_events` (tenant-scoped PK). If found, return 200 `{"status":"duplicate"}` without further work.
3. INSERT into `webhook_events` (`received_at=now()`, `processed_at=NULL`). "Unprocessed" = `processed_at IS NULL`; no separate `status` column.
4. Dispatch by event type, in the same request:
   - **`PaymentWebhookEvent` with `attempt` (`PAYMENT_*`):** UPSERT `payment_attempts` by `psp_payment_id` (new → status from event; existing → update only if not stale and not already terminal). Recompute the order's status; transition + write `order_events` if it changed.
   - **`PaymentWebhookEvent` with `refund` (`REFUND_*`):** UPDATE `refunds` by `psp_refund_id`; recompute the order's status (may → `PARTIALLY_REFUNDED` / `REFUNDED`); write `order_events`.
   - **`PaymentWebhookEvent` `ORDER_EXPIRED`:** set the order → `EXPIRED` (only if no SUCCESS attempt).
   - **`MandateWebhookEvent`:** route to `services/mandate_processor.py` (§9), which runs `resolve_transition`, persists the mandate / charge change, and enqueues any outbound app webhook.
5. Mark `webhook_events.processed_at = now()`, enqueue matching consumer-webhook deliveries (inline burst on the hot path; §9.6), and return 200 `{"status":"processed"}`.

### 3.7 DB schema

Canonical source: `src/orbit/persistence/schema.sql` (dbmate-dumped) and the
append-only `migrations/`. Reproduced here faithfully (pg_dump noise trimmed).
Migrations are plain SQL applied by **dbmate** — there is **no Alembic, no
SQLAlchemy ORM, no models.py**; all SQL lives in `persistence/repositories/`.

**Payments core**

```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    api_key_id UUID NOT NULL REFERENCES api_keys(id),
    customer_id TEXT NOT NULL,
    amount_minor BIGINT NOT NULL,
    currency TEXT NOT NULL,
    status TEXT NOT NULL,                       -- OrderStatus
    psp_name TEXT NOT NULL,
    psp_merchant_id TEXT NOT NULL,              -- PSP-side merchant id (snapshot)
    psp_merchant_config_id UUID NOT NULL REFERENCES psp_merchant_configs(id),
    psp_order_id TEXT,                          -- NULL while in-flight
    payment_link TEXT,                          -- NULL while in-flight
    return_url TEXT NOT NULL,
    allowed_methods JSONB,
    expires_at TIMESTAMPTZ NOT NULL,
    terminally_failed BOOLEAN NOT NULL DEFAULT FALSE,
    failure_reason TEXT,
    idempotency_key TEXT NOT NULL DEFAULT '',   -- echoed; the create idem key
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);   -- NOTE: no recovery_attempts column (inline-resume, not janitor)
CREATE UNIQUE INDEX orders_psp_order_id_idx ON orders(psp_name, psp_order_id) WHERE psp_order_id IS NOT NULL;
CREATE INDEX orders_in_flight_idx ON orders(created_at) WHERE psp_order_id IS NULL;
CREATE INDEX orders_expiry_idx    ON orders(expires_at) WHERE status = 'CREATED';

CREATE TABLE payment_attempts (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id),
    psp_payment_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,                       -- PaymentAttemptStatus
    method_used TEXT,
    amount_minor BIGINT,
    failure_code TEXT,                          -- PaymentFailureCode
    failure_reason TEXT,
    attempted_at TIMESTAMPTZ NOT NULL,          -- PSP-reported
    received_at TIMESTAMPTZ NOT NULL,           -- when Orbit first saw this
    raw_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX payment_attempts_order_idx ON payment_attempts(order_id);

CREATE TABLE refunds (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id),
    payment_attempt_id UUID NOT NULL REFERENCES payment_attempts(id),
    psp_refund_id TEXT UNIQUE,                  -- NULL only briefly while in-flight
    amount_minor BIGINT NOT NULL,
    status TEXT NOT NULL,                       -- RefundStatus
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE idempotency_keys (
    api_key_id UUID NOT NULL,
    key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    response_json JSONB,                        -- NULL while in-flight
    status_code INT,                            -- NULL while in-flight
    order_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (api_key_id, key)
);
CREATE INDEX idempotency_keys_expires_at_idx ON idempotency_keys(expires_at) WHERE response_json IS NOT NULL;

CREATE TABLE order_events (
    id BIGSERIAL PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id),
    from_status TEXT,
    to_status TEXT NOT NULL,
    source TEXT NOT NULL,                       -- api | webhook | sync | housekeeping | admin
    detail TEXT,
    at TIMESTAMPTZ NOT NULL
);

CREATE TABLE webhook_events (
    psp_name TEXT NOT NULL,
    psp_event_id TEXT NOT NULL,
    psp_merchant_config_id UUID NOT NULL REFERENCES psp_merchant_configs(id),
    order_id UUID REFERENCES orders(id),
    payment_attempt_id UUID REFERENCES payment_attempts(id),
    refund_id UUID REFERENCES refunds(id),
    event_type TEXT NOT NULL,
    raw_payload JSONB,
    received_at TIMESTAMPTZ NOT NULL,
    processed_at TIMESTAMPTZ,
    PRIMARY KEY (psp_merchant_config_id, psp_event_id)   -- tenant-scoped dedup
);
CREATE INDEX webhook_events_unprocessed_idx ON webhook_events(received_at) WHERE processed_at IS NULL;
```

**Tenancy & auth** (multi-tenant; per-tenant KMS-encrypted PSP credentials)

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    consumer_app TEXT NOT NULL,
    hmac_hash BYTEA NOT NULL,                   -- HMAC-SHA256(key, pepper); NOT argon2id
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);
CREATE INDEX api_keys_hmac_idx ON api_keys(hmac_hash);

CREATE TABLE psp_merchant_configs (
    id UUID PRIMARY KEY,
    api_key_id UUID NOT NULL REFERENCES api_keys(id),
    psp_name TEXT NOT NULL,
    psp_merchant_id TEXT NOT NULL,
    encrypted_credentials BYTEA NOT NULL,       -- KMS envelope (api/secret/webhook secret)
    encrypted_data_key BYTEA NOT NULL,
    encryption_context JSONB NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL,
    rotated_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX psp_merchant_configs_active_idx ON psp_merchant_configs(api_key_id, psp_name) WHERE active = TRUE;
```

**Mandates** (Phase 3 — §9)

```sql
CREATE TABLE mandates (
    id UUID PRIMARY KEY,
    api_key_id UUID NOT NULL REFERENCES api_keys(id),
    psp_merchant_config_id UUID NOT NULL REFERENCES psp_merchant_configs(id),
    customer_id TEXT NOT NULL,
    customer_email TEXT NOT NULL,               -- raw (RBI pre-debit); NOT fanned out
    customer_phone TEXT NOT NULL,               -- raw (RBI pre-debit); NOT fanned out
    requested_rails TEXT[],                     -- rails offered at create; NULL/empty = all instruments (customer chooses on the PSP authorization screen)
    realized_rail TEXT,                         -- UPI_AUTOPAY | CARD_EMANDATE; the instrument the customer actually chose, from lens realized_rail. NULL until a successful authorization
    authorization_reference TEXT,               -- UMN/UMRN/enrollment id from lens authorization_reference; NULL until authorized
    status TEXT NOT NULL,                       -- CHECK: 8 MandateStatus values
    amount_minor BIGINT NOT NULL,
    max_amount_minor BIGINT NOT NULL,           -- CHECK amount_minor <= max_amount_minor
    currency TEXT NOT NULL,
    interval_type TEXT NOT NULL,                -- DAY | WEEK | MONTH | YEAR
    interval_count INT NOT NULL DEFAULT 1,
    first_charge_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    max_cycles INT,
    description TEXT NOT NULL,
    return_url TEXT NOT NULL,
    psp_mandate_ref TEXT,                       -- UNIQUE WHERE NOT NULL
    approval_type TEXT,                         -- from lens ApprovalHandle
    approval_url TEXT,
    approval_session_id TEXT,
    next_charge_at TIMESTAMPTZ,
    last_failure_code TEXT,
    last_event_at TIMESTAMPTZ,
    idempotency_key TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX mandates_idem_uq      ON mandates(api_key_id, idempotency_key);
CREATE UNIQUE INDEX mandates_psp_ref_uq   ON mandates(psp_mandate_ref) WHERE psp_mandate_ref IS NOT NULL;
CREATE INDEX mandates_active_recon_idx    ON mandates(status, last_event_at) WHERE status = 'ACTIVE';
CREATE INDEX mandates_customer_idx        ON mandates(api_key_id, customer_id, created_at, id);

CREATE TABLE mandate_charges (
    id UUID PRIMARY KEY,
    mandate_id UUID NOT NULL REFERENCES mandates(id),
    psp_debit_id TEXT NOT NULL,
    status TEXT NOT NULL,                       -- CHECK: PENDING | SUCCESS | FAILED
    amount_minor BIGINT NOT NULL,
    currency TEXT NOT NULL,
    failure_code TEXT,
    psp_attempt INT,                            -- PSP-reported retry attempt number
    occurred_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX mandate_charges_debit_uq ON mandate_charges(mandate_id, psp_debit_id);

CREATE TABLE mandate_events (                   -- append-only timeline
    id UUID PRIMARY KEY,
    mandate_id UUID NOT NULL REFERENCES mandates(id),
    event_type TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX mandate_events_mandate_idx ON mandate_events(mandate_id, created_at);
```

**Outbound consumer webhooks** (Phase 2 — §9.6)

```sql
CREATE TABLE webhook_subscriptions (
    id UUID PRIMARY KEY,
    api_key_id UUID NOT NULL REFERENCES api_keys(id),
    url TEXT NOT NULL,
    encrypted_secret BYTEA NOT NULL,            -- KMS envelope (HMAC signing secret)
    encrypted_data_key BYTEA NOT NULL,
    encryption_context JSONB NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ,
    event_types TEXT[] NOT NULL                 -- per-event-type filter (C1)
        DEFAULT ARRAY['order.status_changed','refund.status_changed']
);
CREATE INDEX webhook_subscriptions_active_idx ON webhook_subscriptions(api_key_id) WHERE active = TRUE;

CREATE TABLE consumer_webhook_deliveries (
    id UUID PRIMARY KEY,
    subscription_id UUID NOT NULL REFERENCES webhook_subscriptions(id),
    event_type TEXT NOT NULL,
    event_id UUID NOT NULL,                     -- mirrored as X-Orbit-Webhook-Id
    payload JSONB NOT NULL,
    status TEXT NOT NULL,                       -- CHECK: pending | delivered | failed_permanent
    attempts SMALLINT NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NOT NULL,
    last_attempted_at TIMESTAMPTZ,
    last_status_code INT,
    last_error TEXT,
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE -- the /test trigger
);
CREATE INDEX consumer_webhook_deliveries_due_idx ON consumer_webhook_deliveries(next_attempt_at, id) WHERE status = 'pending';
```

All amounts are minor units (integer). No floats anywhere.

---

## §4. Dependencies

- **Lens** (constitution Layer 2; in-process Python import). Installed from SyPI as `lens` (e.g. `lens>=0.2.0,<0.3`). Distribution name and import name are both `lens`. Source lives at `/Users/sarthak/PycharmProjects/symplora/sylibs/packages/lens/`.
- Python ≥ 3.11.
- `fastapi` + `mangum` (Lambda adapter); `uvicorn` for local dev only.
- `pydantic` v2 + `pydantic-settings` (config).
- `asyncpg` (direct Postgres driver — **no SQLAlchemy, no ORM**; RDS Proxy in prod).
- `dbmate` (plain-SQL migrations — **not Alembic**; append-only).
- `boto3` (KMS envelope encryption + Secrets Manager).
- `httpx` (outbound consumer-webhook delivery; lens owns its own client for PSP calls).
- `sykit` (JSON logging). **No `structlog`. No `argon2-cffi`** — API keys are HMAC-SHA256 + pepper.
- Postgres ≥ 15.

---

## §5. Non-functional requirements

Inherits constitution §6. Additions:

- API p99 < 500ms (excluding any PSP-side latency surfaced through `payment_link`).
- Webhook endpoint: processing is **inline** (synchronous). The inline consumer-webhook burst is time-boxed with a short per-attempt timeout; overflow/retries are handed to the `orbit-housekeeping` queue sweep.
- Idempotency-key TTL configurable; default 24h.
- DB connection pool: asyncpg pool (RDS Proxy in prod).
- Migrations: applied by **dbmate** from `persistence/migrations/`. The CI deploy job runs migrations against the target DB **before** the SAM deploy; migrations do **not** run at Lambda cold start (and there is no `alembic`).
- API key rotation: zero-downtime; old + new keys both valid during the rotation window.
- KMS envelope encryption for all per-tenant PSP credentials and webhook secrets; the API-key pepper + admin token are resolved from Secrets Manager at lifespan startup (`.strip()`'d).
- All money fields integer minor units.
- `orbit-housekeeping` cron cadence: EventBridge `rate(1 minute)`. There is no janitor and no per-order recovery-attempt counter (in-flight recovery is inline-resume).

### §5.1 PII handling

Two complementary controls: **never log secrets/PII**, and **never fan out PII to consumer webhook URLs**. Storage-at-rest differs by field:

- **API-key secret** (bearer token in `Authorization`) — verified by **HMAC-SHA256 over the secret with a server-side pepper**; only the digest is stored, in `api_keys.hmac_hash` (`bytea`). There is **no argon2id**. The plaintext exists only in memory between extraction and the constant-time HMAC comparison and is never logged.
- **PSP credentials + webhook signing secrets** — stored **KMS-envelope-encrypted** (`psp_merchant_configs`, `webhook_subscriptions`); decrypted in-memory only at the moment of a PSP call or signature verification.
- **Mandate `customer_email` / `customer_phone`** (Phase 3) — stored **RAW** in `mandates` (Cashfree needs them for the RBI pre-debit notification). Deliberate decision: they are **excluded from every outbound consumer-webhook payload** (`MandateSnapshot` in `domain/mandate_event_payload.py` omits them) and from all log lines. Raw at rest, never fanned out.
- `customer_id` is an opaque per-tenant identifier; callers are advised not to embed email/phone in it.

Forbidden in logs entirely: full PAN (16 contiguous digits), CVV, bank account number, IFSC + account combination, full UPI VPA, and the mandate email/phone.

Logging uses stdlib `logging` with a `sykit` JSON formatter (**not `structlog`**). Where a PII value must transit a model that could be logged, the `Maskable[T]` wrapper (from lens) stringifies it as `***`. Acceptance: "No PII in any log line" is verified by a log-scrubbing test.

---

## §6. Acceptance criteria for v1

- [ ] All endpoints in §2 exist and return the documented shapes.
- [ ] Happy-path end-to-end test:
    - `POST /v1/orders` returns `payment_link`.
    - User completes payment on Cashfree sandbox.
    - `PAYMENT_SUCCESS_WEBHOOK` arrives → `payment_attempts` row created with `status=SUCCESS` → Order transitions to `PAID` (verified in `order_events` and `GET /v1/orders/{id}`).
    - `POST /v1/orders/{id}/refund` creates a `refunds` row.
    - `REFUND_SUCCESS` webhook → Order transitions to `REFUNDED`.
- [ ] **Multi-attempt test**: simulate a Cashfree order where attempt 1 fails (USER_DROPPED webhook) and attempt 2 succeeds. Verify:
    - Two rows in `payment_attempts` for the same `order_id`.
    - First row: `status=FAILED`, `failure_code=USER_DROPPED`.
    - Second row: `status=SUCCESS`.
    - Order's status: `PAID`.
- [ ] **`sync_payment` recovery test**: PAYMENT_SUCCESS webhook is dropped; `POST /v1/orders/{id}/sync` recovers the state.
- [ ] **Orbit-first creation flow tests**:
    - PSP `create_order` succeeds → order in `CREATED` with `psp_order_id` set.
    - PSP `create_order` returns 4xx → order in `FAILED`, idempotency record holds the error response.
    - PSP `create_order` times out (retriable) → order stays with `psp_order_id=NULL`, status `CREATED`; idempotency row stays in-flight; a caller retry with the SAME idempotency key resumes inline against the same deterministic PSP key. An un-retried order is swept to `EXPIRED` by housekeeping once `expires_at` passes.
- [ ] **Inline-resume test**: simulate a retriable PSP error mid-create, then retry with the same idempotency key → the same PSP key is reused (PSP dedups) and the order completes with one PSP-side order.
- [ ] Idempotency tests: same key returns stored response; mismatched body returns 409; in-flight key returns 409 with `IDEMPOTENCY_IN_FLIGHT`.
- [ ] Webhook tests: signed-good, tampered, duplicate, out-of-order all handled correctly.
- [ ] State-machine tests: every allowed Order/PaymentAttempt/Refund transition exercised; every disallowed transition rejected.
- [ ] `mypy --strict` clean.
- [ ] `pytest --cov` ≥ 80%.
- [ ] `docker-compose up` brings up Postgres + Orbit + a Cashfree-sandbox-or-mock for local dev.
- [ ] `/healthz` and `/readyz` return correct states.
- [ ] API key creation + rotation + revocation flows tested.
- [ ] No PII in any log line, verified by a log-scrubbing test.

---

## §7. Roadmap

Maps to constitution §9 Step 6. **All steps below are delivered** — kept for traceability; tool/design choices that changed during implementation are flagged inline (dbmate not Alembic; inline-resume not janitor; inline webhook processing not an async worker).

1. **Project skeleton** — FastAPI app, config, logging, asyncpg pool, dbmate. ~1 day.
2. **DB schema + migrations** — All tables in §3.7. ~1 day.
3. **Domain state machines** — Order + PaymentAttempt + Refund; pure domain logic; fully unit-tested. ~2 days.
4. **API skeleton** — All routes in §2 return stub responses; OpenAPI schema generated. ~1 day.
5. **Idempotency middleware** — Wired in before any state-mutating route. ~1.5 days.
6. **Orbit-first creation flow** — `POST /v1/orders` with the two-transaction pattern from §3.4. ~1.5 days.
7. **Lens integration** — Wire `PaymentsFacade` into `/sync`, `/refund`, `/refunds/{id}/sync` endpoints. ~2 days.
8. **Webhook receiver (inline)** — Verify → dedup → process synchronously. ~2.5 days.
9. **Housekeeping cron** — `orbit-housekeeping` (expiry sweep + idempotency prune; later mandate recon + consumer-webhook queue). Inline-resume replaced the janitor. ~1 day.
10. **API-key auth** — HMAC-SHA256 + pepper, per-tenant keys, rotation. ~1 day.
11. **End-to-end sandbox test** — Happy path + multi-attempt + sync-recovery + inline-resume from §6. ~1.5 days.
12. **Operational endpoints + observability** — `/healthz`, `/readyz`, metrics. ~1 day.
13. **Docs** — README, API reference, runbook. ~1 day.

Total: ~17 days single-agent. Parallelizable: 1–3 split nicely; 4–11 mostly serial.

---

## §8. Open questions for the implementing agent

- **Q1**: Postgres or another store? **Resolved**: Postgres (asyncpg; RDS Proxy in prod). *(The earlier "LISTEN/NOTIFY worker queue" idea was dropped — webhook processing is inline and the retry queue is swept by orbit-housekeeping; see Q2.)*
- **Q2**: Async worker mechanism — `LISTEN/NOTIFY`, Celery, or in-process `asyncio` task queue? **Resolved**: none — webhook processing is **inline** (synchronous) in the request; deferred retry/delivery work is handled by the `orbit-housekeeping` EventBridge cron. No `LISTEN/NOTIFY`, no Celery.
- **Q3**: Should housekeeping also poll PSPs for `CREATED` orders whose only attempts are stuck in `PENDING` (e.g., `FRAUD_REVIEW_PENDING`)? **Status**: not implemented for orders (callers can force a `POST /v1/orders/{id}/sync`). The analogous backstop *is* implemented for mandates — `orbit-housekeeping` reconciles stale `ACTIVE` mandates via `sync_subscription` (§3.5.3). Add an order-side equivalent if PSP webhook-reliability data warrants it.
- **Q4**: When a duplicate `SUCCESS` event arrives for an order that already has a `SUCCESS` attempt: log + drop, or upsert and alert? **Recommendation**: log + drop, increment a metric; alert if rate exceeds a threshold. (Duplicates are usually webhook replays; legitimate.)
- **Q5**: API auth — bearer token alone, or also IP allow-list? **Recommendation**: token only inside Orbit; IP allow-list is a Cloudflare / ingress concern.
- **Q6**: Hashing — argon2 or bcrypt? **Resolved**: neither — API keys are verified by **HMAC-SHA256 + a server-side pepper** (constant-time compare), not a password hash. The threat model (high-entropy machine-generated keys, not user passwords) makes a keyed MAC the right primitive.
- **Q7**: `POST /v1/orders` idempotency: same key returns same order. Confirmed (§3.4).
- **Q8**: Multi-currency is out of scope. Schema carries `currency` for forward-compat; v1 rejects any currency that mismatches the configured PSP currency for the consumer app.
- **Q9**: What's the canonical `customer_id` namespace — per consumer app? **Recommendation**: per consumer app (each API key has its own customer namespace).
- **Q10**: Should `GET /v1/orders/{id}` always include the `attempts` array, or is there a separate `/v1/orders/{id}/attempts` endpoint with pagination? **Recommendation**: nested in v1 (orders rarely have more than 3–4 attempts). Add the separate endpoint with pagination if a real workload demands it.
- **Q11**: Deterministic PSP key for in-flight retries — derived or stored? **Resolved**: derived (`orbit-create-order-{order_id}`), reused by **inline-resume** (there is no janitor). One less column.
- **Q12** (constitution OQ-10): janitor cadence + max recovery attempts. **Resolved**: no janitor. `orbit-housekeeping` runs at `rate(1 minute)`; in-flight recovery is inline-resume (no recovery-attempt counter).

---

## §9. Phase 3 — Periodic subscription mandates

### 9.1 Scope

Periodic subscription mandates are **now in scope** (Phase 3). Orbit offers a trial → auto-debit → recurring billing lifecycle on Cashfree via lens 0.2.0. Supported rails: UPI Autopay and card e-mandate, INR.

**On-demand / merchant-triggered debit** (`execute_mandate_debit` / `notify_pre_debit`) remains **out of scope**. In periodic mode Cashfree owns the debit schedule, retries, and RBI pre-debit notifications entirely; Orbit configures the mandate once at create and then reacts to webhooks.

### 9.2 What orbit consumes from lens 0.2.0

Orbit holds two facade instances (one per domain) and one shared webhook entry:

- **`MandatesFacade`** — resolved via `ConnectorFactory.create_mandates_facade(config)` (raises `ConnectorError(NOT_SUPPORTED)` if the PSP is not mandate-capable). Lifecycle methods orbit calls:
  - `await mandates_facade.create_subscription(CreateSubscriptionRequest(...))`
  - `await mandates_facade.sync_subscription(SyncSubscriptionRequest(...))`
  - `await mandates_facade.cancel_subscription(ManageMandateRequest(...))`
  - `await mandates_facade.pause_subscription(ManageMandateRequest(...))`
  - `await mandates_facade.resume_subscription(ManageMandateRequest(...))`
  - `await mandates_facade.create_plan(CreatePlanRequest(...))` — v0.9 (plan upgrade/downgrade)
  - `await mandates_facade.change_plan(ChangePlanRequest(...))` — v0.9
- **`WebhookRouter`** — resolved via `ConnectorFactory.create_webhook_router(config)`. The router's single async method `handle(raw_payload, headers)` verifies the PSP signature once and returns `PaymentWebhookEvent | MandateWebhookEvent` by event family. Orbit branches on the type: payment events go to the existing payment processor; mandate events go to the mandate processor (§9.4).
- **Mandate domain types and enums**: `CreateSubscriptionRequest`/`CreateSubscriptionResponse`, `SyncSubscriptionRequest`/`SyncSubscriptionResponse`, `ManageMandateRequest`/`ManageMandateResponse`, `CustomerContact`, `ApprovalHandle`, `MandateDebitOutcome`, `MandateWebhookEvent`, `MandateRail`, `MandateStatus`, `MandateIntervalType`, `MandateDebitStatus`, `WebhookEventType` (extended with 13 `MANDATE_*` values).
  - **Customer-chosen rail (lens 0.3.0):** `CreateSubscriptionRequest.rails: list[MandateRail] | None` — Orbit passes the set of instruments to offer (or `None`/empty to offer all); the customer picks one on the PSP authorization screen. lens reports the **realized** instrument back on a successful authorization via three fields carried on **both** `MandateWebhookEvent` and `SyncSubscriptionResponse`: `realized_rail: MandateRail | None`, `authorization_reference: str | None` (UMN/UMRN/enrollment id), and the raw `payment_group: str | None`. Orbit persists `realized_rail` + `authorization_reference` on the mandate row (§3.7) on `MANDATE_AUTHORIZED` (or via the sync reconcile backstop if that webhook is missed).
  - **Plan upgrade/downgrade (lens 0.4.0):** `create_plan(CreatePlanRequest) -> CreatePlanResponse` (create a reusable PSP plan → `plan_id`) and `change_plan(ChangePlanRequest) -> ManageMandateResponse` (move an active periodic subscription onto `new_plan_id`). Orbit's in-place **upgrade** stays orbit-side (re-auth via `CreateSubscriptionRequest.authorization_amount`); the **downgrade** path and the lower-friction all-rail upgrade alternative call `create_plan` then `change_plan`. Cashfree enforces "new recurring amount ≤ the authorized `plan_max_amount`" and is PERIODIC-only → `ConnectorError(INVALID_REQUEST)` with the PSP code/message; customers are **not** notified of plan changes. New types: `CreatePlanRequest`, `CreatePlanResponse`, `ChangePlanRequest`.
- **`FAILURE_CLASS`** (`MappingProxyType[PaymentFailureCode, FailureClass]`) — published classification data exported by lens. Orbit reads it to decide whether a debit failure is retriable or terminal (`charge_failed` vs. `charge_failed_final`). Lens never branches on it (stateless).

### 9.3 Division of labor — periodic mode

**Cashfree's responsibility (Orbit does not replicate these):**
- Debit schedule and execution.
- Retry cadence and attempts (exposed via `psp_attempt` on `MandateDebitOutcome`). Note: the retry cadence is Cashfree's, not the fixed 24/48/72h intervals described in earlier PRD drafts; consumer apps must not assume fixed intervals.
- RBI-mandated pre-debit notification (`MANDATE_DEBIT_NOTIFIED` webhook — lens emits this; Orbit may forward it as an app webhook).
- Card pre-expiry reminder (`MANDATE_EXPIRING_SOON` — cards only; no equivalent for UPI/eNACH).

**Orbit's responsibility:**
- Mandate, charge, and event records (data model in §3.7; full design in §9.5 — implemented).
- Mandate state machine (`domain/mandate.py::resolve_transition`; table in §9.5). Key transition: `MANDATE_SUSPENDED` (← Cashfree `ON_HOLD`) is the finality signal — payment-failure suspension only (merchant/customer pauses are the distinct `PAUSED` status); Orbit transitions the mandate to `SUSPENDED` and emits `mandate.charge_failed_final`. As a fallback, a `MANDATE_DEBIT_FAILED` whose `FAILURE_CLASS` is `TERMINAL` also drives `SUSPENDED` + `mandate.charge_failed_final`. `psp_attempt` on `MANDATE_DEBIT_FAILED` is kept for attempt-level telemetry.
- Outbound app webhooks — the 12 events emitted by `resolve_transition`: `mandate.created`, `mandate.failed`, `mandate.charged`, `mandate.charge_failed`, `mandate.charge_failed_final`, `mandate.paused`, `mandate.resumed`, `mandate.cancelled`, `mandate.expired`, `mandate.completed`, `mandate.debit_pending`, `mandate.expiring_soon` (plus a `mandate.reconciled` audit event from the housekeeping reconcile). **Note the actual names:** a successful debit is **`mandate.charged`** (not `mandate.charge_succeeded`), and there is **no separate `mandate.suspended`** event — suspension surfaces as `mandate.charge_failed_final`. `mandate.created` corresponds to `MANDATE_AUTHORIZED` from lens (not the `create_subscription` call, which yields `PENDING_AUTHORIZATION`).
- Reconciliation via `sync_subscription` (housekeeping; §3.5.3). Because `sync_subscription` carries the same `realized_rail` / `authorization_reference` / `payment_group` as the auth webhook, a mandate whose `MANDATE_AUTHORIZED` webhook was dropped still has its customer-chosen rail recovered on the next reconcile (recorded onto the mandate row if not already set).
- Suspension decision: on `MANDATE_SUSPENDED`, orbit transitions the mandate to `SUSPENDED` and emits the final-failure app webhook. `ON_HOLD` is definitionally payment-failure-only, so `MANDATE_SUSPENDED` is the unambiguous final-failure signal.

**Cancel semantics:** cancel is best-effort. An already-notified or in-flight debit may still settle after `cancel_subscription` is called (L12 — Cashfree states no cutoff for in-flight debits). Orbit must reconcile via `sync_subscription` rather than treating `cancel_subscription` as an immediate stop.

### 9.4 New PII surface

`CustomerContact{email: str, phone: str}` (both required — Cashfree needs them for the RBI pre-debit notification) is forwarded on `create_subscription`. This is a **new PII surface for orbit** — previously Orbit forwarded only an opaque `customer_id`. **Decision (implemented):** `customer_email` / `customer_phone` are stored **RAW** in `mandates` (Orbit needs them for the PSP handshake), and are **excluded from every outbound consumer-webhook payload** (`MandateSnapshot` omits them) and from all logs. They are *not* `Maskable`-wrapped at rest; the §5.1 controls (no-PII-in-logs, no-PII-in-fan-out) are how they're protected.

### 9.5 Implemented orbit-internal mandate design

All items below are **shipped** (the data model is in §3.7; lens-boundary in §9.2).

**REST surface** (`/v1/mandates/*`, tenant-API-key-gated; idempotent creates via `claim_or_run`):

```
POST   /v1/mandates                    # create — body below; 201 returns the approval handle
GET    /v1/mandates                    # list (status?, customer_id?, cursor, limit)
GET    /v1/mandates/{id}               # full mandate (tenant-scoped; 404 MANDATE_NOT_FOUND)
POST   /v1/mandates/{id}/cancel        # ManageMandateRequest
POST   /v1/mandates/{id}/pause         # ManageMandateRequest
POST   /v1/mandates/{id}/resume        # ResumeMandateRequest
GET    /v1/mandates/{id}/charges       # debit history (mandate_charges)
```

Note there is **no `PATCH /v1/mandates/{id}`** — lifecycle changes are explicit `cancel`/`pause`/`resume` sub-routes.

`POST /v1/mandates` body: `customer_id`, `customer_email`, `customer_phone`, `rails?` (array of `UPI_AUTOPAY`|`CARD_EMANDATE`; omit or empty = offer all supported instruments and let the customer choose on the PSP authorization screen), `amount_minor`, `max_amount_minor` (validated `amount_minor <= max_amount_minor`), `currency` (`INR`), `interval_type` (`DAY`|`WEEK`|`MONTH`|`YEAR`), `interval_count` (default 1), `first_charge_at?`, `expires_at`, `max_cycles?`, `description`, `return_url`, `upi_vpa?`. The 201 response carries `id`, `status` (`PENDING_AUTHORIZATION`), and an `approval` block `{type, url, session_id}` taken **verbatim** from the lens `ApprovalHandle` (persisted on the row; never fabricated) so the consumer can redirect the customer to authorize the mandate.

**Facade resolution** (`integration/lens.py::resolve_mandates_facade(config_id)`):
- *Create* (`POST`): resolve the tenant's **first active** PSP config (`PSP_NOT_CONFIGURED` if none) and record its id on the mandate row.
- *Manage* (`cancel`/`pause`/`resume`): load the mandate first (tenant-scoped; 404 if missing), then resolve the facade from the mandate's stored `psp_merchant_config_id` — so a tenant that rotated PSP configs after creation still manages the mandate against the *original* config.

**Creation flow** mirrors the order create's discipline: a deterministic `mandates.id` + a `(api_key_id, idempotency_key)` unique index make retries safe (replay the stored row or resume the PSP call). Until a real Cashfree mandate connector ships, `resolve_mandates_facade` raises `PSP_NOT_CONFIGURED` for live calls; orbit's logic is exercised against `FakeMandatesFacade` in tests.

**Webhook → mandate state machine** (`domain/mandate.py::resolve_transition(current, event_type, failure_class) -> (new_status, app_event)`). Statuses: `PENDING_AUTHORIZATION`, `ACTIVE`, `PAUSED`, `SUSPENDED`, `CANCELLED`, `EXPIRED`, `COMPLETED`, `FAILED`. Terminal states (`CANCELLED`, `EXPIRED`, `COMPLETED`, `FAILED`) are guarded — any event into them is a no-op.

| lens `event_type` | new status | app event |
|---|---|---|
| `MANDATE_AUTHORIZED` | `ACTIVE` | `mandate.created` |
| `MANDATE_REJECTED` / `MANDATE_FAILED` | `FAILED` | `mandate.failed` |
| `MANDATE_DEBIT_SUCCESS` | *(unchanged)* | `mandate.charged` |
| `MANDATE_DEBIT_FAILED` (`FAILURE_CLASS`=`TERMINAL`) | `SUSPENDED` | `mandate.charge_failed_final` |
| `MANDATE_DEBIT_FAILED` (retriable) | *(unchanged)* | `mandate.charge_failed` |
| `MANDATE_SUSPENDED` | `SUSPENDED` | `mandate.charge_failed_final` |
| `MANDATE_PAUSED` | `PAUSED` | `mandate.paused` |
| `MANDATE_RESUMED` | `ACTIVE` | `mandate.resumed` |
| `MANDATE_CANCELLED` / `MANDATE_REVOKED` | `CANCELLED` | `mandate.cancelled` |
| `MANDATE_EXPIRED` | `EXPIRED` | `mandate.expired` |
| `MANDATE_COMPLETED` | `COMPLETED` | `mandate.completed` |
| `MANDATE_DEBIT_NOTIFIED` | *(unchanged)* | `mandate.debit_pending` |
| `MANDATE_EXPIRING_SOON` | *(unchanged)* | `mandate.expiring_soon` |

The inbound mandate webhook is processed **inline** (§3.6 step 4) by `services/mandate_processor.py`: it runs `resolve_transition`, upserts the `mandate_charges` row for debit events (deduped on `(mandate_id, psp_debit_id)`), writes a `mandate_events` row, and enqueues the app webhook. Reconciliation + stuck-authorization sweeps run in housekeeping (§3.5.3).

### 9.6 Outbound consumer webhooks (Phase 2)

Tenants receive `order.*` / `refund.*` / `mandate.*` events at operator-registered URLs (`/admin/.../webhook-subscriptions`). Each subscription stores a KMS-encrypted HMAC signing secret and an `event_types[]` filter (default `{order.status_changed, refund.status_changed}`; a subscription only receives an event whose type is in its array — the **C1 per-event-type filter**).

Delivery has two stages:
- **Inline burst** on the producing request's hot path: up to `INLINE_MAX_ATTEMPTS` (3) quick signed POST attempts with a short per-attempt timeout; success marks the row `delivered`.
- **Queue sweep** in `orbit-housekeeping` (§3.5.4): unfinished rows in `consumer_webhook_deliveries` are retried on a backoff schedule (`QUEUE_BACKOFF_SECONDS` = 30m, 4h) until `delivered` or `failed_permanent` at `MAX_ATTEMPTS` (5).

**Signature contract** (`services/consumer_webhook_delivery.py`): each POST carries
- `X-Orbit-Webhook-Id: <event_id>`
- `X-Orbit-Timestamp: <unix epoch seconds>`
- `X-Orbit-Signature: t=<ts>,v1=<hex>`, where `<hex>` is `HMAC-SHA256(secret, f"{ts}.".encode() + raw_body)`.

Receivers verify with `hmac.compare_digest` and may reject stale timestamps. The `/test` admin route enqueues a synthetic (`is_synthetic=TRUE`, `X-Orbit-Synthetic: true`) event so a tenant can validate their endpoint. PII discipline (§5.1): mandate outbound payloads carry a `MandateSnapshot` that **omits** `customer_email` / `customer_phone`.

This section documents the implemented Orbit-owned design; the lens boundary is §9.2.
