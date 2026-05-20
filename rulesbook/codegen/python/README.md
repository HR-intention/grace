# Python Connector Rulebook

This rulebook tells Claude Code how to generate a Python PSP connector for the **Orbit Lens** library.

## What you are generating

For each target PSP, you produce one Python package under `lens/connectors/<psp>/` that:

- Implements Lens's locked `Connector` ABC (see `connector_abc.md`).
- Uses only the locked domain types from `lens.domain_types` and `lens.enums` (see `domain_types.md`).
- Lays files out exactly as `file_layout.md` requires.
- Starts every emitted `.py` file with the constitution §4 marker (see `marker.md`).

The class is one class per PSP (e.g., `class Cashfree(Connector)`), with four async flow methods plus `handle_webhook` and `close`. No per-flow subclasses; no abstraction layers; no per-method request builders. Hosted-checkout only — never accept raw card/UPI/wallet data at the boundary.

## Reading order

Read these files in order before producing code:

1. `ground_rules.md` — non-negotiable invariants (Lens §3).
2. `connector_abc.md` — the locked Connector surface (Lens §4.2).
3. `domain_types.md` — request/response models + enums (Lens §4.4 + §4.6).
4. `file_layout.md` — the exact files to emit (Grace §3.2).
5. `status_mapping.md` — how to translate PSP-specific status terms.
6. `webhook_handling.md` — verify-signature-then-parse pattern.
7. `testing.md` — `httpx.MockTransport` discipline + required test cases.
8. `marker.md` — the §4 file marker (mandatory on every emitted .py).

Then read the per-flow patterns under `../guides/patterns/`:
`pattern_createorder.md`, `pattern_psync.md`, `pattern_refund.md`,
`pattern_rsync.md`, `pattern_IncomingWebhook_flow.md`.

## Non-negotiables

- Generate only the four v1 flows (`create_order`, `sync_payment`, `refund`, `sync_refund`) + `handle_webhook` + `close`. Do **not** emit `authorize`, `capture`, `void`, `setup_mandate`, `repeat_payment`, `payment_method_token`, `session_token`, 3DS-specific, payouts, or disputes. Those are deliberately out of v1 scope (Orbit Constitution §7).
- `mypy --strict` clean. No `Any`. No `# type: ignore` without a scoped, commented reason.
- `pytest --cov` ≥ 80% line coverage on the emitted package.
- Every `.py` file starts with the marker.
- `__init__.py` self-registers via `ConnectorFactory.register("<psp>", <Psp>)`.
- `status_map.py` exists and maps every PSP-specific status term in the docs.
- PII passes through `Maskable[T]`; never log raw credentials or secrets.

If the PSP docs cover a flow you don't have a pattern for, stop and surface the gap. Don't invent one.
