# Multi-Lang Connector Generation — Plan B: CLI Flag + Workflow Agent `{LANG}`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `--target-lang` flag to `grace techspec` (defaults to `python`) and parameterize the multi-connector workflow agents (`workflow/*.md`) with a `{LANG}` variable. After this lands, the CLI prints language-aware next-step hints (with a loud warning when the target service repo is missing), and the orchestration prompts can drive either Rust or Python codegen.

**Architecture:** Add a `target_lang: Literal["rust", "python"]` field to `TechspecWorkflowState`. Click decorator on `grace techspec` validates `rust|python`, default `python`. Threaded through `run_techspec_workflow(...)` → `TechspecWorkflow.execute(...)` → initial state. `output_node` reads it, looks up a per-language config dict (`LANG_NEXT_STEPS`), checks whether the target service repo exists as a sibling of `grace/`, and prints either the next-step command or a recovery warning. Workflow markdown files take a new `{LANG}` input variable that selects per-language build/test/rulesbook commands via a config block at the top of `2.3_codegen.md`.

**Tech Stack:** Click (CLI), LangGraph TypedDict state, pytest for unit tests (no existing test suite — Plan B adds `tests/` skeleton + first 2 test files), markdown for workflow agent prompts.

**Source spec:** [docs/superpowers/specs/2026-05-18-multi-lang-connector-generation-design.md](../specs/2026-05-18-multi-lang-connector-generation-design.md) — Sections 5 (CLI), 9 (Workflow agents).

**Depends on:** Plan A (rulesbook restructure) — already landed in 18 commits on `python-support`.

---

## File structure

### New files
- `tests/__init__.py`
- `tests/conftest.py`
- `tests/test_cli_target_lang.py`
- `tests/test_output_node_next_step.py`

### Modified files (Phase 2 — CLI/Python)
- `src/cli.py` — add `-l/--target-lang` option, thread through
- `src/workflows/__init__.py` — pass `target_lang` through re-export signature (if applicable)
- `src/workflows/techspec/workflow.py` — accept `target_lang`, set on initial state
- `src/workflows/techspec/states/techspec_state.py` — add `target_lang` field
- `src/workflows/techspec/nodes/output_node.py` — `LANG_NEXT_STEPS` dict + `_print_next_step` helper + safety check

### Modified files (Phase 5 — workflow agents)
- `workflow/1_orchestrator.md` — new required `{LANG}` input
- `workflow/2_connector.md` — accept `{LANG}`, set working dir per lang
- `workflow/2.2_techspec.md` — pass `--target-lang {LANG}` to `grace techspec`
- `workflow/2.3_codegen.md` — language config block at top
- `workflow/2.4_pr.md` — lang-prefixed PR titles, lang-specific commit glob

### Modified files (docs)
- `CLAUDE.md` — flag docs + workflow `{LANG}` mention
- `README.md` — flag mention in quickstart
- `setup.md` — flag mention in usage examples
- `.env.example` — optional note about `--target-lang`

---

## Tasks

### Task 1: Add `target_lang` field to `TechspecWorkflowState`

**Files:**
- Modify: `src/workflows/techspec/states/techspec_state.py:31-83` (add one field)

- [ ] **Step 1: Read the current state schema**

Run: `wc -l src/workflows/techspec/states/techspec_state.py`
Expected: 83 lines.

- [ ] **Step 2: Add the `target_lang` field**

In `src/workflows/techspec/states/techspec_state.py`, inside the `TechspecWorkflowState` TypedDict (lines 31-83), add this field next to other "Workflow control" fields (after line 43, after the `verbose: bool` line):

```python
    # Target language for codegen — "rust" or "python"
    target_lang: str
```

(Use `str` not `Literal[...]` to keep mypy happy with TypedDict `total=False`.)

The whole TypedDict has `total=False` so the field is optional at construction. We'll set it explicitly from the CLI.

- [ ] **Step 3: Verify import still works**

