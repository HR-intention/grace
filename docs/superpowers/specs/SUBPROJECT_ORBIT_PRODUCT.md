# Sub-project: Orbit (product)

**Inherits from**: `ORBIT_CONSTITUTION.md`. Conflicts resolve in favor of the constitution.
**Owner**: TBD per implementing agent.
**Location**: `/Users/sarthak/PycharmProjects/symplora/orbit/`
**Status**: v0.4 — Order + PaymentAttempt two-entity model; Orbit-first creation flow with janitor recovery.

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
- Janitor job that recovers Orders stuck "in flight" (Orbit row exists, no `psp_order_id` yet).
- Idempotency on every state-mutating endpoint.
- Webhook receiver endpoint that delegates verification + parsing to Lens, dedups locally, and updates the relevant entity.
- Single configured PSP (Cashfree), single tenant per deployment.

**Out of scope for v1**

- Subscriptions, billing cycles, invoices.
- Multi-tenancy.
- Direct-API payment-method handling (constitution §7). Future scope: `FUTURE_S2S_INTERFACE.md`.
- `authorize` / `capture` / `void` endpoints. Hosted-checkout's auto-capture means there's no separate capture step.
- A second PSP in production.
- Apps importing Lens directly.

---

## §2. Public surface

REST API versioned at `/v1`. All requests and responses JSON. All state-mutating endpoints require an `Idempotency-Key` header (UUID v4).

### 2.1 Orders

```
POST /v1/orders
  body: {
    amount: { minor_units: int, currency: "INR" },
    customer_id: str,                        # required
    return_url: HttpUrl,
    allowed_methods?: ["CARD", "UPI", ...]
  }
  → 201 Created
    {
      order_id: str,                          # Orbit's id (UUID)
      status: "CREATED",
      amount: { minor_units: int, currency: "INR" },  # echo for client verification
      payment_link: HttpUrl,                  # PSP-hosted page
      expires_at: ISO8601,
      created_at: ISO8601
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
POST /v1/webhooks/{psp_name}
  (PSP-signed; Orbit verifies via Lens.PaymentsFacade.incoming_webhook)
  → 200 OK    # always; dedup + processing happens async
```

### 2.3 Operational

```
GET /healthz                # liveness
GET /readyz                 # readiness (DB + Lens both ready)
GET /v1/connectors          # registered PSPs + their health
```

### 2.4 Authentication

Bearer token in `Authorization` header. v1 uses a single API key per consumer app, hashed in DB with argon2id. Old + new keys both valid during a rotation window.

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

`OrbitErrorReason` enum: `INVALID_REQUEST`, `UNAUTHENTICATED`, `FORBIDDEN`, `IDEMPOTENCY_CONFLICT`, `IDEMPOTENCY_IN_FLIGHT`, `ORDER_NOT_FOUND`, `ORDER_NOT_PAID`, `ORDER_FULLY_REFUNDED`, `REFUND_NOT_FOUND`, `REFUND_AMOUNT_EXCEEDS_REMAINING`, `PSP_ERROR`, `PSP_UNAVAILABLE`, `PSP_TIMEOUT`, `INTERNAL`.

---

## §3. Internal architecture

