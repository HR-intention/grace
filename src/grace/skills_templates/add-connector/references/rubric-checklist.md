# Quality rubric checklist

Each emitted package is scored 0–100 across six dimensions; pass threshold is 60. This table maps every dimension to the rulebook page that governs it, so when the gate fails you can go straight to the fix.

| Dimension | Max | What it checks | Rulebook page to sharpen |
|---|---|---|---|
| `marker_conformance` | 5 | The constitution §4 marker block is present at the top of every `.py` (Grace's `ensure_marker` post-processor backstops this; you should never see this fail). | `rulesbook/codegen/python/marker.md` |
| `type_correctness` | 20 | `mypy --strict` clean on the emitted package. Generated code must use modern Python 3.11 typing (`dict[str, str]`, `X \| None`, `set[...]`, `StrEnum`) — **never** `Dict`/`List`/`Optional`/`Set` from `typing`. Binary 20/0. | `rulesbook/codegen/python/connector_abc.md`, `domain_types.md` |
| `test_coverage` | 25 | `pytest --cov` ≥ 80% line coverage. Must include mandate lifecycle tests (create, sync, cancel, pause, resume) and mandate + payment webhook router tests; `status_map.py` must map every documented PSP status and event-type term. | `rulesbook/codegen/python/testing.md` |
| `public_surface` | 20 | **Register-based class discovery + capability composition**: the rubric discovers the registered class from `ConnectorFactory.register("<psp>", X)` in `__init__.py` — **not** by class name — and verifies (1) the class isinstance-composes ≥1 capability interface (`PaymentsConnector` / `MandateConnector`), never bare `Connector`; (2) zero leftover abstract methods (resolved across the MRO); (3) domain layout matches §3.2: `core/base.py`, `core/auth.py`, root `connector.py`/`webhooks.py`; per active domain `connector.py`/`status_map.py`/`webhooks.py`; (4) `__init__.py` calls **both** `ConnectorFactory.register(...)` and `ConnectorFactory.register_webhook(...)`; (5) root `webhooks.py` exports `build_webhook_handlers`; (6) per-domain flows present (`orders`: 4 payment flows + 2 props; `subscriptions`: 5 lifecycle + 4 introspection). | `rulesbook/codegen/python/file_layout.md`, `pitfalls.md` |
| `error_handling` | 20 | `WebhookRouter` raises `ConnectorError(WEBHOOK_SIGNATURE_FAILED)` on bad signature (via the `verify` callable in `WebhookHandlers`); unknown webhook family raises `ConnectorError(NOT_SUPPORTED)`; all `httpx` failures in flow methods are wrapped in `ConnectorError` with the correct reason; no raw `httpx.HTTPError` escapes. | `rulesbook/codegen/python/webhook_handling.md`, `pitfalls.md` |
| `pii_discipline` | 10 | `auth.py` types credentials as `Maskable[T]`; no obvious `secret`-named values in log calls; `CustomerContact.email` and `.phone` are not logged in plaintext. | `rulesbook/codegen/python/ground_rules.md` (rule 11), `pitfalls.md` (§6) |

## Reading `quality_report.json`

```json
{
  "total": 87,
  "passed": true,
  "dimensions": [
    {
      "name": "marker_conformance",
      "max": 5,
      "score": 5,
      "detail": "all files carry the §4 marker"
    },
    ...
  ]
}
```

For each dimension where `score < max`:

1. Read `detail` — it lists the specific issues found.
2. Open the rulebook page from the table above.
3. Add a `pitfalls.md` entry if the failure mode is one Claude is likely to repeat across PSPs.
4. Re-run `uv run grace regenerate <psp>`.

## Common failure recipes

**`type_correctness` = 0 + detail mentions `Cannot find module named "lens"`**: Lens isn't installed in the venv invoking `grace`. Fix by installing Lens (the consumer) in editable mode: `cd <sylibs>/packages/lens && uv sync --extra dev`, then run grace from there.

**`public_surface` < 20 + detail mentions `registered class is not a PaymentsConnector or MandateConnector`**: Claude subclassed bare `Connector` instead of a capability interface. Sharpen `pitfalls.md` §1 with an example.

**`public_surface` < 20 + detail mentions `register_webhook not called`**: Claude omitted `ConnectorFactory.register_webhook(...)` from `__init__.py`. Sharpen `file_layout.md` with a note that both `register` and `register_webhook` are required.

**`public_surface` < 20 + detail mentions `build_webhook_handlers not exported`**: root `webhooks.py` is missing or doesn't export the builder. Sharpen `webhook_handling.md`.

**`error_handling` < 20 + detail mentions `handle_webhook method found on connector`**: Claude reverted to the lens-0.1 pattern. Sharpen `webhook_handling.md` with a "DO NOT add handle_webhook" callout. The shared `WebhookRouter` (via `build_webhook_handlers`) is the only correct webhook entry-point.

**`error_handling` < 20 + detail mentions `WEBHOOK_SIGNATURE_FAILED` not raised**: The `verify` callable in `WebhookHandlers` returned `False` without the router raising. This is a lens framework behaviour — ensure `build_webhook_handlers` supplies the correct `verify` callable closing over config. Sharpen `webhook_handling.md` §verify.

**`test_coverage` = 0 + detail mentions coverage 0.0%**: Tests don't import, usually because the generated `from lens.X import Y` paths are wrong. Sharpen `pitfalls.md` §2.

**`pii_discipline` < 10 + detail mentions `credentials not typed Maskable`**: Claude wrote `client_secret: str` bare. Sharpen `pitfalls.md` §6 with a counter-example.

**`type_correctness` < 20 + detail mentions `Optional` or `Dict`**: deprecated typing aliases from `typing` used. Sharpen `connector_abc.md` / `domain_types.md` with a "use built-in generics only" rule.