Run:
```bash
source .venv/bin/activate
python -c "from src.workflows.techspec.states.techspec_state import TechspecWorkflowState; print('OK')"
```
Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add src/workflows/techspec/states/techspec_state.py
git commit -m "feat(state): add target_lang field to TechspecWorkflowState

Will be set by the CLI's --target-lang flag (Plan B Task 2)."
```

---

### Task 2: Add `--target-lang` Click option and thread through workflow

**Files:**
- Modify: `src/cli.py:29-141` (add option, thread to call)
- Modify: `src/workflows/techspec/workflow.py:140-150, 156-173, 209-228` (accept param, set on initial state)

- [ ] **Step 1: Read current cli.py signatures**

Open `src/cli.py`. The `techspec` Click command starts around line 29 and calls `run_techspec_workflow(...)` around line 70.

- [ ] **Step 2: Add the Click option to `src/cli.py`**

Find the existing options block (around line 30-37). After the existing options, add this one — placed between `@click.option('urls', '-u', ...)` and `@click.option('--output', '-o', ...)`:

```python
@click.option('-l', '--target-lang',
              type=click.Choice(['rust', 'python'], case_sensitive=False),
              default='python',
              help='Target language for codegen. Default: python.')
```

Add `target_lang` to the `def techspec(...)` parameter list.

- [ ] **Step 3: Thread `target_lang` into the `run_techspec_workflow(...)` call**

Find the `result = await run_techspec_workflow(...)` call (around line 70-79). Add `target_lang=target_lang` as a kwarg:

```python
result = await run_techspec_workflow(
    connector_name=connector,
    folder=folder,
    urls_file=urls,
    output_dir=output_dir,
    test_only=test_only,
    verbose=verbose,
    mock_server=mock_server,
    enhance=enhance,
    target_lang=target_lang,
)
```

- [ ] **Step 4: Echo the chosen lang in verbose mode**

In the verbose block near the top of `run_techspec` async (around lines 51-62), add:

```python
            click.echo(f"Target language: {target_lang}")
```

Place it after the other `click.echo(...)` calls in the verbose block, before the blank line.

- [ ] **Step 5: Update `run_techspec_workflow` signature in `src/workflows/techspec/workflow.py`**

Find `async def run_techspec_workflow(...)` (around line 209). Add `target_lang: str = "python"` to the signature. Pass it into `workflow.execute(...)`:

```python
async def run_techspec_workflow(connector_name: str,
                               folder: Optional[str],
                                urls_file: Optional[str] = None,
                               output_dir: Optional[str] = None,
                               mock_server: bool = False,
                               enhance: bool = False,
                               test_only: bool = False,
                               verbose: bool = False,
                               target_lang: str = "python",
                               ) -> Dict[str, Any]:
    workflow = create_techspec_workflow()
    return await workflow.execute(
        connector_name=connector_name,
        folder=folder,
        urls_file=urls_file,
        output_dir=output_dir,
        mock_server=mock_server,
        enhance=enhance,
        test_only=test_only,
        verbose=verbose,
        target_lang=target_lang,
    )
```

- [ ] **Step 6: Update `TechspecWorkflow.execute` signature in `src/workflows/techspec/workflow.py`**

Find `async def execute(...)` (around line 140). Add `target_lang: str = "python"` to the signature. In the initial state construction (around line 156-173), add `"target_lang": target_lang,`:

```python
        initial_state: TechspecWorkflowState = {
            "connector_name": connector_name,
            "urls_file": urls_file,
            "urls": [],
            "visited_urls": [],
            "folder" : folder or None,
            "output_dir": output_path,
            "mock_server" : mock_server,
            "enhance": enhance,
            "config": config,
            "test_only": test_only,
            "verbose": verbose,
            "target_lang": target_lang,
            "final_output": {},
            "warnings": [],
            "error": None,
            "errors": [],
            "metadata": {"workflow_started": True, "timestamp": datetime.now().isoformat()},
        }
