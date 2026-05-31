---
name: add-connector
description: >
  Adds a new PSP (payment service provider) connector to Lens using the
  domain-modular lens-0.2.0 shape. Orchestrates `grace fetch-docs --domain`,
  `grace generate --domain`, the diff review, and the `docs-generated/`
  refresh. Use when Lens needs to gain support for a new hosted-checkout PSP
  (Razorpay, Stripe, etc.) or when extending an existing connector to cover
  a new capability domain (orders / subscriptions) — not for tweaking an
  already-generated connector.
license: MIT
compatibility: Requires Python ≥ 3.11, `uv`, and Grace installed as an editable dev dep (`uv pip install -e ../grace` or via `[tool.uv.sources]`). Targets lens ≥ 0.2.0.
metadata:
  author: Symplora Engineering
  version: "2.0"
  domain: payment-connectors
---

# Add Connector

## Overview

Adds one new PSP connector to the Lens runtime library using the
**domain-modular** shape introduced in lens 0.2.0. The output is a Python
package at `lens/connectors/<psp>/` that implements Lens's capability
interfaces (`PaymentsConnector`, `MandateConnector`) via per-domain mixins
composed into a single registered `<Psp>Connector`, plus a refreshed
`docs-generated/llms.txt`.

**Inputs:**
- PSP name (lowercase, e.g. `cashfree`)
- URL of the PSP's `llms.txt` (or local path to one)
- Domain scope: `orders`, `subscriptions`, or `all` (default `all`)

**Output (domain-modular layout):**

```
lens/connectors/<psp>/
  __init__.py            # requires_lens = "^0.2"; register + register_webhook
  connector.py           # class <Psp>Connector(<Psp>Orders, <Psp>Subscriptions)
  webhooks.py            # build_webhook_handlers(config) -> WebhookHandlers
  core/
    base.py              # _<Psp>Base(Connector): name, base_url, close, __init__, _client
    auth.py              # build_auth_headers + verify_signature (HMAC, family-agnostic)
    status.py            # failure free-text -> (PaymentFailureCode, FailureClass)
    models.py            # shared wire models (webhook envelope, error body)
  orders/                # domain: PaymentsConnector
    connector.py         # class <Psp>Orders(_<Psp>Base, PaymentsConnector)
    models.py            # payment wire models
    status_map.py        # PSP payment status -> (PaymentAttemptStatus, PaymentFailureCode)
    webhooks.py          # _parse_payment_webhook(bytes) -> PaymentWebhookEvent
  subscriptions/         # domain: MandateConnector
    connector.py         # class <Psp>Subscriptions(_<Psp>Base, MandateConnector)
    models.py            # subscription / plan / mandate wire models
    status_map.py        # subscription_status -> MandateStatus; event -> WebhookEventType
    webhooks.py          # _parse_mandate_webhook(bytes) -> MandateWebhookEvent
```

- `connector_docs/<psp>/{_shared,orders,subscriptions}/` — pinned, domain-grouped doc snapshots
- `connector_docs/<psp>.md` — per-PSP spec carrying normalization decisions
- `docs-generated/llms.txt` — refreshed to include the new connector
- `docs-generated/connectors/<psp>.md` — per-connector reference page

## Flow phases

Run these in order. **Phase 4 is a hard checkpoint** — if the quality gates
fail there, fix the rulebook (in Grace, never in the generated code) and
restart from Phase 3.

### Phase 1 — Prerequisites

Verify before starting:

```bash
# Grace CLI reachable in this venv
uv run grace --version
# claude -p reachable + authenticated for headless mode
uv run grace doctor
# Lens is importable here (gates need this)
uv run python -c "import lens; print(lens.__file__)"
```

If `grace doctor` reports `CLAUDE_CODE_NOT_AUTHENTICATED`, run
`claude setup-token` and export `CLAUDE_CODE_OAUTH_TOKEN` (Grace README →
Troubleshooting).

### Phase 2 — Snapshot the PSP's docs

Find the PSP's `llms.txt` (usually at `<docs-site-root>/llms.txt`). Then:

