# Grace CLI cheatsheet

Every command in the `grace` CLI, with the flags that actually matter for adding a connector.

## `grace doctor`

Verifies the local `claude` binary is reachable + authenticated for headless mode.

```bash
uv run grace doctor
# → "healthy: 2.x.x (Claude Code)"  on success, exit 0
# → "unhealthy: ..."                on failure,  exit 1
```

The most common failure is `CLAUDE_CODE_NOT_AUTHENTICATED` — fix with `claude setup-token` then `export CLAUDE_CODE_OAUTH_TOKEN="..."`. The headless OAuth refresh bug is anthropics/claude-code#28827; a long-lived token works around it.

## `grace fetch-docs`

Pulls the relevant markdown pages out of a PSP's `llms.txt`, groups them by
domain, and writes them to `<cwd>/connector_docs/<psp>/{_shared,orders,subscriptions}/`.
Also scaffolds a developer-editable `connector_docs/<psp>.md` spec.

```bash
uv run grace fetch-docs <psp> --from <llms.txt-url-or-path> --domain all
```

Options that matter:

| Flag | Default | When to set |
|---|---|---|
| `--domain orders\|subscriptions\|all` | `all` | Fetch only the pages relevant to a single capability domain. |
| `--include "<glob>"` | Tuned defaults per domain (payments, webhooks, auth, overview, subscriptions, mandates, etc.) | The PSP uses a non-standard path layout. Repeat for OR. |
| `--exclude "<glob>"` | Drops `previous/*`, S2S flows, payouts, etc. | The PSP has a doc section that survives the include glob but you want it out. Repeat for OR. |
| `--output <dir>` | `<cwd>/connector_docs/<psp>/` | Almost never. |

After fetching, **edit `connector_docs/<psp>.md`** to fill in the PSP-specific
normalization decisions (status mapping, failure codes, webhook discriminator
logic). Grace's `generate` step reads this spec.

## `grace generate`

The full pipeline: assemble domain-scoped context → spawn `claude -p` (output streams live) → post-process markers → run quality gates → emit `quality_report.json` → refresh `docs-generated/`.

```bash
uv run grace generate <psp> --domain all
```

Options that matter:

| Flag | Default | When to set |
|---|---|---|
| `--domain orders\|subscriptions\|all` | `all` | Target a single capability domain. `--domain subscriptions` rewrites only `subscriptions/*` + the compose surface (`connector.py`, `webhooks.py`, `__init__.py`); `core/` and other domains are untouched. |
| `--from <src>` | `<cwd>/connector_docs/<psp>/` (output of `fetch-docs`) | You want to use a different docs snapshot (e.g. an older one for diffing). |
| `--output <dir>` | `<cwd>/lens/connectors/<psp>/` | Almost never. |
| `--config <path>` | `~/.grace/config.yaml` | Tests / experiments. |

If the gates fail, the exit is non-zero and `quality_report.json` is still written for triage.

## `grace regenerate`

Re-runs the last `grace generate <psp>` with the same `--from`/`--output` args. Useful after sharpening the rulebook.

```bash
uv run grace regenerate <psp>
```

Source of truth: `~/.grace/last_run.json`. Delete that file to force a clean re-run from scratch.

## `grace docs`

Standalone rebuild of `docs-generated/`. You shouldn't need to run this directly — `grace generate` invokes it on success. Run it manually if you've added a connector by hand (rare; don't) or if the catalog is out of sync after a manual git operation.

```bash
uv run grace docs
```

## `~/.grace/config.yaml`

Optional. All keys default sensibly. The two that move the most:

```yaml
claude_code:
  cli_path: null          # null ⇒ auto-detect via `which claude`
  timeout_s: 6000         # 100 min; raise to 9000+ for very complex PSPs

quality:
  mypy_strict: true
  min_coverage_pct: 80
  min_rubric_score: 60

lens:
  version_constraint: "^0.2"  # selects which lens ABCs to target; not emitted into generated code (v0.6)
```

CLI flags override config. **No API keys live here.**