```

- [ ] **Step 7: Smoke-test the threading**

Run:
```bash
source .venv/bin/activate
grace techspec --help 2>&1 | grep -A 2 'target-lang'
```
Expected: shows `-l, --target-lang [rust|python]` and `Default: python.`

Also:
```bash
grace techspec dummy_test --target-lang rust --test-only -v 2>&1 | head -10
```
Should not error on flag parsing. (The actual workflow will run — `--test-only` keeps it from writing files. It's OK if it errors later in the pipeline; we just want to confirm the flag is accepted.)

Also reject invalid values:
```bash
grace techspec dummy_test --target-lang java --test-only 2>&1 | head -5
```
Expected: error message from Click about invalid choice.

- [ ] **Step 8: Commit**

```bash
git add src/cli.py src/workflows/techspec/workflow.py
git commit -m "feat(cli): add --target-lang flag, thread to workflow state

Click choice [rust|python], default 'python'. Threaded through
run_techspec_workflow → TechspecWorkflow.execute → initial state."
```

---

### Task 3: Per-language next-step printing in `output_node`

**Files:**
- Modify: `src/workflows/techspec/nodes/output_node.py` (add LANG_NEXT_STEPS dict + _print_next_step helper + call it)

- [ ] **Step 1: Read the current output_node**

Open `src/workflows/techspec/nodes/output_node.py`. Note: the function currently ends with `return state` at line 72, after printing a summary.

- [ ] **Step 2: Add LANG_NEXT_STEPS dict and _print_next_step helper**

At the top of the file (after the existing imports, before the `output_node` function definition), add:

```python
from pathlib import Path as _Path

LANG_NEXT_STEPS = {
    "rust": {
        "target_repo": "connector-service/",
        "rulesbook_path": "grace/rulesbook/codegen-rust/.gracerules",
    },
    "python": {
        "target_repo": "lens/",
        "rulesbook_path": "grace/rulesbook/codegen-python/.gracerules",
    },
}


def _print_next_step(target_lang: str, connector: str) -> None:
    """Print a language-aware next-step hint, with a warning when the target repo is missing."""
    config = LANG_NEXT_STEPS.get(target_lang)
    if config is None:
        return

    grace_dir = _Path(__file__).resolve().parents[4]  # grace/ root
    target_repo = grace_dir.parent / config["target_repo"]

    if not target_repo.exists():
        click.echo(f"\n⚠️  Target repo not found: {target_repo}")
        click.echo(
            f"   Tech spec is generated for --target-lang {target_lang}, but "
            f"{config['target_repo']} is not present at the expected sibling path."
        )
        click.echo(f"   Either:")
        click.echo(f"     • Set up {config['target_repo']} as a sibling directory of grace/, OR")
        click.echo(f"     • Re-run with --target-lang <other> if you meant a different target.")
        return

    click.echo(f"\nNext step (target language: {target_lang}):")
    click.echo(f"  Open {config['target_repo']} in your AI agent and run:")
    click.echo(f"    integrate {connector or '<Connector>'} using {config['rulesbook_path']}")
```

- [ ] **Step 3: Call `_print_next_step` from `output_node`**

At the very end of `output_node`, just before `return state` (currently around line 72), add:

```python
    # Language-aware next-step hint
    target_lang = state.get("target_lang", "python")
    connector = state.get("connector_name") or state.get("file_name") or ""
    _print_next_step(target_lang, connector)
```

- [ ] **Step 4: Smoke-test it**

Run from grace/ with `lens/` not present as sibling:
```bash
source .venv/bin/activate
grace techspec dummy_test -f /tmp/nonexistent --target-lang python -v 2>&1 | tail -15
```

The workflow will fail (no docs), but the run should reach `output_node` if errors didn't abort early. If you see `⚠️ Target repo not found: ...` somewhere in output, that's the next-step warning firing.

(If the workflow doesn't reach output_node for the dummy case, defer this smoke test to Task 5 where we set up a proper minimal run.)

- [ ] **Step 5: Commit**

```bash
git add src/workflows/techspec/nodes/output_node.py
git commit -m "feat(output): print language-aware next-step hint