```
orbit/
  src/orbit/
    main.py                     # FastAPI app entrypoint
    api/
      __init__.py
      orders.py                 # /v1/orders/*
      webhooks.py               # /v1/webhooks/{psp_name}
      ops.py                    # /healthz, /readyz, /v1/connectors
      errors.py                 # exception handlers → JSON error shape
      auth.py                   # bearer-token middleware
    domain/
      order.py                  # Order aggregate + state machine
      payment_attempt.py        # PaymentAttempt aggregate + state machine
      refund.py                 # Refund aggregate + state machine
      idempotency.py            # IdempotencyKey + dedup logic
      status_map.py             # PSP→Orbit mapping helpers (mostly thin; logic in
                                # Lens's status_map.py)
      events.py                 # Domain events
    persistence/
      db.py                     # async DB engine + session factory
      models.py                 # SQLAlchemy ORM
      migrations/               # Alembic
    integration/
      lens.py      # thin wrapper around PaymentsFacade
      webhook_dispatcher.py     # routes incoming webhooks → PaymentsFacade
    background/
      webhook_worker.py         # async processor for queued webhook events
      janitor.py                # in-flight Order recovery (see §3.5)
    config.py                   # pydantic-settings
    logging.py                  # structlog setup
    tests/
      unit/
      integration/
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

Every transition writes an `order_events` row (`from_status`, `to_status`, `source`, `at`). Source ∈ `{api, webhook, sync, janitor, admin}`. This is the `timeline` field on `GET /v1/orders/{id}`.

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
     - Found + response NULL (in-flight) → return 409 IDEMPOTENCY_IN_FLIGHT
       (caller should retry after a short delay; janitor will eventually
       resolve the in-flight row).
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

     6c. ConnectorError (network / timeout — outcome unknown) →
         DO NOT mutate the order's status.
         Begin T2:
           UPDATE idempotency_keys SET status_code=503 (transient marker)
             WHERE (api_key_id, key) = (…, …).
         COMMIT T2.
         Return 503 to caller. The order row stays with psp_order_id=NULL.
         Caller's retry with the SAME idempotency key:
           - Step 3 finds the in-flight idempotency record.
           - Returns 409 IDEMPOTENCY_IN_FLIGHT, OR (preferred) the handler
             can re-attempt step 5 inline. Pick one and apply consistently.
             v1 default: return 409; janitor recovers it.
```

### 3.5 Janitor — in-flight Order recovery

A background task (one per Orbit process, leadership election via Postgres advisory lock if running multi-process) runs every minute:

```python
async def janitor_tick():
    stuck = await db.fetch_all("""
        SELECT id, api_key_id, customer_id, amount_minor, currency,
               return_url, allowed_methods, recovery_attempts, created_at
        FROM orders
        WHERE psp_order_id IS NULL
          AND status = 'CREATED'
          AND created_at < now() - interval '5 minutes'
          AND (recovery_attempts < 3 OR recovery_attempts IS NULL)
        ORDER BY created_at
        LIMIT 50
    """)
    for order in stuck:
        await try_recover(order)

async def try_recover(order):
    try:
        resp = await facade.create_order(CreateOrderRequest(
            merchant_id=order.merchant_id,
            order_id=order.id,
            customer_id=order.customer_id,
            amount=Amount(...),
            return_url=order.return_url,
            allowed_methods=order.allowed_methods,
            idempotency_key=derive_idem_key(order),  # SAME key as initial call
            expires_at=order.expires_at,
        ))
        # PSP either returns the existing order (if it was created earlier) or
        # creates fresh; same idempotency-key dedupe behavior.
        await db.execute("""
            UPDATE orders
            SET psp_order_id=:psp_order_id, payment_link=:payment_link,
                updated_at=now(), recovery_attempts=COALESCE(recovery_attempts, 0) + 1
            WHERE id = :id
        """, ...)
        await emit_event(order.id, from='CREATED', to='CREATED',
                          source='janitor', detail='recovered')
    except ConnectorError as e:
        recovery_attempts = (order.recovery_attempts or 0) + 1
        if recovery_attempts >= 3:
            await db.execute("""
                UPDATE orders SET status='FAILED', terminally_failed=TRUE,
                                   failure_reason=:reason, updated_at=now(),
                                   recovery_attempts=:attempts
                WHERE id = :id
            """, ...)
            await emit_event(order.id, from='CREATED', to='FAILED',
                              source='janitor', detail=f'recovery exhausted: {e.reason}')
        else:
            await db.execute("""
                UPDATE orders SET recovery_attempts=:attempts, updated_at=now()
                WHERE id = :id
            """, attempts=recovery_attempts)
```

Notes:

