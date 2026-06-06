# Python Connector Rulebook

This rulebook tells Claude Code how to generate a Python PSP connector for the **Orbit Lens**
library (lens 0.2.0). Connectors are **domain-modular**: per-capability mixins over a shared
`core/` base, composed into one registered class.

---

## What you are generating

For each target PSP, you produce one Python package under `lens/connectors/<psp>/` that:

- Implements lens's capability interfaces — `PaymentsConnector` and/or `MandateConnector` —
  via domain mixin classes (`<Psp>Orders`, `<Psp>Subscriptions`) over a shared `_<Psp>Base`.
- Composes the domain mixins into a single registered `<Psp>Connector` (root `connector.py`).
- Provides a `build_webhook_handlers` function (root `webhooks.py`) that assembles the
  shared `WebhookHandlers`/`WebhookRouter` for inbound PSP events.
- Uses only the locked domain types from `lens.domain_types` and `lens.enums` (never
  redefines them).
- Lays files out exactly as `file_layout.md` requires.
- Starts every emitted `.py` file with the constitution §4 marker.
- Registers both the connector class and the webhook handlers builder via
  `ConnectorFactory.register` + `ConnectorFactory.register_webhook` in `__init__.py`.

**Never implement bare `Connector` directly.** `ConnectorFactory.register` rejects it.

---

## Reading order

Read these files in order before producing code:

1. `ground_rules.md` — non-negotiable invariants.
2. `connector_abc.md` — the capability-interface split; `_<Psp>Base`; `<Psp>Orders`;
   `<Psp>Subscriptions`; the Grace-owned compose surface.
3. `domain_types.md` — all request/response models + enums (payments + mandates),
   including `FAILURE_CLASS` published-data rule.
4. `file_layout.md` — the exact files to emit (`core/`, per-domain, compose surface).
5. `status_mapping.md` — three mapping surfaces (payment status, subscription status,
   failure free-text); the periodic-mode finality rule; `FAILURE_CLASS` discipline.
6. `webhook_handling.md` — `WebhookHandlers`/`WebhookRouter` shared-router pattern;
   `build_webhook_handlers`; `_classify`; domain parsers.
7. `testing.md` — `httpx.MockTransport` discipline; per-domain required cases;
   cross-domain webhook-router test; tamper-test pattern.
8. `pitfalls.md` — modern typing; one client; singular `MandateConnector`;
   both registrations; no marker hand-edits.
9. `marker.md` — the §4 file marker (mandatory on every emitted `.py`).

Then read the per-flow patterns under `../guides/patterns/`:
`pattern_createorder.md`, `pattern_psync.md`, `pattern_refund.md`,
`pattern_rsync.md`, `pattern_create_subscription.md`, `pattern_sync_subscription.md`,
`pattern_manage_mandate.md`, `pattern_IncomingWebhook_flow.md`.

---

## Non-negotiables

- **Capability interfaces only.** Generate `<Psp>Orders(_<Psp>Base, PaymentsConnector)` and/or
  `<Psp>Subscriptions(_<Psp>Base, MandateConnector)`, composed into `<Psp>Connector`. Never
  a bare `Connector` subclass.
- **Both registrations in `__init__.py`.** `ConnectorFactory.register(...)` and
  `ConnectorFactory.register_webhook(...)`.
- **No `requires_lens`** — the connector version gate was removed in constitution v0.6.
- **Webhook is the shared router** (`build_webhook_handlers` + `WebhookRouter`), not a
  connector method.
- **`MandateConnector` is singular.** `MandatesConnector` does not exist.
- **Modern typing throughout.** No `Dict`/`List`/`Optional`/`Set` from `typing`.
- **One `httpx.AsyncClient`**, built (via `lens.http.build_http_client`) and owned by `_<Psp>Base`.
- `mypy --strict` clean. `pytest --cov` ≥ 80%.
- Every `.py` file starts with the §4 marker.
- No PSP-specific logic in the generic rulebook — use `<Psp>` placeholders. Per-PSP
  normalization decisions live in `connector_docs/<psp>.md`.

If the PSP docs cover a flow you don't have a pattern for, stop and surface the gap.
Don't invent one.
