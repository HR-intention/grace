# Multi-Lang Connector Generation — Plan E: Cashfree End-to-End Validation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Implement a working Cashfree connector in `lens` by exercising the full Plan A → Plan D pipeline. This is the integration test that proves the rulesbook + shell architecture composes. Mocked sandbox calls (httpx MockTransport); no live PSP traffic.

**Why Cashfree:** Strong Indian PSP, UPI-first (matches the project's Indian-ecosystem priority memory), public API docs at developers.cashfree.com, distinct enough from Razorpay to surface edge cases.

**Architecture:** Tech spec via `grace techspec cashfree --target-lang python` → connector implementation via Plan D's patterns → tests with mocked httpx responses → quality verification → lessons logged.

**Tech Stack:** Python + FastAPI + httpx (with MockTransport for tests) + pytest + mypy --strict + Plan D's rulesbook.

**Source spec:** [docs/superpowers/specs/2026-05-18-multi-lang-connector-generation-design.md](../specs/2026-05-18-multi-lang-connector-generation-design.md) — Section 10 Phase 6.

**Depends on:** Plans A, B, C, D — all landed.

**Scope decision:** Mocked sandbox per user's choice. Subagent uses WebFetch/Firecrawl for public Cashfree docs; integration tests use `httpx.MockTransport` with recorded response shapes. Live sandbox verification deferred to manual follow-up.

---

## Repos involved

- `grace/` — for tech spec generation + final feedback log
- `lens/` — for the Cashfree connector implementation + tests

Plan A-D conventions apply: each task ends with a commit; cross-repo commits are clearly labeled.

---

## Tasks

### Task 1: Fetch Cashfree docs + generate tech spec

**Repo:** `grace/`

**Goal:** Produce a `technical_specification.md` for Cashfree at `rulesbook/references/cashfree/technical_specification.md` (or wherever `TECHSPEC_OUTPUT_DIR` points).

- [ ] **Step 1: Fetch Cashfree public docs via WebFetch**

Use the WebFetch tool to retrieve Cashfree's public API documentation. Key URLs to scrape (no live API hits, just docs):

- https://docs.cashfree.com/docs/payment-gateway (overview)
- https://docs.cashfree.com/reference/pg-orders-overview (orders endpoint)
- https://docs.cashfree.com/reference/pg-payments-overview (payments endpoint)
- https://docs.cashfree.com/reference/pg-refunds-overview (refunds endpoint)
- https://docs.cashfree.com/reference/pg-webhooks (webhook events + signature)
- https://docs.cashfree.com/docs/pg-upi-collect (UPI Collect)
- https://docs.cashfree.com/docs/pg-upi-intent (UPI Intent)

Save the fetched markdown to `/tmp/cashfree-docs/` as individual `.md` files. This becomes the input folder for `grace techspec`.

If WebFetch is rate-limited or returns insufficient content, fall back to writing a stub tech spec based on the implementer's general knowledge of Cashfree's API shape (mention this as DONE_WITH_CONCERNS).

- [ ] **Step 2: Run `grace techspec`**

```bash
cd /Users/sarthak/PycharmProjects/symplora/grace
source .venv/bin/activate
grace techspec cashfree -f /tmp/cashfree-docs --target-lang python -v
```

The output goes to `${TECHSPEC_OUTPUT_DIR}/cashfree/technical_specification.md`. The default `TECHSPEC_OUTPUT_DIR` per `.env.example` is `./rulesbook/codegen-rust/references/` (which is gitignored).

If `grace techspec` fails (Groq API errors, network, etc.), the implementer should fall back to hand-writing a minimal tech spec at `/tmp/cashfree-docs/technical_specification.md` covering: base URL, auth header scheme, the 6 core flow endpoints, UPI Collect + Intent specifics, webhook signature scheme.

- [ ] **Step 3: Read the spec end-to-end**

Confirm the spec contains: base URL (`https://sandbox.cashfree.com/pg/`), auth (`x-api-key` + `x-client-id` headers, `x-client-secret` body or header), per-flow endpoints, request/response shapes, status enumerations, idempotency convention, UPI flow specifics, webhook signature header (`x-webhook-signature`) + verification scheme.

- [ ] **Step 4: No commit yet** — the spec lands in `rulesbook/references/` which is gitignored. Note the spec path for Task 2.

---

### Task 2: Implement Cashfree connector

**Repo:** `lens/`

Read Plan D's `.gracerules` and the 10 pattern files. Apply them for Cashfree.

- [ ] **Step 1: Scaffold the package**

Create:
- `lens/connectors/cashfree/__init__.py` — `from .connector import Cashfree; register_connector("cashfree", Cashfree)`
- `lens/connectors/cashfree/auth.py` — `CashfreeAuth(BaseAuth)` with `api_key`, `client_id`, `webhook_secret` (Cashfree uses split api key + client id)
- `lens/connectors/cashfree/connector.py` — main `Cashfree(BaseConnector)` class
- `lens/connectors/cashfree/transformers.py` — Cashfree-specific Pydantic models + transformer functions

Update `lens/connectors/__init__.py` to add `from . import cashfree` (the explicit-discovery convention per Plan C).

- [ ] **Step 2: Implement Authorize flow (Card + UPI)**

Per `pattern_authorize.md`, `authorize/card/pattern_authorize_card.md`, `authorize/upi/pattern_authorize_upi.md`.

Cashfree's Authorize is two-step in real life (create order → fetch payment link), but for this implementation flatten to a single `authorize()` that does both. Use the Cashfree `/pg/orders` endpoint to create the order, capture the `payment_session_id`, and synthesize the `AuthorizeResponse` accordingly.

For UPI Collect: pass `payment_method.upi.channel="collect"` + `payment_method.upi.upi_id=<vpa>`. For UPI Intent: pass `payment_method.upi.channel="link"` and surface the returned `data.payload.default` URL as `RedirectionData(method="INTENT", url=...)`.

Status mapping: `ACTIVE` → PENDING, `PAID` → CHARGED, `EXPIRED`/`TERMINATED` → FAILURE. Add every status the spec lists.

- [ ] **Step 3: Implement remaining flows**

- **PSync** (`/pg/orders/{order_id}/payments` or `/pg/orders/{order_id}`): GET. Map order status to AttemptStatus.
- **Capture**: Cashfree auto-captures by default; the explicit capture endpoint is rarely used. Either implement against `/pg/orders/{order_id}/capture` (if documented) or stub with a clear `raise NotImplementedError` + a comment in the validation checklist. Document the decision.
- **Refund** (`/pg/orders/{order_id}/refunds`): POST with `refund_amount`, `refund_id`, `refund_note`. Use `data.idempotency_key` as the `refund_id` if not provided. Status maps to RefundStatus.
- **RSync** (`/pg/orders/{order_id}/refunds/{refund_id}`): GET.
- **Void**: Cashfree doesn't have a separate void; it's just a refund of a non-captured payment. Either delegate to refund or raise `NotImplementedError` with a clear message. Document.

- [ ] **Step 4: Implement IncomingWebhook**

Cashfree signs webhooks with HMAC-SHA256 of `<timestamp>.<rawPayload>` using the webhook secret. Header name: `x-webhook-signature` (base64-encoded). Header `x-webhook-timestamp` carries the timestamp.

Per `pattern_IncomingWebhook_flow.md`, verify the signature with `hmac.compare_digest`, parse the payload, extract `data.payment.cf_payment_id` or `data.order.order_id` as the event_id (whichever is documented in the tech spec), return a `WebhookEvent`. Router-layer dedup (per Plan C hotfix) handles duplicate detection.

- [ ] **Step 5: mypy clean**

```bash
cd /Users/sarthak/PycharmProjects/symplora/lens
source .venv/bin/activate
uv run mypy lens/connectors/cashfree/
```
Expected: `Success: no issues found`. Fix any reported types.

- [ ] **Step 6: Commit**

```bash
cd /Users/sarthak/PycharmProjects/symplora/lens
git add lens/connectors/cashfree/ lens/connectors/__init__.py
git commit -m "feat(cashfree): implement connector — 6 flows + Card/UPI + webhook

Applied Plan D patterns. Authorize via /pg/orders. UPI Collect uses
upi.channel=collect + upi_id=<vpa>; UPI Intent uses upi.channel=link
and surfaces payment_session_id as redirection deep-link. Webhook
verifies HMAC-SHA256 over <timestamp>.<rawPayload> per Cashfree spec.

Capture/Void stubbed with NotImplementedError (Cashfree auto-captures;
void is a refund of pre-capture payment). Documented in validation
checklist."
```

---

### Task 3: Integration tests with httpx.MockTransport

**Repo:** `lens/`

- [ ] **Step 1: Create `tests/integration/test_cashfree.py`**

Use `httpx.MockTransport` to inject canned Cashfree responses. The test:
1. Patches the connector's `self.client` with a MockTransport configured to return recorded JSON.
2. Calls the FastAPI route via the existing `client` fixture from `conftest.py`.
3. Asserts response shape (status code, body, headers).

Tests to author:
- `test_authorize_card` — mock POST /pg/orders → returns `{"cf_order_id": "order_test_123", "order_status": "ACTIVE", "payment_session_id": "session_xyz"}`. Assert HTTP 200 + body.response.connector_payment_id is set.
- `test_authorize_upi_collect` — mock POST /pg/orders for UPI Collect. Assert status PENDING.
- `test_authorize_upi_intent` — mock POST /pg/orders for UPI Intent. Assert response has redirection_data with method="INTENT".
- `test_psync` — mock GET /pg/orders/{order_id} → returns `{"order_status": "PAID", ...}`. Assert mapped to CHARGED.
- `test_refund` — mock POST /pg/orders/{order_id}/refunds.
- `test_rsync` — mock GET /pg/orders/{order_id}/refunds/{refund_id}.
- `test_incoming_webhook_valid_signature` — POST /v1/webhooks/cashfree with correctly signed payload; assert 200 + duplicate=False.
- `test_incoming_webhook_invalid_signature` — assert 400.
- `test_incoming_webhook_duplicate` — POST same signed payload twice; assert second call returns duplicate=True (Plan C hotfix's router-layer dedup wires this).

Each test should:
- Inject CashfreeAuth into `client.app.state.connectors["cashfree"]`
- Reset the dedup_store before the duplicate test
- Use `@pytest.mark.integration` so they can be skipped in CI if needed (or run by default — caller's choice)

- [ ] **Step 2: Run the tests**

```bash
cd /Users/sarthak/PycharmProjects/symplora/lens
source .venv/bin/activate
pytest tests/integration/test_cashfree.py -v
```

Expected: all ~9 tests pass.

- [ ] **Step 3: mypy clean (whole package now that there's a real connector)**

```bash
uv run mypy lens/
```
Expected: `Success: no issues found`. Fix any new issues.

- [ ] **Step 4: Commit**

```bash
cd /Users/sarthak/PycharmProjects/symplora/lens
git add tests/integration/test_cashfree.py
git commit -m "test(cashfree): add integration tests with httpx.MockTransport

9 tests covering Authorize (Card + UPI Collect + UPI Intent), PSync,
Refund, RSync, and IncomingWebhook (valid sig + invalid sig + duplicate
detection via Plan C's router-layer dedup).

All mocked — no live Cashfree sandbox calls."
```

---

### Task 4: Quality review + acceptance gate

**Read-only verification.**

- [ ] **Step 1: Walk through `python_quality_checks.md`**

Open `grace/rulesbook/codegen-python/guides/quality/python_quality_checks.md`. For each Critical / Warning / Suggestion check, evaluate the Cashfree connector against it. Tally:
- Critical violations
- Warning violations
- Suggestion violations

Apply the shared rubric:
```
Quality Score = 100 - (Critical × 20) - (Warnings × 5) - (Suggestions × 1)
```

Score must be ≥ 60.

- [ ] **Step 2: Cross-cutting checks (shared/quality_rubric.md)**

Verify each cross-cutting check (idempotency keys, status mapping coverage, no hardcoded secrets, webhook signature + dedup, currency/amount safety, PCI/PII masking).

- [ ] **Step 3: Final test + mypy run**

```bash
cd /Users/sarthak/PycharmProjects/symplora/lens
source .venv/bin/activate
uv run mypy lens/
pytest tests/ -v
```

Both must be clean. Tests count: 19 (Plan C baseline) + ~9 Cashfree = ~28 total.

- [ ] **Step 4: No commit** (verification only)

---

### Task 5: Log lessons to shared/feedback.md

**Repo:** `grace/`

- [ ] **Step 1: Append a new entry to `rulesbook/shared/feedback.md`**

After the last existing entry, append a new section. Tag: `[lang:python]`.

```markdown
## [lang:python] Cashfree integration — Plan E (2026-05-19)

**Outcome:** SUCCESS. Score: <score from Task 4 Step 1>.

**Highlights:**
- Cashfree's order/payment two-step is flattenable to a single `authorize()` call by capturing `payment_session_id` from the order-create response.
- UPI Collect uses `upi.channel="collect"` + `upi.upi_id=<vpa>`. UPI Intent uses `upi.channel="link"` and returns a deep-link URL in `data.payload.default`.
- Webhook signature scheme is HMAC-SHA256 over `<timestamp>.<rawPayload>`, headers `x-webhook-signature` (base64) + `x-webhook-timestamp`. Pattern's signature verification (`hmac.compare_digest`) applied cleanly.
- Cashfree's `cf_payment_id` is the natural event_id for webhook dedup; some events use `order_id` instead. The connector checks both.

**Lessons:**
- Cashfree auto-captures by default — explicit Capture flow is rarely needed. Connector stubs with `NotImplementedError` and documents the workaround (do not call Capture).
- Void doesn't exist as a separate endpoint — pre-capture cancellation is just an early refund. Same `NotImplementedError` + documentation approach.
- The 9-test integration suite with httpx.MockTransport covers the happy paths without live sandbox keys. Live sandbox verification is a manual follow-up.

**Patterns that worked well:**
- `from_authorize_response(resp, mapped_status)` taking mapped status as a parameter (Plan D hotfix) cleanly separated transformer from status-mapping.
- Router-layer webhook dedup (Plan C hotfix) means the connector body just signs/parses/normalizes — no app.state plumbing needed in the connector itself.

**Open follow-ups:**
- Live sandbox verification against developer.cashfree.com test creds.
- Wave 2: SetupMandate (Cashfree subscription/eMandate flow).
```

Fill in the actual quality score from Task 4 Step 1.

- [ ] **Step 2: Commit (in grace)**

```bash
cd /Users/sarthak/PycharmProjects/symplora/grace
git add rulesbook/shared/feedback.md
git commit -m "docs(feedback): log Cashfree Plan E lessons (Python pack first prod use)

First Wave 1 connector implemented end-to-end via the Python pattern
pack. Score: <X>/100. Highlights the Cashfree auto-capture quirk,
UPI Collect/Intent channel semantics, and webhook signature scheme.
Live sandbox verification deferred to manual follow-up."
```

---

## Plan E acceptance summary

Plan E is complete when:
- A tech spec exists for Cashfree (in `references/cashfree/` — gitignored, not committed)
- Cashfree connector implementation lands in `lens/` with 6 flows + Card/UPI/webhook (Task 2 commit)
- 9 mocked integration tests pass (Task 3 commit)
- `mypy --strict` clean on the whole `lens/` package
- Quality score ≥ 60
- Lessons logged to `grace/rulesbook/shared/feedback.md` (Task 5 commit)

3 commits total expected:
- `lens`: Cashfree connector
- `lens`: Cashfree integration tests
- `grace`: Cashfree lessons in feedback.md

After Plan E:
- The full Plans A→B→C→D→E pipeline is end-to-end validated.
- Live sandbox verification with real Cashfree creds is the only remaining gate (manual).
