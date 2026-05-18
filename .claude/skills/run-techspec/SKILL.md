---
name: run-techspec
description: Use when the user asks to "generate a tech spec", "run grace techspec", "scrape connector docs", or wants to produce/regenerate a `technical_specification.md` for a PSP connector. Handles venv activation, env-var validation, flag selection (-f vs -u, -e, -m, -v), and output verification. Side-effecting (writes files, calls paid APIs) so user-invocable only.
disable-model-invocation: true
---

# Run `grace techspec`

The Python CLI entrypoint for generating a `technical_specification.md` from source documentation. The spec is the input the rulesbook needs to generate Rust connector code in `connector-service`.

## When to use

User asks to:
- "Generate a tech spec for X"
- "Run grace techspec X with these docs"
- "Re-run techspec for X with enhancement"
- "Produce a mock server for X"

## Pre-flight checklist (run before invoking)

1. **Working directory must be `grace/`** (where `pyproject.toml` and `.venv` live).
   ```bash
   pwd  # should end in /grace
   ls pyproject.toml .venv  # both must exist
   ```
2. **Virtualenv must be activated.** If `which grace` returns nothing or points outside `.venv/`:
   ```bash
   source .venv/bin/activate
   ```
3. **Required env vars** (from `.env` — see [.env.example](.env.example) and [CLAUDE.md](CLAUDE.md#environment-variables)):
   - `AI_API_KEY` — always required.
   - `FIRECRAWL_API_KEY` — required only when using `-u` (URL scraping). Without it, scraping silently fails and LLM analysis runs on empty input.
   - `ANTHROPIC_API_KEY` — required only with `-e`. Falls back to `AI_API_KEY` if unset.

   Verify before running:
   ```bash
   grep -E "^(AI_API_KEY|FIRECRAWL_API_KEY)=" .env
   ```

## Choosing flags

| User intent | Flags |
|---|---|
| Generate spec from local PDFs / markdown | `-f /path/to/docs` |
| Generate spec from URLs | `-u urls.txt` (one URL per line) |
| Use both URLs and enhancement loop | `-u urls.txt -e` |
| Field-dependency analysis on top of base spec | `-e` (also enables Claude Agent SDK enhancement) |
| Generate a mock server alongside the spec | `-m` |
| See node-by-node progress | `-v` (always use during debugging) |
| Validate flow without writing files | `--test-only` |
| Custom output dir (overrides `TECHSPEC_OUTPUT_DIR`) | `-o ./somewhere` |

Default output path: `${TECHSPEC_OUTPUT_DIR}/<connector>/technical_specification.md` (env var defaults to `./output`, but most workflows point it at `./rulesbook/codegen-rust/references`).

## Standard invocations

```bash
# Local docs folder, verbose
grace techspec stripe -f ~/Downloads/stripe-docs -v

# URL list with enhancement
grace techspec adyen -u adyen_urls.txt -e -v

# Local docs + mock server
grace techspec airwallex -f ./docs/airwallex -m -v

# Connector name omitted — CLI will infer from spec content via LLM
grace techspec -f ./docs/unknown_psp -v
```

## After the run

1. Check exit code (`echo $?`) — non-zero means failure; re-run with `-v` if you didn't.
2. Verify the spec was written:
   ```bash
   ls -la "${TECHSPEC_OUTPUT_DIR:-./output}"/<connector>/
   ```
   Expect `technical_specification.md`. With `-e`: also `*_enhanced_spec.md`. With `-m`: also a `mock-server/` subdirectory.
3. Skim the spec — open it and confirm it has Base URL, Auth, and at least one endpoint per target flow. If it's stubby, re-run with `-e` or add more source docs.
4. **Do not commit the output.** `rulesbook/codegen-rust/references/**` is gitignored on purpose — generated specs are local artifacts.

## Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `grace: command not found` | venv not activated | `source .venv/bin/activate` |
| Spec is nearly empty, no errors | `FIRECRAWL_API_KEY` missing while using `-u` | Set the key in `.env` or switch to `-f` |
| `Unexpected error: API key invalid` | `AI_API_KEY` wrong / expired | Replace in `.env`; rerun |
| Hangs at `enhance_spec` | `-e` set but `ANTHROPIC_API_KEY` unreachable (and `AI_BASE_URL` not Anthropic-compatible) | Drop `-e`, or set `CLAUDE_AGENT_ENABLED=false` |
| Output written somewhere unexpected | `TECHSPEC_OUTPUT_DIR` overriding | Pass `-o` explicitly or unset env var |
| `connector` argument missing and LLM-inferred name is a sentence | LLM hallucinated | Pass the connector name explicitly |

## Next step

Once the spec looks good, switch to the `connector-service` repo and invoke the codegen rulesbook:

```
integrate <Connector> using grace/rulesbook/codegen-rust/.gracerules
```

(Or the appropriate `.gracerules_add_*` variant for incremental work.)

Optionally, before that, ask the `techspec-reviewer` subagent to audit the spec against the source docs.
