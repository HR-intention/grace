# Changelog

Notable changes to the Grace codegen tool. Grace follows SemVer; per Orbit Constitution §8,
a rulebook/template change that alters generated-code shape is a **major** bump (expressed
pre-1.0 as a `0.x` increment). The §4 generated-file marker records the Grace version used.

## 0.8.0 — 2026-06-01

Fold Orbit's live Cashfree sandbox hotfix into Grace so a regen reproduces it
(generated-output-shape change → major per constitution §8):

- **Cashfree (`connector_docs/cashfree.md`):** `create_subscription` emits a positive
  `authorization_details.authorization_amount` (from `request.authorization_amount`, default
  ₹1.00; never `0`, which Cashfree rejects with `auth_amount_invalid_for_action`) plus the
  `authorization_amount_refund` flag; `create_order` returns the merchant `order_id` as
  `psp_order_id` (not `cf_order_id`) so `sync_payment` round-trips.
- **Generic (`connector_abc.md`):** every connector's `_map_http_error` now parses the PSP error
  body via `_extract_psp_error` and sets `ConnectorError.psp_code` / `psp_message` — connectors
  no longer swallow the PSP's real reason.
- **Tests (`testing.md`):** require assertions for the positive auth amount + refund flag, the
  merchant-id `psp_order_id`, and `psp_code`/`psp_message` on a 4xx error.

## 0.7.0 — 2026-06-01

- **Stop emitting `requires_lens` into generated connector packages.** The connector version
  gate was removed in Orbit Constitution v0.6: connectors ship bundled inside the `lens` wheel
  (one distribution, versioned by `lens.__version__`, regenerated in-tree), so a connector can
  never disagree with the Lens contract it was built against, and `ConnectorFactory.register`
  no longer reads `requires_lens`. A generated `__init__.py` now contains only the §4 marker,
  the imports, and `ConnectorFactory.register(...)` + `register_webhook(...)`.
- `compose.write_compose_surface` drops its `lens_version` argument; the rulebook, generation
  prompt, and `add-connector` skill no longer instruct writing `requires_lens` (they now carry
  an explicit "do not declare `requires_lens`" guardrail).
- `lens.version_constraint` is retained in config as the ABC-targeting selector but is no
  longer written into generated code.

## 0.6.0 — 2026-05-31

- Domain-modular, mandate-capable connectors: per-capability mixins (`<Psp>Orders`,
  `<Psp>Subscriptions`) over a shared `core/` base, composed into one registered
  `<Psp>Connector`, plus the shared `WebhookHandlers` builder. Added a
  `--domain {orders|subscriptions|all}` axis to `fetch-docs`/`generate` with incremental,
  per-domain regeneration.