```bash
# Snapshot docs for all domains (creates connector_docs/<psp>/{_shared,orders,subscriptions}/)
# and scaffolds connector_docs/<psp>.md for developer review.
uv run grace fetch-docs <psp> --from <llms.txt-url> --domain all
```

`--domain` controls which capability pages to include. Use `--domain orders`
when adding only payment support, `--domain subscriptions` only for mandates,
or `--domain all` (default) for the full connector.

Review the file list — if too few pages survived the default filter, pass
`--include "*<pattern>*"` globs (see `references/grace-cli-cheatsheet.md`).

**Edit `connector_docs/<psp>.md`** to fill in the normalization decisions
(status mapping, failure-code mapping, per-domain notes). This spec is read
by `grace generate` and is the authoritative source for PSP-specific mapping
decisions.

**Commit the snapshot** so the regen is reproducible:

```bash
git add connector_docs/<psp>/ connector_docs/<psp>.md
git commit -m "docs(<psp>): snapshot v1 doc pages for grace"
```

### Phase 3 — Generate

```bash
# Generate the full domain-modular connector (both orders + subscriptions domains):
uv run grace generate <psp> --domain all

# Or target a single domain (e.g. add subscriptions to an existing payments connector):
uv run grace generate <psp> --domain subscriptions
```

`--domain all` regenerates all files. `--domain subscriptions` rewrites only
`connectors/<psp>/subscriptions/*` plus the Grace-owned compose surface
(`connector.py`, `webhooks.py`, `__init__.py`), leaving `core/` and `orders/`
untouched.

Output streams live. Default destination: `lens/connectors/<psp>/`.

After generation, Grace runs the quality gates (`mypy --strict`,
`pytest --cov`, the 6-dimension rubric) and writes
`lens/connectors/<psp>/quality_report.json`.

### Phase 4 — Quality gate (hard checkpoint)

Read `lens/connectors/<psp>/quality_report.json`. The run passes iff
`"passed": true` and `"total" >= 60`. If it doesn't:

- Identify the lowest-scoring dimension from the JSON.
- Open `references/rubric-checklist.md` and trace which rulebook page
  governs that dimension.
