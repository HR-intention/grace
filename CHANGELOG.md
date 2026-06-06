# Changelog

Notable changes to the Grace codegen tool. Grace follows SemVer; per Orbit Constitution §8,
a rulebook/template change that alters generated-code shape is a **major** bump (expressed
pre-1.0 as a `0.x` increment). The §4 generated-file marker records the Grace version used.

## 0.9.1 — 2026-06-06

`create_subscription`: map `CreateSubscriptionRequest.customer_name` (new required lens field,
lens 0.6.1) into the PSP customer block.

- **`pattern_create_subscription.md`**: add `request.customer_name: str` (required) to the input
  field list and `customer_name=request.customer_name` to the `<Psp>CustomerDetails(...)` mapping.
- **`rulesbook/codegen/python/testing.md`**: add `customer_name` to the `_create_subscription_request`
  fixture and the "all fields forwarded" assertion list (else generated fixtures fail on the now-required field).
- **`rulesbook/codegen/python/domain_types.md`** and **`SUBPROJECT_LENS.md` §4.4**:
  `CreateSubscriptionRequest` gains `customer_name: str`.
- Regenerate Cashfree (`grace generate cashfree`) so the connector forwards `customer_name` to
  `customer_details.customer_name` and the generated subscription fixtures supply it.

- **`_<Psp>Base` builds its client via `lens.http.build_http_client`** (not raw `httpx.AsyncClient`),
  so generated connectors get outbound request/response logging (lens 0.6.1). Updated: the generation
  prompt's base example + `_SELF_CHECK_CORE` grep (now asserts `build_http_client` present / raw
  `httpx.AsyncClient(` absent), `connector_abc.md`, `pitfalls.md`, `file_layout.md`, `README.md`.
  Generated `__init__` preserves `timeout=30.0` + the `base_url_override` branch.
- **Generation agent now self-verifies with pytest + mypy before exiting.** A new `MANDATORY
  EXECUTION VERIFICATION` section in the generation prompt instructs the agent to run
  `mypy --strict . tests/` and `python -m pytest tests/ -v` on its own output, fix every reported
  error/failure, and rerun until both exit clean — before it exits. A hard guard explicitly
  prohibits fixing failures by weakening, skipping, or deleting assertions; broken connector logic
  must be fixed in the connector. This catches attribute errors and missing required fields in
  generated tests (e.g. `CreateSubscriptionRequest.CustomerContact` or dropped `customer_ref`)
  that grep-only structural checks cannot detect.

- **Body-idempotent marker de-churn:** after each generation run, a new de-churn
  pass compares every emitted `.py` file's marker-stripped body against the last-committed
  version in git HEAD. If the body is byte-identical the file is silently restored to HEAD's
  exact content (reverting the timestamp/version churn), so `git diff` only shows files with
  real code changes. New files and files outside any git repo keep their fresh markers. The
  pass is best-effort: any git error is logged at DEBUG and skipped — the pipeline never
  crashes. Covers both connector files under `output_dir` and relocated test files under
  `<tests_dir>/<psp>/`. Implemented in `pipeline/marker.py` (`extract_body`,
  `dechurn_if_unchanged`) and wired into `pipeline/orchestrate.py` after `_relocate_tests`.

Versioned **0.9.1** (patch) by request — note the §8 convention above would treat a
generated-shape change as a `0.x`-position bump.

## 0.9.0 — 2026-06-03

Customer-chosen mandate rail + plan upgrade/downgrade — reproduce the lens 0.3.0 / 0.4.0
hand-edits via regen (generated-output-shape change → major per constitution §8):

- **Rail set (`create_subscription`):** `CreateSubscriptionRequest.rail` → `rails: list[MandateRail] | None`;
  the connector translates it into the PSP `payment_methods` allow-list — deduped order-preserving
  union, `None`/empty ⇒ omit (never `[]`), unsupported rails rejected with `NOT_SUPPORTED` pre-HTTP.
- **Realized rail (webhook + sync):** `MandateWebhookEvent` and `SyncSubscriptionResponse` carry
  `realized_rail` / `authorization_reference` / `payment_group`, populated only on a successful
  authorization (the webhook and sync wire-key spellings may differ); plus a raw-preserving many→few
  `payment_group → MandateRail` mapper.
- **Plan management:** new `create_plan` (`POST /plans`, PERIODIC, deterministic plan id, major-unit
  amounts) + `change_plan` (CHANGE_PLAN manage action; ceiling rejection is a 400 → `INVALID_REQUEST`).
- **Pipeline:** `prompt.py` permits the realized-rail fields, imports the plan types, and instructs the
  new methods; `quality_rubric.py` gates `create_plan`/`change_plan`; `context.py` registers
  `pattern_create_plan.md`; new/updated rulebook patterns + mirror docs.

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