- `recovery_attempts` is a column on `orders`. Initialized 0; incremented per janitor run.
- The `derive_idem_key` function is deterministic from the Orbit order id (e.g., `f"orbit-create-order-{order.id}"`). Same key every retry → PSP dedups.
- Cadence: 60s default; configurable.
- Concurrency: single janitor per Orbit deployment via a Postgres advisory lock (`pg_try_advisory_lock(N)` at tick start, release at end). Other processes skip the tick.

### 3.6 Webhook receiver

`POST /v1/webhooks/{psp_name}`:

1. Synchronously call `PaymentsFacade.incoming_webhook(raw_body, headers)` → `WebhookEvent`. On signature failure: log internally, return 200 (avoid triggering unnecessary PSP retries on suspected attack traffic).
2. Look up `(psp_name, psp_event_id)` in `webhook_events`. If found, return 200 without further work (dedup).
3. Insert into `webhook_events` (`received_at=now()`, `processed_at=NULL`). "Unprocessed" is detected by `processed_at IS NULL`; there is no separate `status` column on this table.
4. Notify the async worker via Postgres `LISTEN/NOTIFY`.
5. Return 200 immediately to the PSP.

Async worker:

- Pull queued events.
- For events with `attempt` populated (`PAYMENT_*`):
  - UPSERT `payment_attempts` row by `(psp_payment_id)`. If new row → status from the event; if existing → only update if the event is not stale (timestamp comparison) and the existing row isn't already terminal.
  - Recompute the parent order's status; transition if it changed; write `order_events`.
- For events with `refund` populated (`REFUND_*`):
  - UPDATE `refunds` row by `(psp_refund_id)` with the new status.
  - Recompute the order's status (may transition to `PARTIALLY_REFUNDED` or `REFUNDED`); write `order_events`.
- For `ORDER_EXPIRED`:
  - UPDATE the order's status to `EXPIRED` (only if no `SUCCESS` attempt exists).
- Mark `webhook_events.processed_at = now()`.

### 3.7 DB schema (sketch)

```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    api_key_id UUID NOT NULL REFERENCES api_keys(id),
    customer_id TEXT NOT NULL,          -- required at the Orbit API boundary
    amount_minor BIGINT NOT NULL,
    currency TEXT NOT NULL,
    status TEXT NOT NULL,               -- OrderStatus
    psp_name TEXT NOT NULL,
    psp_merchant_id TEXT NOT NULL,      -- PSP-side merchant identifier; resolved
                                         -- from the PSP's ConnectorConfig at
                                         -- request time. Stored so historical
                                         -- audits don't depend on current config.
    psp_order_id TEXT,                  -- NULL while in-flight
    payment_link TEXT,                  -- NULL while in-flight
    return_url TEXT NOT NULL,
    allowed_methods JSONB,
    expires_at TIMESTAMPTZ NOT NULL,
    terminally_failed BOOLEAN NOT NULL DEFAULT FALSE,
    failure_reason TEXT,
    recovery_attempts INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE UNIQUE INDEX orders_psp_order_id_idx ON orders(psp_order_id) WHERE psp_order_id IS NOT NULL;
CREATE INDEX orders_in_flight_idx ON orders(created_at) WHERE psp_order_id IS NULL;

CREATE TABLE payment_attempts (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id),
    psp_payment_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,               -- PaymentAttemptStatus
    method_used TEXT,
    amount_minor BIGINT,
    failure_code TEXT,                  -- PaymentFailureCode
    failure_reason TEXT,
    attempted_at TIMESTAMPTZ NOT NULL,  -- PSP-reported
    received_at TIMESTAMPTZ NOT NULL,   -- when Orbit first saw this
    raw_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX payment_attempts_order_idx ON payment_attempts(order_id);

CREATE TABLE refunds (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id),
    payment_attempt_id UUID NOT NULL REFERENCES payment_attempts(id),
    psp_refund_id TEXT UNIQUE,          -- NULL only briefly while in-flight
    amount_minor BIGINT NOT NULL,
    status TEXT NOT NULL,               -- RefundStatus
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE idempotency_keys (
    api_key_id UUID NOT NULL,
    key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    response_json JSONB,                -- NULL while in-flight
    status_code INT,                    -- NULL while in-flight
    order_id UUID,                      -- if this key created an order
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (api_key_id, key)
);

CREATE TABLE order_events (
    id BIGSERIAL PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id),
    from_status TEXT,
    to_status TEXT NOT NULL,
    source TEXT NOT NULL,               -- api | webhook | sync | janitor | admin
    detail TEXT,
    at TIMESTAMPTZ NOT NULL
);

CREATE TABLE webhook_events (
    psp_name TEXT NOT NULL,
    psp_event_id TEXT NOT NULL,
    order_id UUID REFERENCES orders(id),
    payment_attempt_id UUID REFERENCES payment_attempts(id),
    refund_id UUID REFERENCES refunds(id),
    event_type TEXT NOT NULL,
    raw_payload JSONB,
    received_at TIMESTAMPTZ NOT NULL,
    processed_at TIMESTAMPTZ,
    PRIMARY KEY (psp_name, psp_event_id)
);

CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    consumer_app TEXT NOT NULL,
    hashed_secret TEXT NOT NULL,        -- argon2id
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);
```

