# v1 flow patterns

This directory holds the per-flow pattern files Grace ships to Claude Code as context. The entry point for the full Python rulebook is `../../python/README.md` — read it first.

## Patterns kept for v1

The four PSP flows + the webhook:

- **`pattern_createorder.md`** — `create_order` (hosted-checkout session creation).
- **`pattern_psync.md`** — `sync_payment` (poll for OrderStatus + list of PaymentAttempts).
- **`pattern_refund.md`** — `refund` (initiate full or partial refund).
- **`pattern_rsync.md`** — `sync_refund` (poll for refund status).
- **`pattern_IncomingWebhook_flow.md`** — `handle_webhook` (verify + parse).

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