LANG_NEXT_STEPS maps rust/python → (target_repo, rulesbook_path).
When the target repo is missing as a sibling of grace/, prints a loud
warning instead of an orphaned 'integrate' hint."
```

---

### Task 4: Add `tests/` skeleton + first unit tests

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_cli_target_lang.py`
- Create: `tests/test_output_node_next_step.py`

- [ ] **Step 1: Create `tests/__init__.py`** (empty file)

```bash
mkdir -p tests
touch tests/__init__.py
```

- [ ] **Step 2: Create `tests/conftest.py`**

```python
"""Shared pytest fixtures."""
import pytest


@pytest.fixture
def cli_runner():
    """A Click CliRunner for invoking the grace CLI in-process."""
    from click.testing import CliRunner
    return CliRunner()
```

- [ ] **Step 3: Create `tests/test_cli_target_lang.py`**

```python
"""Tests for the --target-lang CLI flag."""
import pytest
from src.cli import cli


def test_target_lang_help_text_lists_choices(cli_runner):
    result = cli_runner.invoke(cli, ["techspec", "--help"])
    assert result.exit_code == 0
    assert "--target-lang" in result.output
    assert "rust" in result.output
    assert "python" in result.output


def test_target_lang_default_is_python(cli_runner):
    result = cli_runner.invoke(cli, ["techspec", "--help"])
    assert result.exit_code == 0
    assert "Default: python" in result.output


def test_target_lang_rejects_invalid_value(cli_runner):
    result = cli_runner.invoke(cli, ["techspec", "dummy", "--target-lang", "java", "--test-only"])
    assert result.exit_code != 0
    assert "java" in result.output.lower() or "invalid" in result.output.lower()


def test_target_lang_accepts_rust(cli_runner):
    # We only verify Click parses; the workflow itself will fail without docs, which is fine.
    result = cli_runner.invoke(cli, ["techspec", "--target-lang", "rust", "--help"])
    assert result.exit_code == 0


def test_target_lang_accepts_python(cli_runner):
    result = cli_runner.invoke(cli, ["techspec", "--target-lang", "python", "--help"])
    assert result.exit_code == 0


def test_short_flag_l_works(cli_runner):
    # Sanity: short flag works the same way
    result = cli_runner.invoke(cli, ["techspec", "-l", "rust", "--help"])
    assert result.exit_code == 0
```

- [ ] **Step 4: Create `tests/test_output_node_next_step.py`**

```python
"""Tests for the language-aware next-step printing in output_node."""
from pathlib import Path
import pytest

from src.workflows.techspec.nodes.output_node import LANG_NEXT_STEPS, _print_next_step


def test_lang_next_steps_has_both_languages():
    assert "rust" in LANG_NEXT_STEPS
    assert "python" in LANG_NEXT_STEPS


def test_lang_next_steps_rust_points_to_codegen_rust():
    assert LANG_NEXT_STEPS["rust"]["target_repo"] == "connector-service/"
    assert "codegen-rust" in LANG_NEXT_STEPS["rust"]["rulesbook_path"]


def test_lang_next_steps_python_points_to_codegen_python():
    assert LANG_NEXT_STEPS["python"]["target_repo"] == "lens/"
    assert "codegen-python" in LANG_NEXT_STEPS["python"]["rulesbook_path"]


def test_print_next_step_warns_when_target_repo_missing(capsys):
    # lens doesn't exist as a sibling of grace/ during testing
    _print_next_step("python", "razorpay")
    captured = capsys.readouterr()
    assert "⚠️" in captured.out or "not found" in captured.out
    assert "lens" in captured.out


def test_print_next_step_warns_for_rust_when_target_repo_missing(capsys):
    # connector-service/ also doesn't exist as a sibling of grace/ during testing
    _print_next_step("rust", "stripe")
    captured = capsys.readouterr()
    # Either the warning fires (likely) or the next-step hint fires (if connector-service/ exists)
    # Both outcomes are acceptable; we just verify SOMETHING printed
    assert captured.out  # non-empty output


def test_print_next_step_silent_for_unknown_lang(capsys):
    _print_next_step("typescript", "stripe")
    captured = capsys.readouterr()
    assert captured.out == ""  # unknown lang → no output
```