All amounts are minor units (integer). No floats anywhere.

---

## §4. Dependencies

- Lens (constitution Layer 2; in-process Python import).
- Python ≥ 3.11.
- `fastapi`, `uvicorn`.
- `pydantic-settings` (config).
- `sqlalchemy[asyncio] >= 2.0` + `asyncpg`.
- `alembic` (migrations).
- `argon2-cffi` (API key hashing).
- `structlog`.
- Postgres ≥ 15.

---

## §5. Non-functional requirements

Inherits constitution §6. Additions:

- API p99 < 500ms (excluding any PSP-side latency surfaced through `payment_link`).
- Webhook endpoint p99 < 200ms (heavy work goes to the async worker).
- Idempotency-key TTL configurable; default 24h.
- DB connection pool: configurable; default 20.
- Migrations: auto-run at startup in dev; production requires explicit `alembic upgrade head` step.
- API key rotation: zero-downtime; old + new keys both valid during the rotation window.
- All money fields integer minor units.
- Janitor cadence: configurable; default 60s.
- Janitor max recovery attempts per Order: configurable; default 3.

### §5.1 PII handling and `Maskable[T]`

Orbit-side PII fields, all of which MUST be typed `Maskable[T]` (from `lens.common`) on every Pydantic model that crosses an Orbit boundary (request DTOs, response DTOs, internal aggregates passed to logging):

- API key plaintext (bearer token presented in `Authorization` header) — `Maskable[str]`. Hashed at rest (argon2id); plaintext exists only in memory between auth-middleware extraction and the hash comparison.
- `customer_id` if it contains email or phone (any value with `@` or 10+ digits). Wrap in `Maskable[str]` at the API boundary.
- Any future customer-name, email, phone, address fields (out of scope for v1; pattern locked here).
- PSP-side identifiers that the PSP treats as confidential (PSP API keys, signing secrets, webhook secrets) — these are sourced via `ConnectorConfig` and never leave Lens, but Orbit's `api_keys` table treats its `hashed_secret` column as locked-down.

Forbidden in logs even when wrapped in `Maskable`:

- Anything resembling a full PAN (16 contiguous digits), CVV (3–4 digits with a card field), bank account number, IFSC + account combination, full UPI VPA.

`structlog` is configured with a processor that runs `Maskable.__str__` before serialization. Acceptance criterion §6 "No PII in any log line" is verified by a log-scrubbing test that feeds known PII through every endpoint and asserts no plaintext appears in captured log records.

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
    - PSP `create_order` times out → order stays with `psp_order_id=NULL`; idempotency record holds 503; janitor picks it up and either recovers or marks `FAILED` after 3 attempts.
- [ ] **Janitor test**: synthetic stuck order → janitor recovers it by re-calling PSP with the same idempotency key.
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

