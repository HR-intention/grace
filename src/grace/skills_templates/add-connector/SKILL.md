---
name: add-connector
description: >
  Adds a new PSP (payment service provider) connector to Lens. Orchestrates
  `grace fetch-docs`, `grace generate`, the diff review, and the
  `docs-generated/` refresh. Use when Lens needs to gain support for a new
  hosted-checkout PSP (Razorpay, Stripe, etc.) — not for tweaking an existing
  one.
license: MIT
compatibility: Requires Python ≥ 3.11, `uv`, and Grace installed as an editable dev dep (`uv pip install -e ../grace` or via `[tool.uv.sources]`).
metadata:
  author: Symplora Engineering
  version: "1.0"
  domain: payment-connectors
---

# Add Connector

## Overview

Adds one new PSP connector to the Lens runtime library. The output is a
Python package at `lens/connectors/<psp>/` that implements Lens's locked
`Connector` ABC, plus a refreshed `docs-generated/llms.txt`.

**Inputs:**
- PSP name (lowercase, e.g. `razorpay`)
- URL of the PSP's `llms.txt` (or local path to one)

**Output:**
- `lens/connectors/<psp>/` — the generated package (Connector class, auth, models,
  status_map, tests)
- `connector_docs/<psp>/*.md` — pinned doc snapshots Grace used as input
- `docs-generated/llms.txt` — refreshed to include the new connector
- `docs-generated/connectors/<psp>.md` — per-connector reference page

## Flow phases

Run these in order. **Phase 4 is a hard checkpoint** — if the quality gates
fail there, fix the rulebook (in Grace, never in the generated code) and
restart from Phase 2.

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
uv run grace fetch-docs <psp> --from <llms.txt-url>
```

This writes filtered markdown into `connector_docs/<psp>/`. Review the
file list — if too few pages survived the default filter, pass
`--include "*<pattern>*"` globs (see `references/grace-cli-cheatsheet.md`).

**Commit the snapshot** so the regen is reproducible:

```bash
git add connector_docs/<psp>/
git commit -m "docs(<psp>): snapshot v1 doc pages for grace"
```

### Phase 3 — Generate

```bash
uv run grace generate <psp>
```

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

Common iteration: Cashfree's status terms (`USER_DROPPED`, `FLAGGED`,
`CANCELLED`) need explicit mapping. Razorpay uses different vocabulary
(`captured`, `failed`, `created`). When the rubric flags status-map
gaps, the fix is always in `<grace>/rulesbook/codegen/python/status_mapping.md`
or the per-PSP `status_map.py` mapping table.

### Phase 5 — Review the diff

```bash
git diff lens/connectors/<psp>/
```

Read the generated `connector.py` end-to-end. The locked surface is
small (see `references/flow-patterns/`) — spotting deviations is fast.
Confirm:

- [ ] `class <Psp>(Connector):` (PascalCase, no `Connector` suffix)
- [ ] `from lens.connector import Connector`
- [ ] All five flow methods are `async def`
- [ ] `__init__.py` calls `ConnectorFactory.register("<psp>", <Psp>)` AND declares `requires_lens`
- [ ] `auth.py` types credentials as `Maskable[str]`
- [ ] `handle_webhook` raises `ConnectorError(reason=ConnectorErrorReason.WEBHOOK_SIGNATURE_FAILED)` on bad signature
- [ ] `status_map.py` uses ONLY the locked enum values (see `references/rubric-checklist.md`)

### Phase 6 — Land

```bash
git add lens/connectors/<psp>/ docs-generated/
git commit -m "feat(connectors): add <Psp> via grace"
```

`docs-generated/llms.txt` and `docs-generated/connectors/<psp>.md` are
refreshed automatically by `grace generate`; commit them alongside the
package so downstream consumers see the new connector advertised.

## Don't

- **Don't hand-edit generated files.** Every file in `lens/connectors/<psp>/`
  carries the constitution §4 marker; modifications are forbidden. If the
  output is wrong, fix the Grace rulebook and regenerate.
- **Don't widen scope.** v1 ships four flows: `create_order`, `sync_payment`,
  `refund`, `sync_refund`. If the PSP supports server-to-server
  `authorize`/`capture`/`void`, those land in a later product slice
  (`docs/superpowers/specs/FUTURE_S2S_INTERFACE.md`).
- **Don't invent enum values.** `PaymentAttemptStatus` is `PENDING | SUCCESS | FAILED`,
  full stop. `PaymentFailureCode` has eleven locked values. PSP-specific terms
  map INTO these via `status_map.py`.

## References

- `references/grace-cli-cheatsheet.md` — every `grace` command + the
  options that actually matter.
- `references/rubric-checklist.md` — what each of the six rubric dimensions
  measures + the rulebook page that fixes it.
- `references/flow-patterns/` — per-flow implementation patterns
  (Python skeleton, errors to surface, required tests).