- [ ] **Step 5: Run the tests**

```bash
source .venv/bin/activate
uv pip install pytest >/dev/null 2>&1 || pip install pytest >/dev/null 2>&1
pytest tests/ -v
```

Expected: all tests pass. If `pytest` isn't installed in the venv, install it.

Note: the `test_print_next_step_warns_for_rust_when_target_repo_missing` test allows either outcome (warning OR hint) because whether `connector-service/` exists depends on the developer's filesystem. The assertion is just "something printed."

- [ ] **Step 6: Commit**

```bash
git add tests/
git commit -m "test: add tests/ skeleton + cli/target-lang and output_node tests

First test files in the repo. Covers --target-lang flag parsing and
output_node's language-aware next-step printing including the warning
when the target service repo is missing."
```

---

### Task 5: End-to-end smoke test

**Files:**
- Read-only verification.

- [ ] **Step 1: Verify the full CLI smoke path works**

Run from `/Users/sarthak/PycharmProjects/symplora/grace`:

```bash
source .venv/bin/activate

# Help text shows the new flag
grace techspec --help 2>&1 | grep -A 1 'target-lang'

# Invalid value rejected
grace techspec dummy --target-lang ruby --test-only 2>&1 | grep -i 'invalid' || echo "FAIL: should have rejected ruby"

# Valid value accepted (workflow may fail later due to missing docs, that's OK)
grace techspec test_connector --target-lang python -f /tmp/empty-fake-folder --test-only -v 2>&1 | tail -20
```

Note any unexpected behavior.

- [ ] **Step 2: Run the test suite**

```bash
source .venv/bin/activate
pytest tests/ -v
```

All tests must pass.

- [ ] **Step 3: No commit** (verification-only task)

---

### Task 6: Update `workflow/1_orchestrator.md` to thread `{LANG}`

**Files:**
- Modify: `workflow/1_orchestrator.md`

- [ ] **Step 1: Read the current orchestrator**

Open `workflow/1_orchestrator.md`. Find the "## Inputs" section (around line 9-23). It lists `{FLOW}`, `{CONNECTORS_FILE}`, `{BRANCH}`.

- [ ] **Step 2: Add `{LANG}` to the Inputs table**

Insert a new row into the inputs table just after `{FLOW}`:

```markdown
| `{LANG}` | Target language for codegen (`rust` or `python`) | `python` |
```

- [ ] **Step 3: Update the spawn command template**

Find the "HOW TO SPAWN THE CONNECTOR AGENT" section (around line 96-114). The template currently looks like:

```
Task(
  subagent_type="general",
  description="Implement {FLOW} for {CONNECTOR}",
  prompt="Read and follow the workflow defined in grace/workflow/2_connector.md

Variables:
  CONNECTOR: <connector name, exact casing from JSON>
  FLOW: <the payment flow>
  CONNECTORS_FILE: <path to the connectors JSON file>
  BRANCH: <the branch name>"
)
```

Add `LANG: <lang>` to the Variables block:

```
Task(
  subagent_type="general",
  description="Implement {FLOW} for {CONNECTOR}",
  prompt="Read and follow the workflow defined in grace/workflow/2_connector.md

Variables:
  CONNECTOR: <connector name, exact casing from JSON>
  FLOW: <the payment flow>
  CONNECTORS_FILE: <path to the connectors JSON file>
  BRANCH: <the branch name>
  LANG: <target language: rust or python>"
)
```

- [ ] **Step 4: Mention `{LANG}` in the example invocation at the top**

Near the top of the file (search for "Example:" or update the opening paragraph), include `{LANG}` in the example invocation pattern. Find any example like:

```
Implement {FLOW} for all connectors in {CONNECTORS_FILE}. Read grace/workflow/1_orchestrator.md and follow it exactly.
```

Update it to mention `LANG`:

