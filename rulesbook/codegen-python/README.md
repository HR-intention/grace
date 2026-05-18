# codegen-python — Python language pack

Sibling of `codegen-rust/`. Produces Python connectors for the
`connector-service-python` shell at the sibling repo.

## Entrypoints

| File | Command form | Status |
|---|---|---|
| `.gracerules` | `integrate <Connector> using grace/rulesbook/codegen-python/.gracerules` | **Wave 1 — works** |
| `.gracerules_add_flow` | `add <Flow> flow to <Connector> using grace/rulesbook/codegen-python/.gracerules_add_flow` | Wave 2 stub |
| `.gracerules_add_payment_method` | `add <Category>:<PM> to <Connector> using grace/rulesbook/codegen-python/.gracerules_add_payment_method` | Wave 2 stub |

## Wave 1 scope

- **7 flows:** Authorize, PSync, Capture, Refund, RSync, Void, IncomingWebhook
- **3 PMs:** Card, Wallet, UPI (Collect + Intent)
- Indian payment ecosystem first — UPI is mandatory, webhook dedup is required

## How it connects to the rest

- Type-system surface comes from `connector-service-python/connector_service/domain_types/` (Plan C). See [`guides/types/types.md`](guides/types/types.md) for the cross-reference.
- Flow definitions, prerequisite DAG, payment-method taxonomy, and quality rubric come from [`../shared/`](../shared/) — same as `codegen-rust`.
- Per-language quality checks live in [`guides/quality/python_quality_checks.md`](guides/quality/python_quality_checks.md).

## See also

- [`../codegen-rust/`](../codegen-rust/) — Rust language pack
- [`../shared/`](../shared/) — language-neutral content (flows, payment_methods, quality_rubric, feedback, learnings)
