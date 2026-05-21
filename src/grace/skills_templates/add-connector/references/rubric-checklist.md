# Quality rubric checklist

Each emitted package is scored 0–100 across six dimensions; pass threshold is 60. This table maps every dimension to the rulebook page that governs it, so when the gate fails you can go straight to the fix.

| Dimension | Max | What it checks | Rulebook page to sharpen |
|---|---|---|---|
| `marker_conformance` | 5 | The constitution §4 marker block is present at the top of every `.py` (Grace's `ensure_marker` post-processor backstops this; you should never see this fail). | `rulesbook/codegen/python/marker.md` |
| `type_correctness` | 20 | `mypy --strict` clean on the emitted package. Binary 20/0. | `rulesbook/codegen/python/connector_abc.md`, `domain_types.md` |
| `test_coverage` | 25 | `pytest --cov` ≥ 80% line coverage. Linear scale below that. | `rulesbook/codegen/python/testing.md` |
| `public_surface` | 20 | Required files exist; `class <Psp>(Connector)` defined; all four flows + handle_webhook + close present; `__init__.py` calls `ConnectorFactory.register(...)` and declares `requires_lens`; `status_map.py` references `PaymentAttemptStatus`. | `rulesbook/codegen/python/file_layout.md`, `pitfalls.md` |
| `error_handling` | 20 | `handle_webhook` raises `ConnectorError(WEBHOOK_SIGNATURE_FAILED)`; `ConnectorError` referenced in `connector.py`; httpx errors wrapped. | `rulesbook/codegen/python/webhook_handling.md`, `pitfalls.md` |
| `pii_discipline` | 10 | `auth.py` types credentials as `Maskable[T]`; no obvious `secret`-named values in log calls. | `rulesbook/codegen/python/ground_rules.md` (rule 11), `pitfalls.md` (§6) |

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

**`type_correctness` = 0 + detail mentions `Cannot find module named "lens"`**: Lens isn't installed in the venv invoking `grace`. Fix by installing Lens (the consumer) in editable mode in its own venv: `cd lens && uv sync --extra dev`, then run grace from there.

**`public_surface` < 20 + detail mentions `no class named (case-insensitive) <psp>`**: Claude emitted `class <Psp>Connector` or similar suffix. Sharpen `pitfalls.md` §1 with an example using the offending PSP name.

**`error_handling` < 20 + detail mentions `handle_webhook does not raise ConnectorError(WEBHOOK_SIGNATURE_FAILED)`**: Claude raised `ValueError` or returned a benign default. Sharpen `webhook_handling.md` with a "do not raise generic exceptions" note + the exact required line.

**`test_coverage` = 0 + detail mentions coverage 0.0%**: Tests don't import, usually because the generated `from lens.X import Y` paths are wrong (e.g. `lens.connector_abc`). Sharpen `pitfalls.md` §2.

**`pii_discipline` < 10 + detail mentions `credentials not typed Maskable`**: Claude wrote `client_secret: str` bare. Sharpen `pitfalls.md` §6 with a counter-example.