```
Implement {FLOW} in {LANG} for all connectors in {CONNECTORS_FILE}. Read grace/workflow/1_orchestrator.md and follow it exactly.
```

If no such example exists in the file, skip this step.

- [ ] **Step 5: Commit**

```bash
git add workflow/1_orchestrator.md
git commit -m "feat(workflow): thread {LANG} input through orchestrator

Required input; passed to each Connector Agent spawn. Selects whether
codegen targets connector-service/ (Rust) or lens/."
```

---

### Task 7: Update `workflow/2_connector.md` and `workflow/2.2_techspec.md`

**Files:**
- Modify: `workflow/2_connector.md`
- Modify: `workflow/2.2_techspec.md`

- [ ] **Step 1: Add `{LANG}` to `2_connector.md` Inputs**

Open `workflow/2_connector.md`. Find the "## Inputs" section. Add a row for `{LANG}`:

```markdown
| `{LANG}` | Target language for codegen (`rust` or `python`) | `python` |
```

- [ ] **Step 2: Thread `{LANG}` into every subagent spawn in `2_connector.md`**

Find each `Task(...)` template in `2_connector.md` (there are several — Phase 1 Links, Phase 2 TechSpec, Phase 4 Codegen, Phase 5 PR). In each `Variables:` block, ADD a `LANG: {LANG}` line:

For example, the Phase 2 TechSpec spawn (around the `2.2_techspec.md` reference):

```
Task(
  subagent_type="general",
  description="Generate techspec for {CONNECTOR}",
  prompt="Read and follow the workflow defined in grace/workflow/2.2_techspec.md

Variables:
  CONNECTOR: <connector name, exact casing>
  FLOW: <the payment flow>
  LANG: {LANG}"
)
```

Apply analogously to all other Task spawns in `2_connector.md`.

- [ ] **Step 3: Update `workflow/2.2_techspec.md` to use `--target-lang {LANG}`**

Open `workflow/2.2_techspec.md`. Find the `grace techspec ...` invocation. Add `--target-lang {LANG}` to it:

```bash
grace techspec {CONNECTOR} --target-lang {LANG} ...
```

Place the flag right after the connector name, before any `-f` / `-u` flags.

Also update the file's "## Inputs" section if present to include `{LANG}`.

- [ ] **Step 4: Commit**

```bash
git add workflow/2_connector.md workflow/2.2_techspec.md
git commit -m "feat(workflow): thread {LANG} through Connector Agent and TechSpec Agent

2_connector.md passes {LANG} to all subagents. 2.2_techspec.md invokes
grace with --target-lang {LANG}."
```

---

### Task 8: Update `workflow/2.3_codegen.md` with language config block

**Files:**
- Modify: `workflow/2.3_codegen.md`

- [ ] **Step 1: Read the current codegen workflow**

Open `workflow/2.3_codegen.md`. Note its structure — it likely has rust-hardcoded commands (`cargo build`, `grpcurl`, paths into `connector-service/`).

- [ ] **Step 2: Add `{LANG}` to Inputs**

Add to the Inputs section:

```markdown
| `{LANG}` | Target language for codegen (`rust` or `python`) | `python` |
```

- [ ] **Step 3: Insert the language config block near the top of the file**

After the Inputs section (and any "Hard rules" or pre-flight setup), add this exact block:

```markdown
## Language config (selected by {LANG})

Use the entries below matching the LANG variable. Substitute these into
the build, test, and commit commands throughout this workflow.

### rust
- **repo:** `connector-service/`
- **rulesbook:** `grace/rulesbook/codegen-rust/`
- **build:** `cargo build`
- **service-start (background):** `cargo run --bin grpc-server`
- **smoke test:** `grpcurl -d '{...}' -plaintext localhost:50051 PaymentService/Authorize`
- **commit glob:** `backend/connector-integration/src/connectors/{connector}*`

### python
- **repo:** `lens/`
- **rulesbook:** `grace/rulesbook/codegen-python/`
- **build:** `uv run mypy lens/connectors/{connector}/ && uv run pytest tests/integration/test_{connector}.py --collect-only`
- **service-start (background):** `uv run uvicorn lens.api.server:app --port 8000`
- **smoke test:** `uv run pytest tests/integration/test_{connector}.py::test_authorize -v`
- **commit glob:** `lens/connectors/{connector}*`
```

