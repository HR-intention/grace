# Grace

Build-time CLI that generates Python PSP (payment service provider) connectors for the [Orbit Lens](docs/superpowers/specs/SUBPROJECT_LENS.md) library. Reads a PSP's API docs, hands them to **Claude Code**, runs the output through quality gates (`mypy --strict`, `pytest --cov`, a 6-dimension rubric), writes the generated package to disk.

Grace itself runs only at build time. Generated code is committed to git and reviewed like any other code.

**Dependency direction**: Grace is a standalone CLI tool with **zero knowledge of Lens**. Lens (or any other consumer) installs Grace as a build-time dev dependency, invokes the `grace` CLI from within its own tree, and lets Grace write generated code into its package. The quality-gate subprocesses (`mypy`, `pytest`) inherit the consumer's venv — so all the `from lens.connector import Connector` imports in the generated code resolve correctly. Grace itself never `import lens`.

> **Scope (v0.4)**: hosted-checkout PSPs only, four flows (`create_order`, `sync_payment`, `refund`, `sync_refund`) + webhook. Server-to-server flows (`authorize`/`capture`/`void`) and recurring/mandates are deliberately out of scope; see [`docs/superpowers/specs/FUTURE_S2S_INTERFACE.md`](docs/superpowers/specs/FUTURE_S2S_INTERFACE.md).

---

## One-time setup

### 1. Install Grace into the consumer's venv

Requires Python ≥ 3.11. Grace is meant to be installed as a build-time dev dependency of the repo that consumes it (typically Lens). From the consumer repo:

```bash
# Option A — uv path dep (recommended if Grace and Lens are sibling checkouts)
#   In the consumer's pyproject.toml:
#     [project.optional-dependencies]
#     dev = ["grace-cli", ...]
#     [tool.uv.sources]
#     grace-cli = { path = "../grace", editable = true }
#   Then:
uv sync --extra dev

# Option B — explicit editable install
uv pip install -e ../grace
```

Standalone Grace development (working on Grace itself, not generating connectors):

```bash
cd grace
uv sync --extra dev
```

Verify the CLI either way:

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

### 3. Configure paths for your repo layout

Grace looks for `<cwd>/.grace/config.yaml` first, falling back to
`~/.grace/config.yaml`, then built-in defaults. The most important keys for
a new consumer are the `paths.*` settings — these tell Grace where to put
docs snapshots and the generated package.

For a **src-layout** consumer like Lens (where the package root is
`src/lens/`), one-time setup:

```bash
cd /path/to/lens
uv run grace config set paths.output_dir src/lens/connectors
# Optional: change the docs snapshot dir too
# uv run grace config set paths.docs_dir my_docs
```

That writes `<cwd>/.grace/config.yaml`. Verify with:

```bash
uv run grace config show
# → docs_dir   = connector_docs
# → output_dir = src/lens/connectors
# Resolved at <cwd>:
#   docs:    /path/to/lens/connector_docs/<psp>
#   output:  /path/to/lens/src/lens/connectors/<psp>
```

Without this step, `output_dir` defaults to `lens/connectors` (flat layout
at the repo root) — which is **outside the importable package** for
src-layout repos, so `from lens.connectors.<psp> import ...` won't resolve
to the generated code. Setting it to `src/lens/connectors` puts the
generated package on the import path.

The same config file accepts any of:

```yaml
paths:
  docs_dir: connector_docs            # default; where fetch-docs writes
  output_dir: src/lens/connectors      # default is lens/connectors
claude_code:
  cli_path: null                       # null ⇒ auto-detect via `which claude`
  timeout_s: 6000                      # 100 min; raise for very complex PSPs
quality:
  mypy_strict: true
  min_coverage_pct: 80
  min_rubric_score: 60
lens:
  version_constraint: "^0.1"
```

CLI flags override config. `--output <path>` and `--from <path>` on `grace
generate` always beat the configured defaults. **No provider API keys live
here.** Add `.grace/` to your `.gitignore`.

---

## Generating a connector

**All commands below run from inside the consumer repo (Lens).** Grace's
`connector_docs/<psp>/` defaults to `<cwd>/connector_docs/<psp>` and
`--output` defaults to `<cwd>/lens/connectors/<psp>` — both versioned with
the consumer, not with Grace. The quality-gate subprocesses (`mypy`,
`pytest`) inherit the consumer's venv, so `from lens.connector import ...`
in the generated code resolves naturally.

