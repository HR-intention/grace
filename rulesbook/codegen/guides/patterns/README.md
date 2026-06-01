# Flow patterns

This directory holds the per-flow pattern files Grace ships to Claude Code as context. The entry point for the full Python rulebook is `../../python/README.md` — read it first.

## Payment domain patterns (`orders/`)

- **`pattern_createorder.md`** — `create_order` (hosted-checkout session creation).
- **`pattern_psync.md`** — `sync_payment` (poll for OrderStatus + list of PaymentAttempts).
- **`pattern_refund.md`** — `refund` (initiate full or partial refund).
- **`pattern_rsync.md`** — `sync_refund` (poll for refund status).

## Mandate / subscription domain patterns (`subscriptions/`)

- **`pattern_create_subscription.md`** — `create_subscription` (inline mandate creation + customer approval handle).
- **`pattern_sync_subscription.md`** — `sync_subscription` (poll for MandateStatus + last debit outcome).
- **`pattern_manage_mandate.md`** — `cancel_subscription` / `pause_subscription` / `resume_subscription` (all share `ManageMandateRequest`; resume = PSP ACTIVATE).
- **`pattern_mandate_webhook.md`** — `_parse_mandate_webhook` (domain parser for mandate events; router-dispatched).

## Shared webhook router pattern

- **`pattern_IncomingWebhook_flow.md`** — `build_webhook_handlers` (shared `WebhookRouter` integration: verify once via HMAC, classify by `WebhookFamily`, dispatch to domain parsers; **no `handle_webhook` connector method**).

Each pattern documents: the domain types involved, the method signature, an implementation skeleton, the errors to surface, and the required test cases.

## Out of scope for v1

Removed in Step 2 of the python-support roadmap (per constitution §7 + `FUTURE_S2S_INTERFACE.md`):

- `authorize`, `capture`, `void`, `void_pc` (server-to-server direct-API flows).
- `setup_mandate`, `mandate_revoke`, `repeat_payment` (recurring / mandates).
- `payment_method_token`, `session_token` (instrument vaulting).
- `IncrementalAuthorization`, `CreateAccessToken`.
- `dsync` (dispute sync), `accept_dispute`, `defend_dispute`, `submit_evidence`.
- `flow_macro_guide`, `macro_patterns_reference` (Rust macro infrastructure).

These will return as a follow-up product slice when direct-API support enters scope. Until then, the patterns and rulebook do not describe them — and Claude Code is not asked to generate them.