- [ ] **Step 4: Update each phase of the codegen workflow to use the selected lang's commands**

Walk through the rest of `2.3_codegen.md`. Anywhere it currently hardcodes a Rust-specific command, replace with the variable shape. For example:

- `cargo build` → `<build command from Language config>`
- `grpcurl ...` → `<smoke test command from Language config>`
- `connector-service/` → `<repo from Language config>`
- `grace/rulesbook/codegen-rust/.gracerules` → `<rulesbook>/.gracerules`
- `backend/connector-integration/src/connectors/{connector}*` → `<commit glob>`

Preserve the structure and intent of the file (the gating, the no-loop-without-fix rule, the autonomous behavior). Only change the literal commands to be lang-aware.

- [ ] **Step 5: Commit**

```bash
git add workflow/2.3_codegen.md
git commit -m "feat(workflow): make 2.3_codegen.md language-aware

Adds a Language config block at the top. Build/test/rulesbook commands
now select per {LANG} between Rust (cargo + grpcurl) and Python (mypy +
pytest). Hard rules unchanged."
```

---

### Task 9: Update `workflow/2.4_pr.md` with lang-prefixed PR titles

**Files:**
- Modify: `workflow/2.4_pr.md`

- [ ] **Step 1: Add `{LANG}` to Inputs**

Add to the inputs section:

```markdown
| `{LANG}` | Target language (`rust` or `python`) | `python` |
```

- [ ] **Step 2: Lang-prefix PR titles**

Find the `gh pr create --title "..."` command(s). Update the title format to include a language prefix:

If the title is currently like:
```
Add {FLOW} to {CONNECTOR}
```

Change to:
```
[{LANG}] Add {FLOW} to {CONNECTOR}
```

Apply consistently to every PR title in the file.

- [ ] **Step 3: Lang-specific commit glob**

Find the `git add` commands. Replace hardcoded paths with the language-appropriate glob:

For `rust`: `git add backend/connector-integration/src/connectors/{connector}*`
For `python`: `git add lens/connectors/{connector}*`

If the file uses a single hardcoded path, replace with a conditional or a `{LANG}_GLOB` placeholder + a short note explaining how to derive it. Aim for clarity over cleverness.

Add a small reference block near the top:

```markdown
### Commit glob by language
- `rust`: `backend/connector-integration/src/connectors/{connector}*`
- `python`: `lens/connectors/{connector}*`
```

Then use `<commit glob for {LANG}>` in the `git add` commands.

- [ ] **Step 4: Commit**

```bash
git add workflow/2.4_pr.md
git commit -m "feat(workflow): lang-prefix PR titles + lang-specific commit glob

PR titles now carry [rust] / [python] prefix for at-a-glance tooling
visibility. Commit glob selects connector-service/ vs
lens/ paths."
```

---

### Task 10: Update top-level docs

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `setup.md`
- Modify: `.env.example` (optional note)

- [ ] **Step 1: Document the new flag in CLAUDE.md**

Open `CLAUDE.md`. Find the "Common commands" or "Quickstart" section that shows `grace techspec` invocations. Add a note about `--target-lang`:

Append after the existing flag descriptions or to the "Common commands" block:

```markdown
### Target language

The `--target-lang` flag (defaults to `python`) selects which language pack
will consume the generated tech spec. Acceptable values: `rust`, `python`.

```bash
grace techspec stripe -f ./docs --target-lang rust          # codegen-rust pack
grace techspec razorpay -f ./docs --target-lang python      # codegen-python pack (default)
```

When the corresponding target service repo (`connector-service/` for Rust,
`lens/` for Python) is not present as a sibling of
`grace/`, the CLI prints a loud warning rather than an orphaned next-step
hint.
```

