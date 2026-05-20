# Legacy

Artifacts from earlier iterations of Grace, kept for historical context. **Nothing in this directory is wired into the v1 pipeline.** Delete freely if you're certain you won't want to reference any of it.

## Contents

| File | Era | What it was | Why it's not in v1 |
|---|---|---|---|
| `analysis.md` | Rust workflow | 769-line "API field dependency analysis" rule set for tracing field origins across multi-call flows (authorize → capture → refund). | Useful conceptual frame, but the load-bearing parts are absorbed into `rulesbook/codegen/python/pitfalls.md §4a` (field-name reference) and `rulesbook/codegen/python/testing.md §5` (mock-response vs request-input assertions). |
| `enhacer.md` | Rust workflow | System prompt for an AI agent that reads PSP doc files and incrementally builds a `technical_specification.md` intermediate. | v1 pipeline deliberately has no tech-spec intermediate (sub-project spec §3.1: "three steps, not five"). Claude reads the rulebook + the snapshotted docs directly. |
| `extract_source_urls_simple.sh` | Rust workflow | Bash script that greps `Source URL:` annotations from a tree of markdown files and writes per-PSP URL files into `connector-service/urls/`. | Tied to the discontinued `output/markdown/` layout and the `connector-service/` consumer. `grace fetch-docs` solves the same problem differently (snapshots docs into `connector_docs/<psp>/`). |
| `main.py` | Rust workflow | `from src.cli import main` shim — broken since Step 3.1 deleted `src/cli.py` and moved the CLI to `src/grace/cli.py`. | The current entry point is `[project.scripts] grace = "grace.cli:main"` in `pyproject.toml`. |
| `setup.md` | Rust workflow | Setup guide referencing "AI API key" + "Cursor/Claude Code/Windsurf" as alternative AI agents. | Pre-dates the v0.2 lock-in of Claude Code as the single AI backend. The current README leads with `claude setup-token` + `CLAUDE_CODE_OAUTH_TOKEN`. |
| `workflow/` | Rust workflow | LangGraph multi-step orchestrator docs (`1_orchestrator.md`, `2.1_links.md`, `2.2_techspec.md`, `2.3_codegen.md`, `2.4_pr.md`, `2_connector.md`). | v1 pipeline collapsed these into the three steps in `grace.pipeline.orchestrate`: context → invoke → gates. No multi-step orchestrator. |

## If you want to revive any of these

- **`analysis.md`** — the field-dependency mental model is genuinely useful for understanding cross-call field flow. If you ever need to teach an AI agent how to trace `psp_payment_id` from a sync_payment response back to a refund request, this is a starting point. Distill to a 1-2 page guide before adding to the rulebook.
- **`enhacer.md`** — the "systematic per-file enrichment" pattern is sound. If you ever want a `grace tech-spec` pre-step (distill PSP docs before generation), this is the prompt scaffold.
- **`extract_source_urls_simple.sh`** — nothing reusable. Snapshots in `connector_docs/<psp>/` already pin sources.
- **`main.py`** / **`setup.md`** / **`workflow/`** — pure historical artifacts; the current pipeline replaces them entirely.