Maps to constitution §9 Step 6. Earliest start: when Step 2 publishes a usable `PaymentsFacade`. Non-integration work (steps 1–6 below) can begin immediately on a stub facade.

1. **Project skeleton** — FastAPI app, config, logging, DB engine, Alembic. ~1 day.
2. **DB schema + migrations** — All tables in §3.7. ~1 day.
3. **Domain state machines** — Order + PaymentAttempt + Refund; pure domain logic; fully unit-tested. ~2 days.
4. **API skeleton** — All routes in §2 return stub responses; OpenAPI schema generated. ~1 day.
5. **Idempotency middleware** — Wired in before any state-mutating route. ~1.5 days.
6. **Orbit-first creation flow** — `POST /v1/orders` with the two-transaction pattern from §3.4. ~1.5 days.
7. **Lens integration** — Wire `PaymentsFacade` into `/sync`, `/refund`, `/refunds/{id}/sync` endpoints. ~2 days.
8. **Webhook receiver + async worker** — Verify → dedup → enqueue → process. ~2.5 days.
9. **Janitor** — `LISTEN/NOTIFY` + advisory-lock + recovery loop. ~1 day.
10. **Bearer-token auth** — Single shared key per consumer app, hashed storage, rotation. ~1 day.
11. **End-to-end sandbox test** — Happy path + multi-attempt + sync-recovery + janitor-recovery from §6. ~1.5 days.
12. **Operational endpoints + observability** — `/healthz`, `/readyz`, metrics. ~1 day.
13. **Docs** — README, API reference, runbook. ~1 day.

Total: ~17 days single-agent. Parallelizable: 1–3 split nicely; 4–11 mostly serial.

---

## §8. Open questions for the implementing agent

- **Q1**: Postgres or another store? **Recommendation**: Postgres — schema is straightforward, async support mature, `LISTEN/NOTIFY` solves the worker queue for free.
- **Q2**: Async worker mechanism — `LISTEN/NOTIFY`, Celery, or in-process `asyncio` task queue? **Recommendation**: `LISTEN/NOTIFY` for v1.
- **Q3**: Should the janitor also poll PSPs for `CREATED` orders whose only attempts are stuck in `PENDING` (e.g., `FRAUD_REVIEW_PENDING`)? **Recommendation**: yes, as a separate janitor task (`/sync_payment` on the order after 1 hour of inactivity). Configurable; off by default until we see real data on PSP webhook reliability.
- **Q4**: When a duplicate `SUCCESS` event arrives for an order that already has a `SUCCESS` attempt: log + drop, or upsert and alert? **Recommendation**: log + drop, increment a metric; alert if rate exceeds a threshold. (Duplicates are usually webhook replays; legitimate.)
- **Q5**: API auth — bearer token alone, or also IP allow-list? **Recommendation**: token only inside Orbit; IP allow-list is a Cloudflare / ingress concern.
- **Q6**: Hashing — argon2 or bcrypt? **Recommendation**: argon2id.
- **Q7**: `POST /v1/orders` idempotency: same key returns same order. Confirmed (§3.4).
- **Q8**: Multi-currency is out of scope. Schema carries `currency` for forward-compat; v1 rejects any currency that mismatches the configured PSP currency for the consumer app.
- **Q9**: What's the canonical `customer_id` namespace — per consumer app? **Recommendation**: per consumer app (each API key has its own customer namespace).
- **Q10**: Should `GET /v1/orders/{id}` always include the `attempts` array, or is there a separate `/v1/orders/{id}/attempts` endpoint with pagination? **Recommendation**: nested in v1 (orders rarely have more than 3–4 attempts). Add the separate endpoint with pagination if a real workload demands it.
- **Q11**: Should the deterministic idempotency key for janitor's PSP retries be derived from the Orbit order id (`f"orbit-create-order-{order_id}"`) or stored separately? **Recommendation**: derive deterministically — one less column, one less recovery surface.
- **Q12** (constitution OQ-10): janitor cadence + max recovery attempts. **Recommendation**: 60s / 3 attempts; configurable. Tune from production data.
