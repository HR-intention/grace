# Grace — AI-Assisted PSP Connector Toolkit

Grace is a Python CLI plus a markdown "rulesbook" plus a set of agent prompts that, together, let an AI coding agent generate **Rust payment service provider (PSP) connectors** for the sister repo `connector-service` (Juspay's UCS / Universal Connector Service).

There are **three distinct things** in this repo. Do not confuse them:

| Component | What it is | Lives in |
|---|---|---|
| **Python CLI** (`grace`) | Generates `technical_specification.md` from API docs (URLs or PDFs) via a LangGraph workflow | `src/`, `main.py`, `pyproject.toml` |
| **Rulesbook** (`.gracerules*`) | Markdown rules and pattern templates that an external AI agent reads when implementing the Rust connector | `rulesbook/codegen-rust/` |
| **Workflow agents** | Markdown prompts for multi-connector batch orchestration | `workflow/` |

The Rust connector code itself is **NOT in this repo** — it's generated into `connector-service/backend/connector-integration/src/connectors/` by an AI agent that the user invokes with one of the `.gracerules*` files.

---

## Repository layout

```
grace/
├── src/                              # Python CLI source
│   ├── cli.py                        # Click entrypoint — defines `grace techspec ...`
│   ├── config.py                     # Env-var config (AI keys, Firecrawl, etc.)
│   ├── ai/                           # LiteLLM wrapper + prompt registry
│   ├── tools/                        # Firecrawl scraper, file manager
│   ├── workflows/techspec/           # LangGraph state machine (the tech-spec pipeline)
│   │   ├── workflow.py               # Graph definition
│   │   ├── states/techspec_state.py  # TypedDict state schema
│   │   └── nodes/                    # collect_urls → crawling → llm_analysis →
│   │                                 #   [enhance_spec → field_analysis] →
│   │                                 #   [mock_server] → output
│   ├── utils/                        # PDF/DOCX extraction, validation
│   └── types/config.py               # AIConfig, TechSpecConfig, ClaudeAgentConfig
├── rulesbook/
│   ├── shared/                       # Language-neutral content
│   │   ├── flows.md                  # Authoritative flow list + prerequisite DAG
│   │   ├── payment_methods.md        # Payment-method categories + types
│   │   ├── quality_rubric.md         # Scoring formula + cross-cutting checks
│   │   ├── feedback.md               # Quality-review feedback (tagged by lang)
│   │   ├── learnings.md              # Implementation lessons (tagged by lang)
│   │   └── tech_spec_template.md     # Tech-spec template (lang-neutral)
│   └── codegen-rust/                 # Rust language pack (rulebook that AI agents read)
│       ├── .gracerules               # NEW connector from scratch (6 core flows)
│       ├── .gracerules_add_flow      # Add one flow to existing connector
│       ├── .gracerules_add_payment_method  # Add payment methods
│       ├── README.md                 # GRACE-UCS user guide
│       ├── guides/
│       │   ├── patterns/             # Rust pattern templates
│       │   ├── types/types.md        # UCS Rust type system
│       │   └── quality/              # Rust-only quality checks
│       ├── connector_integration/
│       └── references/               # Per-connector tech specs (gitignored)
├── workflow/                         # Multi-connector batch orchestration prompts
│   ├── 1_orchestrator.md             # Top-level (spawns Connector Agents sequentially)
│   ├── 2_connector.md                # One agent per connector (links→spec→codegen→PR)
│   ├── 2.1_links.md                  # Docs URL discovery
│   ├── 2.2_techspec.md               # Calls `grace techspec`
│   ├── 2.3_codegen.md                # Runs `.gracerules*`, cargo build, grpcurl test
│   └── 2.4_pr.md                     # git commit + cherry-pick + gh pr create
├── main.py                           # Thin entry — just calls src.cli:main
├── pyproject.toml                    # `grace = "src.cli:main"` script entry
├── enhacer.md                        # Prompt for -e enhancement (NOTE: typo in filename, has trailing space)
├── analysis.md                       # Historical analysis notes (not consumed at runtime)
└── extract_source_urls_simple.sh
```

The `rulesbook/` directory has two top-level children:

- `shared/` — language-neutral content used by every codegen pack (flow definitions, quality rubric, feedback/learnings)
- `codegen-<lang>/` — one directory per supported target language; each holds the `.gracerules*` triad, pattern templates, language-specific type and quality references, and a `references/` subdir for per-connector tech specs generated by `grace techspec` (gitignored)

---

## Quickstart

```bash
cd grace
uv sync                       # install deps (or: pip install uv && uv sync)
source .venv/bin/activate     # required every new shell
cp .env.example .env          # then edit .env with your AI keys
grace --help
```

### Generate a tech spec

```bash
# From local docs folder (PDFs/markdown/etc.)
grace techspec stripe -f /path/to/docs -v

# From URLs (Firecrawl-scraped)
grace techspec stripe -u urls.txt -v

# With Claude Agent SDK enhancement + field-dependency analysis
grace techspec stripe -f /path/to/docs -e -v

# With mock server generation
grace techspec stripe -f /path/to/docs -m
```

Output goes to `rulesbook/codegen-rust/references/<connector>/technical_specification.md` (or the path in `TECHSPEC_OUTPUT_DIR`).

### Target language

The `-l` / `--target-lang` flag (defaults to `python`) selects which language pack
will consume the generated tech spec. Acceptable values: `rust`, `python`.

```bash
grace techspec stripe -f ./docs --target-lang rust          # codegen-rust pack
grace techspec razorpay -f ./docs --target-lang python      # codegen-python pack (default)
```

> **Migration note:** Plan B sets the default to `python`. Users with
> existing scripts that omit `--target-lang` will now produce
> Python-targeted output. Pass `--target-lang rust` explicitly to
> preserve pre-Plan-B behavior.

When the corresponding target service repo (`connector-service/` for Rust,
`connector-service-python/` for Python) is not present as a sibling of
`grace/`, the CLI prints a loud warning rather than an orphaned next-step
hint. See [src/workflows/techspec/nodes/output_node.py](src/workflows/techspec/nodes/output_node.py) for the lookup table.

### Generate the Rust connector

After producing the tech spec, switch to the **`connector-service/` repo** and tell your AI coding agent:

```
integrate Stripe using grace/rulesbook/codegen-rust/.gracerules
```

(Or `.gracerules_add_flow` / `.gracerules_add_payment_method` for incremental work.) The AI agent reads the rulesbook, implements the connector in Rust, and verifies with `cargo build`.

---

## Architecture: the TechSpec LangGraph

Defined in [src/workflows/techspec/workflow.py](src/workflows/techspec/workflow.py).

```
START
  ├─ (folder given?) ─► llm_analysis
  └─ (no folder)    ─► collect_urls ─► crawling ─► llm_analysis
                                                       │
                              ┌─(enhance flag)─► enhance_spec ─► field_analysis ─┐
                              │                                                    │
                              └─────────────────────────────────────────────────► (mock_server flag?) ─► output ─► END
```

- **State**: `TechspecWorkflowState` TypedDict in [src/workflows/techspec/states/techspec_state.py](src/workflows/techspec/states/techspec_state.py).
- **Errors are accumulated, not raised** — check `state["errors"]` and `state["error"]` after run.
- **Conditional edges** are private methods on `TechspecWorkflow` (e.g., `_should_continue_after_llm`).
- **All nodes are sync functions taking & returning state**, except `mock_server` which is async (wrapped via `asyncio.run` in the graph node lambda).

### AI layer

[src/ai/ai_service.py](src/ai/ai_service.py) wraps **LiteLLM** (provider-agnostic). Default provider is GRID (`AI_BASE_URL=https://grid.ai.juspay.net`, model `openai/qwen3-coder-480b`); OpenAI and Anthropic also work.

- Prompts live in `src/ai/prompts/` and are loaded by [src/ai/system/prompt_config.py](src/ai/system/prompt_config.py) (YAML registry, `{placeholder}` substitution via `str.replace`).
- Large docs are chunked at ~80k tokens; if the merged result is too long, chunks are concatenated instead.
- **Claude Agent SDK** is only used in the `enhance_spec` node when `-e` is set. It reads [enhacer.md ](enhacer.md ) (filename has a trailing space — yes, really) as its system prompt.

### Tools

- [src/tools/firecrawl/firecrawl.py](src/tools/firecrawl/firecrawl.py) — Firecrawl API wrapper for URL → markdown.
- [src/tools/filemanager/filemanager.py](src/tools/filemanager/filemanager.py) — local file I/O + PDF/DOCX extraction.

---

## Rulesbook: how the AI agent writes Rust

The rulesbook is **read by an external AI coding agent** (Cursor / Claude Code / Windsurf) opened on the `connector-service` repo. The Python CLI does not consume it.

Three entrypoints, invoked in plain English commands:

| File | Command form | Used for |
|---|---|---|
| `.gracerules` | `integrate <Connector> using grace/rulesbook/codegen-rust/.gracerules` | New connector from scratch — implements 6 core flows (Authorize, PSync, Capture, Refund, RSync, Void) |
| `.gracerules_add_flow` | `add <Flow> flow to <Connector> using grace/rulesbook/codegen-rust/.gracerules_add_flow` | Add one or more flows incrementally |
| `.gracerules_add_payment_method` | `add <Category>:<PM1>,<PM2> to <Connector> using grace/rulesbook/codegen-rust/.gracerules_add_payment_method` | Add payment methods (e.g., `Wallet:Apple Pay,Google Pay`) |

**Supported flows**: Authorize, Capture, Refund, Void, PSync, RSync, SetupMandate, RepeatPayment, IncomingWebhook, CreateOrder, SessionToken, PaymentMethodToken, DefendDispute, AcceptDispute, DSync, MandateRevoke, IncrementalAuthorization, VoidPC. One pattern file per flow under `rulesbook/codegen-rust/guides/patterns/`.

**Supported payment-method categories**: Card, Wallet, BankTransfer, BankDebit, BankRedirect, UPI, BNPL, Crypto, GiftCard, MobilePayment, Reward.

**Quality Guardian**: a subagent inside the rulesbook scores each implementation (formula in `guides/quality/`). Score must be **≥ 60** to be approved. Critical issues = −20 each; warnings = −5; suggestions = −1.

---

## Multi-connector batch workflow (`workflow/`)

For implementing one flow across many connectors in a single run. **Operates on the `connector-service` repo**, not this one (except for `grace techspec` calls).

Invocation pattern:
```
Implement {FLOW} for all connectors in {CONNECTORS_FILE}. Read grace/workflow/1_orchestrator.md and follow it exactly.
Branch: {BRANCH}
LANG: <target language: rust or python>
```

The orchestrator and every per-connector subagent (`2_connector.md`, `2.2_techspec.md`, `2.3_codegen.md`, `2.4_pr.md`) take a `{LANG}` input variable (default `python`) and thread it through to `grace techspec --target-lang {LANG}` and to the language-specific codegen rulesbook.

Hard constraints baked into the prompts:
- **STRICTLY SEQUENTIAL** — one Task call per orchestrator message. Parallel agents on the shared `{BRANCH}` corrupt git state.
- **No `cargo test`** — testing is via `grpcurl` only.
- **No retries without a code change** — looping the same test produces the same error.
- **Build → grpcurl → commit** is a hard gate.
- **Credentials in `creds.json`** at `connector-service` root; missing entry = silently SKIPPED.
- The orchestrator (`1_orchestrator.md`) ONLY spawns Connector Agents (`2_connector.md`). The Connector Agent spawns Links / TechSpec / Codegen / PR subagents. Each agent reads its own file; the parent never inlines the content.

If you edit `workflow/*.md`, preserve these guardrails — they exist because past parallel runs corrupted branches.

---

## Common commands

```bash
# CLI
grace techspec <connector> [-f docs/ | -u urls.txt] [-o out/] [-l rust|python] [-e] [-m] [-v] [--test-only]

# Lint / format / type-check (config in pyproject.toml; no pre-commit hook installed)
black src/                            # line-length 100, py39-py312
mypy src/                             # check_untyped_defs=true, warn_return_any=true
flake8 src/

# Tests (no test suite currently checked in)
pytest                                # markers: unit, integration, workflow, slow
```

There is **no CI workflow** in `.github/workflows/` and **no pre-commit hooks** are enforced. Run linters manually.

---

## Environment variables

See [.env.example](.env.example). Loaded from (in precedence order, see [src/config.py:22](src/config.py:22)):
1. Explicit `env_file` argument
2. `.env` in cwd
3. `.env` in `grace/` directory
4. `.env` in parent (project root)

| Var | Used for | Default |
|---|---|---|
| `AI_API_KEY` | LiteLLM auth — **required** | — |
| `AI_BASE_URL` | LLM endpoint | `https://grid.ai.juspay.net` |
| `AI_MODEL_ID` | Spec generation model | `openai/qwen3-coder-480b` |
| `AI_VISION_MODEL_ID` | Vision tasks | `openai/glm-46-fp8` |
| `AI_MAX_TOKENS` / `AI_TEMPERATURE` | Sampling | `32768` / `0.7` |
| `FIRECRAWL_API_KEY` | Required for `-u` URL scraping | — |
| `ANTHROPIC_API_KEY` | Claude Agent SDK (`-e`). Falls back to `AI_API_KEY` | — |
| `CLAUDE_AGENT_ENABLED` | Disable `-e` even with key set | `true` |
| `CLAUDE_AGENT_MAX_TURNS` | Cap on enhancer turns | `25` |
| `TECHSPEC_OUTPUT_DIR` | Output directory | `./output` |
| `LOG_LEVEL` / `LOG_FILE` / `DEBUG` | Logging | `INFO` / `grace.log` / `false` |

---

## Conventions & gotchas

1. **`enhacer.md` (with trailing space) is intentionally that filename** — it's referenced by string and shipped in the repo. Do not "fix" it without also updating the references.
2. **`rulesbook/codegen-rust/references/**` is gitignored.** Generated tech specs are local artifacts. Don't commit them.
3. **The CLI is invoked from `grace/` with `.venv` activated.** Workflow agents that call it always `source .venv/bin/activate` first — preserve this when editing them.
4. **One subcommand only**: `grace techspec`. The README's "Other Commands" section refers to AI-agent prompt commands (read by the rulesbook), not CLI subcommands.
5. **Config is a singleton** ([src/config.py:117](src/config.py:117)). `get_config()` caches; use `reload_config()` to pick up env changes.
6. **No URL scraping without `FIRECRAWL_API_KEY`** — missing key silently produces empty markdown files and the LLM analysis gets no input.
7. **Connector-name casing matters**: workflow agents use original casing for `grace techspec` (`Adyen`) and lowercase for branches/paths (`adyen`).
8. **Pattern files are mutable templates, not specs.** Adding a new flow means adding a `pattern_<flow>.md` under `rulesbook/codegen-rust/guides/patterns/` and referencing it from the relevant `.gracerules*` file.
9. **Don't run `cargo test`** when working in `connector-service` via these workflows — all testing is `grpcurl`-based by design.
10. **The Quality Guardian's `feedback.md`** is append-only institutional memory. New review findings belong there; do not edit historical entries.

---

## Where to look first

| If you're… | Read |
|---|---|
| Adding a new CLI flag | [src/cli.py:29](src/cli.py:29) → thread through to `run_techspec_workflow` |
| Adding a new pipeline stage | [src/workflows/techspec/workflow.py](src/workflows/techspec/workflow.py) + new file in `nodes/` + extend `TechspecWorkflowState` |
| Tuning the spec prompt | [src/ai/prompts/](src/ai/prompts/) (loaded by [src/ai/system/prompt_config.py](src/ai/system/prompt_config.py)) |
| Adding a new flow pattern | Create `rulesbook/codegen-rust/guides/patterns/pattern_<flow>.md`, reference it from `.gracerules*` |
| Adding a new payment-method pattern | Create `rulesbook/codegen-rust/guides/patterns/authorize/<pm>/pattern_authorize_<pm>.md` |
| Debugging a failing connector run | Check `grace.log`, then re-run with `-v`. Inspect `state["errors"]` accumulation in the relevant node |
| Tweaking batch orchestration | `workflow/1_orchestrator.md` (top-level) or `workflow/2_*.md` (per-connector subagents) |

---

## What this repo is NOT

- **Not the Rust connector code** — that lives in [juspay/connector-service](https://github.com/juspay/connector-service).
- **Not an LLM provider** — Grace orchestrates calls to whatever LLM you configure via LiteLLM.
- **Not a test framework** — generated connectors are validated externally via `cargo build` and `grpcurl`.
