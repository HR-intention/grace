# Grace

Build-time CLI that generates Python PSP (payment service provider) connectors for the [Orbit Lens](docs/superpowers/specs/SUBPROJECT_LENS.md) library. Reads a PSP's API docs, hands them to **Claude Code**, runs the output through quality gates (`mypy --strict`, `pytest --cov`, a 6-dimension rubric), writes the generated package to disk.

Grace itself runs only at build time. Generated code is committed to git and reviewed like any other code.

> **Scope (v0.4)**: hosted-checkout PSPs only, four flows (`create_order`, `sync_payment`, `refund`, `sync_refund`) + webhook. Server-to-server flows (`authorize`/`capture`/`void`) and recurring/mandates are deliberately out of scope; see [`docs/superpowers/specs/FUTURE_S2S_INTERFACE.md`](docs/superpowers/specs/FUTURE_S2S_INTERFACE.md).

---

## One-time setup

### 1. Install

Requires Python ≥ 3.11. Uses [`uv`](https://docs.astral.sh/uv/) for env + deps.

```bash
cd grace
uv sync --extra dev
```

Verify:

```bash
uv run grace --version
# grace, version 0.1.0
```

### 2. Authenticate the local Claude Code CLI (mandatory)

Grace shells out to the local `claude` binary in headless mode (`claude -p`). The interactive `claude` session and headless mode share credentials, **but headless OAuth refresh is broken for subscription users** ([anthropics/claude-code#28827](https://github.com/anthropics/claude-code/issues/28827)). You must set up a long-lived token explicitly.

```bash
# Generates a long-lived OAuth token tied to your Anthropic account
# (works for Claude Pro / Max subscriptions — no API key required)
claude setup-token

# Copy the printed token and export it in your shell rc (~/.zshrc, ~/.bashrc, …)
export CLAUDE_CODE_OAUTH_TOKEN="<paste-the-token>"
```

Reload your shell or `source` the rc, then verify:

```bash
echo "say hi" | claude -p
# should reply, not 401

uv run grace doctor
# healthy: 2.x.x (Claude Code)
```

If `claude setup-token` itself errors, your installed CLI version may not support it — upgrade Claude Code, or fall back to an `ANTHROPIC_API_KEY` from `console.anthropic.com` (API credit required).

### 3. (Optional) Per-user config

`~/.grace/config.yaml` (all keys optional):

```yaml
claude_code:
  cli_path: null          # null ⇒ auto-detect via `which claude`
  timeout_s: 6000         # 100 min; raise if generations time out
quality:
  mypy_strict: true
  min_coverage_pct: 80
  min_rubric_score: 60
lens:
  version_constraint: "^0.1"
```

CLI flags override config. **No provider API keys live here.**

---

## Generating a connector

Two-step workflow: snapshot the PSP's docs, then generate.

### Step 1 — Snapshot docs

Most modern PSP doc sites publish an [`llms.txt`](https://llmstxt.org/) index listing every markdown page. `grace fetch-docs` reads that index, filters to the v1-relevant pages, and writes them to `connector_docs/<psp>/`.

```bash
# Cashfree
uv run grace fetch-docs cashfree --from https://www.cashfree.com/docs/llms.txt
# → writes ~30 .md files to connector_docs/cashfree/

# Razorpay (example URL — confirm the actual location)
uv run grace fetch-docs razorpay --from https://razorpay.com/docs/llms.txt
```

The default include/exclude globs are tuned for hosted-checkout PSPs: keeps `orders/`, `payments/`, `refunds/`, `webhooks/`, auth, overview, enums, errors. Drops S2S flows, subscriptions, payouts, disputes, splits, etc. To override:

```bash
uv run grace fetch-docs cashfree \
  --from https://www.cashfree.com/docs/llms.txt \
  --include "*api*orders*" --include "*api*refunds*" \
  --exclude "*previous/*"
```

**Commit `connector_docs/<psp>/` to the repo.** This pins the docs Grace consumed at generation time, making the run reproducible.

```bash
git add connector_docs/cashfree/
git commit -m "docs(cashfree): snapshot v1 doc pages for grace"
```

### Step 2 — Generate

```bash
uv run grace generate cashfree \
  --output /tmp/grace_cashfree_run1/lens/connectors/cashfree
```

When `--from` is omitted, Grace defaults to `connector_docs/<psp>/`. Explicit `--from` accepts a URL, a local file, or a local directory.

The pipeline:
1. Assembles context (Grace rulebook + snapshotted docs).
2. Spawns `claude -p --permission-mode acceptEdits`, CWD = output directory. Claude writes the package files.
3. Post-processes any `.py` missing the constitution §4 marker (belt-and-suspenders).
4. Runs `mypy --strict` + `pytest --cov` + the 6-dimension rubric on the result.
5. Writes `quality_report.json` next to the package; raises on any gate failure.

Inspect the result:

```bash
ls /tmp/grace_cashfree_run1/lens/connectors/cashfree/
# __init__.py  auth.py  connector.py  models.py  status_map.py  quality_report.json  tests/

cat /tmp/grace_cashfree_run1/lens/connectors/cashfree/quality_report.json | python -m json.tool
# {
#   "total": 87,
#   "passed": true,
#   "dimensions": [ ... ]
# }
```

### Re-running with the same args

```bash
uv run grace regenerate cashfree
# replays the last `grace generate cashfree` invocation from ~/.grace/last_run.json
```

Use this when you've tightened the rulebook and want to re-run against the pinned docs.

---

## CLI reference

```
grace --version
grace doctor                                          # is Claude Code reachable?
grace fetch-docs <psp> --from <llms.txt-url-or-path>  # snapshot PSP docs
grace generate   <psp> [--from <src>] [--output <dir>]
grace regenerate <psp>
```

Run any command with `-h` for full options.

---

## Troubleshooting

**`CLAUDE_CODE_NOT_AUTHENTICATED` / 401 from `claude -p`**
You're on a Claude subscription (Pro/Max) and headless OAuth refresh is failing — re-run `claude setup-token` and export `CLAUDE_CODE_OAUTH_TOKEN` (see "One-time setup → 2"). Verify with `echo hi | claude -p`.

**`CLAUDE_CODE_TIMEOUT`**
Default timeout is 100 minutes. For very complex PSPs, bump `claude_code.timeout_s` in `~/.grace/config.yaml`.

**`CONTEXT_BUNDLE_INVALID: rulebook file missing`**
You're running Grace from outside its repo (e.g., a copy). `cd` into the Grace repo first; `grace` resolves the rulebook relative to its own source tree.

**`QUALITY_GATE_FAILED: rubric: <X> < 60`**
Read `quality_report.json` for the per-dimension breakdown. The fix is in the **rulebook** (`rulesbook/codegen/python/*.md` or `rulesbook/codegen/guides/patterns/*.md`), **not in the generated code** — hand-editing generated files is forbidden (constitution §4). Sharpen the rulebook page that maps to the missing dimension, then `grace regenerate <psp>`.

**`grace generate` says "no --from and connector_docs/<psp>/ is empty"**
Run `grace fetch-docs <psp> --from <llms.txt-url>` first, or pass an explicit `--from` URL/path/directory.

**Want a fresh source URL but the same output?**
Edit `~/.grace/last_run.json`, or just rerun `grace generate` with the new `--from`.

---

## Architecture

The full design lives in [`docs/superpowers/`](docs/superpowers/):

- [`specs/ORBIT_CONSTITUTION.md`](docs/superpowers/specs/ORBIT_CONSTITUTION.md) — system-level invariants (locked).
- [`specs/SUBPROJECT_GRACE_CODEGEN.md`](docs/superpowers/specs/SUBPROJECT_GRACE_CODEGEN.md) — this sub-project's locked spec.
- [`specs/SUBPROJECT_LENS.md`](docs/superpowers/specs/SUBPROJECT_LENS.md) — the runtime library Grace generates against.
- [`plans/PLAN_GRACE_CODEGEN.md`](docs/superpowers/plans/PLAN_GRACE_CODEGEN.md) — the implementation plan this repo executes.

In one diagram:

```
PSP API docs (URL or local)
        │
        ▼
  ┌───────────────────────────────┐
  │ grace fetch-docs              │
  │ → connector_docs/<psp>/*.md   │
  └───────────────┬───────────────┘
                  │
                  ▼
  ┌───────────────────────────────┐
  │ grace generate                │
  │ ├ context  (rulebook + docs)  │
  │ ├ invoke   (claude -p)        │
  │ └ gates    (mypy + cov +      │
  │             6-dim rubric)     │
  └───────────────┬───────────────┘
                  │ writes
                  ▼
        lens/connectors/<psp>/
                  │
                  ▼
       committed to git, reviewed
       like any other code
```

---

## Upstream

This is the Symplora team's fork of [`juspay/hyperswitch-prism`](https://github.com/juspay/hyperswitch-prism) (née `juspay-prism/grace`). Upstream is Rust-targeted; this fork's `python-codegen` track adds Python connector generation. Periodic subtree merges from upstream pull non-rule-related improvements.