Two-step workflow: snapshot the PSP's docs, then generate.

### Step 1 — Snapshot docs

Most modern PSP doc sites publish an [`llms.txt`](https://llmstxt.org/) index listing every markdown page. `grace fetch-docs` reads that index, filters to the v1-relevant pages, and writes them to `<cwd>/connector_docs/<psp>/`.

```bash
cd /path/to/lens

# Cashfree
uv run grace fetch-docs cashfree --from https://www.cashfree.com/docs/llms.txt
# → writes ~30 .md files to connector_docs/cashfree/ in the Lens repo

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

**Commit `connector_docs/<psp>/` in the Lens repo.** This pins the docs Grace consumed at generation time, making the run reproducible alongside the package it produced.

```bash
git add connector_docs/cashfree/
git commit -m "docs(cashfree): snapshot v1 doc pages for grace"
```

### Step 2 — Generate

```bash
# from inside the Lens repo
uv run grace generate cashfree
# → writes to lens/connectors/cashfree/ by default
```

When `--from` is omitted, Grace defaults to `<cwd>/connector_docs/<psp>/`. When `--output` is omitted, Grace defaults to `<cwd>/lens/connectors/<psp>/`. Explicit `--from` accepts a URL, a local file, or a local directory.

The pipeline:
1. Assembles context (Grace rulebook + snapshotted docs).
2. Spawns `claude -p --permission-mode acceptEdits`, CWD = output directory. Claude writes the package files. Output streams live to your terminal.
3. Post-processes any `.py` missing the constitution §4 marker (belt-and-suspenders).
4. Runs `mypy --strict` + `pytest --cov` + the 6-dimension rubric. The gate subprocesses inherit the **consumer's venv** — so `from lens.connector import Connector` in the generated code resolves to the real Lens package (Lens must be installed in editable mode in its own dev venv for this to work; standard practice anyway).
5. Writes `quality_report.json` next to the package; raises on any gate failure.

Inspect the result:

```bash
ls lens/connectors/cashfree/
# __init__.py  auth.py  connector.py  models.py  status_map.py  quality_report.json  tests/

cat lens/connectors/cashfree/quality_report.json | python -m json.tool
# {
#   "total": 87,
#   "passed": true,
#   "dimensions": [ ... ]
# }
```

### Re-running with the same args

```bash
uv run grace regenerate cashfree
# replays the last `grace generate cashfree` invocation from <cwd>/.grace/last_run.json
```

Use this when you've tightened the rulebook and want to re-run against the pinned docs.

The record lives at `<cwd>/.grace/last_run.json` (i.e., in whichever consumer repo grace was invoked from), so two checkouts iterating on Grace simultaneously don't clobber each other's state. Add `.grace/` to your repo's `.gitignore`.

---

## CLI reference

```
grace --version
grace doctor                                          # is Claude Code reachable?
grace config show / get <key> / set <key> <value>     # per-project paths + thresholds
grace fetch-docs <psp> --from <llms.txt-url-or-path>  # snapshot PSP docs
grace generate   <psp> [--from <src>] [--output <dir>]
grace regenerate <psp>
grace docs                                            # rebuild docs-generated/llms.txt
grace skills list                                     # list bundled .skills/ templates
grace skills install [--force]                        # copy them into <cwd>/.skills/
```

Run any command with `-h` for full options.

## Bundled artifacts the consumer (Lens) commits

After `grace generate <psp>` succeeds, three trees end up in the consumer repo and should all be committed together. Two are refreshed automatically; one is bootstrapped once.

| Tree | Refreshed when | Purpose |
|---|---|---|
| `lens/connectors/<psp>/` | every `grace generate` | The runtime connector package. |
| `connector_docs/<psp>/` | every `grace fetch-docs` | The PSP doc snapshot Grace consumed (pins the input for reproducibility). |
| `docs-generated/llms.txt` + `docs-generated/connectors/<psp>.md` | every `grace generate` (auto) | Catalog for downstream AI agents — modeled on juspay-prism's pattern. |
| `.skills/` | once, via `grace skills install` | Claude Code Skills the consumer uses for `add-connector` workflows. |

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