- Sharpen the rulebook page (in Grace's repo) — **never hand-edit the
  generated code**.
- Re-run from Phase 3 with `uv run grace regenerate <psp>`.

Common iteration notes:
- Cashfree payment terms (`USER_DROPPED`, `FLAGGED`, `CANCELLED`) need
  explicit mapping in `orders/status_map.py`.
- Mandate status terms (`ACTIVE`, `PAUSED`, `SUSPENDED`, `REVOKED`) need
  mapping in `subscriptions/status_map.py`.
- Webhook errors must come from the `WebhookRouter` (via `build_webhook_handlers`),
  not from a connector method. If rubric flags `error_handling`, ensure
  `webhooks.py` uses the shared router shape.

### Phase 5 — Review the diff

```bash
git diff lens/connectors/<psp>/
```

Read the generated package end-to-end. The locked surface is small (see
`references/flow-patterns/`) — spotting deviations is fast.

Confirm all of the following:

**compose surface (Grace-owned)**
- [ ] `connector.py` (root): `class <Psp>Connector(<Psp>Orders, <Psp>Subscriptions):` — no methods, pure composition; or just `(<Psp>Orders, _<Psp>Base)` for payments-only.
- [ ] `webhooks.py` (root): exports `build_webhook_handlers(config: ConnectorConfig) -> WebhookHandlers`; no `handle_webhook` method anywhere.
- [ ] `__init__.py`: declares `requires_lens = "^0.2"` at module scope AND calls **both** `ConnectorFactory.register("<psp>", <Psp>Connector)` AND `ConnectorFactory.register_webhook("<psp>", build_webhook_handlers)`.

**core/**
- [ ] `core/base.py`: `class _<Psp>Base(Connector)` — owns `name`, `base_url`, `close()`, `__init__(config)`, and the ONE `httpx.AsyncClient`.
- [ ] `core/auth.py`: `verify_signature` uses `hmac.compare_digest`; credentials typed `Maskable[str]`.

**orders/ (PaymentsConnector domain)**
- [ ] `orders/connector.py`: `class <Psp>Orders(_<Psp>Base, PaymentsConnector)` — implements `create_order`, `sync_payment`, `refund`, `sync_refund` (all `async def`) plus `supported_methods` and `supports_idempotency_key` (both `@property`).
- [ ] `orders/status_map.py`: every documented PSP payment-status term mapped to `(PaymentAttemptStatus, PaymentFailureCode | None)`; unknown falls back to `(FAILED, UNKNOWN)` with a `structlog.warning`.

**subscriptions/ (MandateConnector domain)**
- [ ] `subscriptions/connector.py`: `class <Psp>Subscriptions(_<Psp>Base, MandateConnector)` — implements five `async def` lifecycle methods (`create_subscription`, `sync_subscription`, `cancel_subscription`, `pause_subscription`, `resume_subscription`) and four **plain** `def` introspection methods (`supported_mandate_rails`, `supports_pause`, `supported_intervals`, `max_mandate_amount`).
- [ ] `subscriptions/status_map.py`: subscription status mapped to `MandateStatus`; webhook event-type strings mapped to `WebhookEventType`.

**modern typing (required throughout)**
- [ ] All type annotations use Python 3.11 built-ins: `dict[str, str]`, `list[X]`, `set[X]`, `X | None` — **never** `Dict`/`List`/`Optional`/`Set` from `typing`.
- [ ] `StrEnum` used for enums where applicable.

### Phase 6 — Land

```bash
git add lens/connectors/<psp>/ connector_docs/ docs-generated/
git commit -m "feat(connectors): add <Psp> via grace (domain-modular)"
```

`docs-generated/llms.txt` and `docs-generated/connectors/<psp>.md` are
refreshed automatically by `grace generate`; commit them alongside the
package so downstream consumers see the new connector advertised.

## Don't

- **Don't hand-edit generated files.** Every file in `lens/connectors/<psp>/`
  carries the constitution §4 marker; modifications are forbidden. If the
  output is wrong, fix the Grace rulebook and regenerate.
- **Don't add a `handle_webhook` method.** Webhooks are dispatched by the
  shared `WebhookRouter` via `build_webhook_handlers`. The `PaymentsConnector`
  and `MandateConnector` ABCs do not declare `handle_webhook`. A connector-method
  webhook is a lens-0.1 pattern; it must not appear in 0.2.0 connectors.
- **Don't subclass bare `Connector`.** The domain-mixin classes subclass
  `(_<Psp>Base, PaymentsConnector)` or `(_<Psp>Base, MandateConnector)`. Only
  `_<Psp>Base` subclasses `Connector` directly. `ConnectorFactory.register`
  rejects a class that is not a `PaymentsConnector` or `MandateConnector` at
  import time.
- **Don't invent enum values.** `PaymentAttemptStatus` is `PENDING | SUCCESS | FAILED`.
  `PaymentFailureCode` has eleven locked values. `MandateStatus` values are
  `ACTIVE | PAUSED | SUSPENDED | REVOKED | FAILED | PENDING | EXPIRED`. PSP-specific
  terms map INTO these via `status_map.py`. Never widen an enum locally.
- **Don't use deprecated typing aliases.** `Dict`, `List`, `Optional`, `Set` from
  `typing` are banned in 0.2.0 generated code. Modern Python 3.11 built-ins only.

## References

- `references/grace-cli-cheatsheet.md` — every `grace` command + the
  options that actually matter (including `--domain`).
- `references/rubric-checklist.md` — what each of the six rubric dimensions
  measures + the rulebook page that fixes it.
- `references/flow-patterns/` — per-flow implementation patterns
  (Python skeleton, errors to surface, required tests). The webhook pattern
  (`handle_webhook.md`) now describes the shared `build_webhook_handlers`/
  `WebhookRouter` approach.