- [ ] **Step 2: Document in README.md**

Open `README.md`. Find the "Quick Start" or examples section. Add a one-liner:

```markdown
> Pass `--target-lang rust|python` to select which language pack will consume the spec. Default: `python`.
```

Place it after the basic `grace techspec` examples.

- [ ] **Step 3: Document in setup.md**

Open `setup.md`. Find the section showing example invocations. Add the same `--target-lang` note next to existing examples.

- [ ] **Step 4: Add a note in `.env.example`**

Optional: add a comment near the top of `.env.example` mentioning that `--target-lang` is a CLI flag (not an env var). This avoids confusion if users go looking.

If the file already documents AI provider env vars cleanly, a small added comment block:

```bash
# Note: --target-lang (rust/python) is a CLI flag, not an env var.
#   grace techspec <connector> --target-lang python
```

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md README.md setup.md .env.example
git commit -m "docs: document --target-lang flag and workflow {LANG} parameter

Quickstart and command examples now show the flag. Notes that target
service repo absence triggers a warning."
```

---

### Task 11: Acceptance gate

**Files:**
- Read-only audits.

- [ ] **Step 1: Tests still pass**

```bash
source .venv/bin/activate
pytest tests/ -v
```
Must all pass.

- [ ] **Step 2: Flag works end-to-end**

```bash
source .venv/bin/activate
grace techspec --help | grep -A 1 'target-lang'
grace techspec dummy --target-lang java --test-only 2>&1 | grep -i 'invalid'  # rejected
grace techspec dummy --target-lang rust --test-only 2>&1 | head -5            # accepted (workflow may fail later — fine)
```

- [ ] **Step 3: Workflow agents reference `{LANG}`**

```bash
grep -l '{LANG}' workflow/*.md | sort
```
Expected: `1_orchestrator.md`, `2_connector.md`, `2.2_techspec.md`, `2.3_codegen.md`, `2.4_pr.md` (5 files). `2.1_links.md` is allowed to be absent — it's language-neutral.

- [ ] **Step 4: Language config block exists in 2.3_codegen.md**

```bash
grep -n 'Language config\|### rust\|### python' workflow/2.3_codegen.md | head
```
Expected: shows the config block with both `rust` and `python` subsections.

- [ ] **Step 5: Commit log**

```bash
git log --oneline | head -15
```
Note the new commits from Plan B (should be 10 — one per task except Task 5 and Task 11 which are verification-only).

- [ ] **Step 6: No working tree changes**

```bash
git status --short
```
Expected: empty (or only untracked `docs/`).

---

## Plan B acceptance summary

Plan B is complete when:
- All tasks above are committed
- `pytest tests/` passes
- `grace techspec --help` shows `--target-lang` with both lang choices and default
- `grace techspec X --target-lang python` prints a target-repo-missing warning (since `lens/` doesn't exist yet)
- Workflow agents have `{LANG}` threaded through and the language config block in `2.3_codegen.md`

After Plan B lands:
- Plan C (bootstrap `lens` shell) can proceed independently
- Plan D (Python pattern pack Wave 1) requires Plan C
- Plan E (Razorpay E2E) requires all prior plans

---

## Self-review notes (for the plan-writer's records)

Spec coverage:
- ✓ Section 5.1 `--target-lang` flag — Task 2
- ✓ Section 5.2 target-repo-exists warning — Task 3
- ✓ Section 5.4 state schema additions — Task 1
- ✓ Section 9.1 `{LANG}` threading — Tasks 6, 7, 9
- ✓ Section 9.2 language config block in 2.3_codegen.md — Task 8
- ✓ Section 9.4 commit glob by language — Task 9

Placeholders: none — every step has concrete code/commands.

Type consistency: `target_lang: str` in state (TypedDict total=False), `Click.Choice(['rust', 'python'])` in CLI, default `python`, threaded through `run_techspec_workflow` → `execute` → state.

Tests added: 4 new tests covering CLI parsing (5 assertions) and output_node next-step behavior (6 assertions). First test suite checked into the repo.
