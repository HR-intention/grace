# Grace (codegen) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the `python-support` branch on the team's Grace fork so Grace emits Python connector packages that conform to Lens's locked `Connector` ABC. v1 ships with one AI backend (Claude Code via local CLI) and a three-step pipeline (context → invoke → gates). Acceptance: `grace generate cashfree` regenerates the hand-written Cashfree connector with quality gates passing; `grace generate razorpay` produces a fresh connector that also passes gates; `python-support` is merged into `main`.

**Architecture:** Replace the existing fork's multi-prompt LangGraph workflow with a flat three-step pipeline. `pipeline/context.py` assembles a context bundle (Python rulebook + fetched PSP docs); `pipeline/runner.py` spawns Claude Code as a headless subprocess in the output directory; `pipeline/gates.py` runs `mypy --strict`, `pytest --cov`, and a six-dimension rubric on what Claude wrote. One concrete `ClaudeCodeRunner` class. No `AIProvider` ABC, no provider registry, no fallback chain, no `openai`/`anthropic` SDK dependencies. The Rust-targeted rulebook (`rulesbook/codegen/`) gets replaced by a Python-targeted rulebook that describes Lens's `Connector` ABC, the file layout from sub-project §3.2, and the constitution §4 generated-file marker.

**Tech Stack:** Python ≥3.11, `click` (CLI), `jinja2` (marker + skeleton templates), `pyyaml` (config), `httpx` (PSP doc fetching), `packaging` (semver), `uv` (env), subprocess-based `claude` CLI invocation. Subprocess invocations of `mypy`, `pytest`, `coverage` against generated code.

**Locked references (read before any task):**
- ``../specs/ORBIT_CONSTITUTION.md`` §4 (marker), §5 (`Connector` ABC + domain types), §9 (dependency order).
- ``../specs/SUBPROJECT_GRACE_CODEGEN.md`` §3 (architecture), §4 (`ClaudeCodeRunner`), §5 (rubric), §8 (acceptance), §9 (roadmap).
- ``../specs/SUBPROJECT_LENS.md`` §2 (glossary), §4 (interfaces), §5.1 (file layout), §5.2 (status mapping).

**Hard constraints (do not violate):**
- ONE AI backend. No `AIProvider` ABC. No OpenAI, Anthropic, Bedrock, or Gemini SDKs.
- Generated code matches Lens's locked `Connector` ABC exactly.
- Every emitted Python file carries the constitution §4 marker; gates fail otherwise.
- Grace never runs in production; codegen artifacts are committed to `lens` like normal code.
- The plan is the design. No revisiting decisions during execution.

---

## Overview

| Step | Title | Effort | Parallelizable |
|---|---|---|---|
| 0 | Setup (worktree, branch, env, prune) | 0.5d | — |
| 1 | Sync from upstream juspay-prism/grace | 0.5d | After Step 0 |
| 2 | Python rulebook + templates | 3d | Yes, in parallel with Step 3 once Step 1 lands |
| 3 | `ClaudeCodeRunner` + pipeline + CLI | 2d | Yes, in parallel with Step 2 once Step 1 lands |
| 4 | Quality gates + 6-dimension rubric | 1.5d | After Steps 2 & 3 |
| 5 | Regenerate Cashfree, diff against hand-written reference | 2d | After Step 4 |
| 6 | Generate Razorpay from scratch, pass gates | 2d | After Step 5 |
| 7 | Merge `python-support` into `main` | 0.5d | After Step 6 |

**Total:** ~12 days single-agent; ~10 days if Steps 2 and 3 split between two agents.

**Critical path:** 0 → 1 → (2 ∥ 3) → 4 → 5 → 6 → 7. Step 5 gates Step 6; Step 6 gates Step 7. Steps 2 and 3 are the only parallelizable pair on the critical path.

**Dependency on other sub-projects:**
- Steps 5 and 6 depend on Lens Step 3 (the hand-written Cashfree reference) being available. Confirm with the Lens implementing agent before starting Step 5.
- Step 7 depends on the Lens team accepting the regenerated Cashfree as drop-in equivalent to the hand-written reference.

---

## Step 0 — Setup

### Task 0.1: Confirm branch state & freeze the working tree

**Files:**
- Read: `/Users/sarthak/PycharmProjects/references/grace/.git/HEAD`
- Read: `/Users/sarthak/PycharmProjects/references/grace/.git/refs/heads/`

- [ ] **Step 1: Confirm `main` and `python-support` exist locally**

```bash
ls /Users/sarthak/PycharmProjects/references/grace/.git/refs/heads/
```
Expected output (one per line): `main`, `python-support`.

- [ ] **Step 2: Confirm origin remote is the team fork**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace remote -v
```
Expected: `origin  git@github.com:HR-intention/grace.git` (or HTTPS equivalent). If the remote is something else, stop and re-check with the owner before continuing.

- [ ] **Step 3: Ensure working tree is clean**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace status
```
Expected: `nothing to commit, working tree clean`. If dirty, stop — do not proceed until the owner clarifies what to keep.

- [ ] **Step 4: Check out `python-support`**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace checkout python-support
git -C /Users/sarthak/PycharmProjects/references/grace status
```
Expected: `On branch python-support`, clean tree.

**Validation criterion:** `git status` reports clean on `python-support`.

**Estimated effort:** 15 min.

---

### Task 0.2: Add `juspay-prism` as a remote

**Files:**
- Modify: `/Users/sarthak/PycharmProjects/references/grace/.git/config` (via `git remote add`)

- [ ] **Step 1: Add upstream remote**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace remote add upstream https://github.com/juspay/hyperswitch-prism.git
git -C /Users/sarthak/PycharmProjects/references/grace remote -v
```
Expected output includes both `origin` (HR-intention/grace) and `upstream` (juspay/hyperswitch-prism).

- [ ] **Step 2: Fetch upstream**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace fetch upstream
```
Expected: no error; remote refs populated under `.git/refs/remotes/upstream/`.

**Validation criterion:** `git remote -v` shows two remotes; `git -C ... branch -r` lists `upstream/main` (or whichever upstream default branch name applies).

**Estimated effort:** 5 min.

---

### Task 0.3: Inventory the existing fork's modules to prune

The fork carries LangGraph workflows, litellm provider abstraction, prompt orchestration, and Firecrawl scraping — none of which the v1 spec wants. Catalog the pieces that must be deleted in Step 3 so the cleanup is concrete, not improvised.

**Files:**
- Read-only inventory; write findings into the plan's working notes (not into the repo).

- [ ] **Step 1: List what's there**

```bash
ls /Users/sarthak/PycharmProjects/references/grace/src/
ls /Users/sarthak/PycharmProjects/references/grace/src/ai/
ls /Users/sarthak/PycharmProjects/references/grace/src/workflows/
ls /Users/sarthak/PycharmProjects/references/grace/src/tools/
ls /Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/
```

- [ ] **Step 2: Tag what survives, what dies**

Survives (will be heavily rewritten):
- `src/cli.py` — keep as the entrypoint; rewrite contents in Step 3.
- `src/config.py` — keep as the home for `~/.grace/config.yaml` loading; rewrite in Step 3.
- `src/types/` — keep as the home for `GenerationContext`, `GenerationResult`, `GraceError`, `GraceErrorReason`; rewrite in Step 3.
- `pyproject.toml` — keep, edit heavily in Task 0.5.

Dies in Step 3:
- `src/ai/ai_service.py` (the litellm/multi-provider abstraction).
- `src/ai/prompts/`, `src/ai/system/` (LangGraph macro-prompt config).
- `src/workflows/techspec/` (LangGraph tech-spec workflow — replaced by the 3-step pipeline).
- `src/tools/firecrawl/` (replaced by `httpx` direct fetching in `pipeline/context.py`).
- `src/utils/ai_utils.py`, `src/utils/transformations.py` (LangChain glue).

Dies in Step 2:
- `rulesbook/codegen/template-generation/connector.rs.template`
- `rulesbook/codegen/template-generation/test.rs.template`
- `rulesbook/codegen/template-generation/transformers.rs.template`
- `rulesbook/codegen/template-generation/macro_templates.md`
- `rulesbook/codegen/guides/patterns/pattern_authorize.md`, `pattern_capture.md`, `pattern_void.md`, `pattern_void_pc.md`, `pattern_setup_mandate.md`, `pattern_mandate_revoke.md`, `pattern_payment_method_token.md`, `pattern_session_token.md`, `pattern_IncrementalAuthorization_flow.md`, `pattern_repeat_payment_flow.md`, `pattern_accept_dispute.md`, `pattern_defend_dispute.md`, `pattern_submit_evidence.md` (out-of-scope flows per constitution §7).
- All other Rust-targeted pattern files (rewritten in Step 2).

**Validation criterion:** the implementing agent has produced a written inventory matching the above before starting Step 1. No code changes yet.

**Estimated effort:** 30 min.

---

### Task 0.4: Reset `uv` environment to Python 3.11

**Files:**
- Create: `/Users/sarthak/PycharmProjects/references/grace/.python-version`

- [ ] **Step 1: Pin Python 3.11**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv python pin 3.11
cat /Users/sarthak/PycharmProjects/references/grace/.python-version
```
Expected: file contains `3.11`.

- [ ] **Step 2: Rebuild the virtualenv**

```bash
rm -rf /Users/sarthak/PycharmProjects/references/grace/.venv
cd /Users/sarthak/PycharmProjects/references/grace && uv venv
```
Expected: new `.venv` created.

- [ ] **Step 3: Sync existing deps (pre-pruning) to confirm baseline imports**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv pip install -e .
```
Expected: install succeeds (LangGraph etc. still present at this point — that's fine, Task 0.5 prunes them).

- [ ] **Step 4: Commit the `.python-version`**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace add .python-version
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "chore: pin Python 3.11 for grace fork"
```

**Validation criterion:** `uv run python --version` reports `Python 3.11.x`.

**Estimated effort:** 15 min.

---

### Task 0.5: Prune `pyproject.toml` to the v1 dependency set

**Files:**
- Modify: `/Users/sarthak/PycharmProjects/references/grace/pyproject.toml`

- [ ] **Step 1: Rewrite `pyproject.toml`**

Replace the file contents with:

```toml
[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "grace-cli"
version = "0.1.0"
description = "Grace: codegen tool that emits Python PSP connectors for the Orbit Lens ABC."
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [{name = "Symplora Engineering", email = "engineering@symplora.com"}]
keywords = ["cli", "codegen", "psp", "connector", "orbit"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
    "click>=8.1.0",
    "jinja2>=3.1.0",
    "pyyaml>=6.0",
    "httpx>=0.27.0",
    "structlog>=24.0.0",
    "rich>=13.5.0",
    "pydantic>=2.6.0",
    "packaging>=24.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.12.0",
    "mypy>=1.10.0",
    "ruff>=0.4.0",
]

[project.urls]
Homepage = "https://github.com/HR-intention/grace"
Repository = "https://github.com/HR-intention/grace"
Upstream = "https://github.com/juspay/hyperswitch-prism"

[project.scripts]
grace = "grace.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
include = ["grace*"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_ignores = true
warn_redundant_casts = true
warn_unreachable = true
strict_equality = true
explicit_package_bases = true
mypy_path = "src"

[tool.pytest.ini_options]
minversion = "8.0"
addopts = "-ra -q --strict-markers --strict-config"
testpaths = ["tests"]
python_files = ["test_*.py"]
asyncio_mode = "auto"
markers = [
    "integration: integration tests that may spawn subprocesses",
    "rubric: rubric-scoring tests",
]

[tool.ruff]
line-length = 100
target-version = "py311"
```

Key deletions from the original:
- `langgraph`, `langchain`, `langchain-core`, `litellm`, `claude-agent-sdk`, `pydantic-settings`, `requests`, `aiohttp`, `markdownify`, `pypdf2`, `python-docx`, `pandas`, `openpyxl`, `flake8`, `types-pyyaml`, `types-requests`, `python-dotenv` (no .env-driven secrets in v1; no provider keys).
- Optional `ai` extras (`openai`, `anthropic`) — gone.
- Optional `nlp` extras — gone.
- Black/isort config — replaced by `ruff` (single tool).

Key changes:
- Entry point moves from `src.cli:main` to `grace.cli:main` (package is now named `grace`, lives under `src/grace/`).
- `requires-python` bumped to `>=3.11` (constitution §6).
- `mypy.strict = true` (no per-flag tuning).
- Version reset to `0.1.0` (the v1 baseline; constitution §8).

- [ ] **Step 2: Refresh lockfile**

```bash
rm -f /Users/sarthak/PycharmProjects/references/grace/uv.lock
cd /Users/sarthak/PycharmProjects/references/grace && uv lock
cd /Users/sarthak/PycharmProjects/references/grace && uv sync --extra dev
```
Expected: lock + sync succeed; new `.venv` populated only with the dependencies above.

- [ ] **Step 3: Verify the prune**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv pip list | grep -Ei 'langgraph|langchain|litellm|openai|anthropic|claude-agent-sdk|firecrawl' || echo "OK — none present"
```
Expected: `OK — none present`.

- [ ] **Step 4: Commit**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace add pyproject.toml uv.lock
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "chore: prune pyproject to v1 dep set (no AI SDKs, no LangChain stack)"
```

**Validation criterion:** `uv pip list` shows only the dependencies listed in the new `pyproject.toml`. No `openai`, no `anthropic`, no `langgraph`, no `litellm`.

**Estimated effort:** 45 min.

---

## Step 1 — Sync upstream juspay-prism/grace

The spec's roadmap §9 step 1 calls this out as 0.5d. The goal is a clean baseline before we rewrite anything: pull in any non-rule-related infrastructure improvements upstream may have shipped (e.g., the `add_connector.sh` script, doc updates) without taking their Rust-specific rulebook on top of ours.

### Task 1.1: Identify what to merge

**Files:**
- Read-only inventory.

- [ ] **Step 1: Diff upstream vs our `python-support` for non-rulebook paths**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace diff --stat python-support upstream/main -- ':!rulesbook/codegen/template-generation/*' ':!src/' | head -60
```
Expected: a list of files only outside `src/` and the Rust templates dir. Note which look worth pulling (README updates, build scripts, `rulesbook/README.md`, etc.).

- [ ] **Step 2: Snapshot the list**

Write the list as a comment in the next commit message. We'll deliberately leave most upstream rulebook/code changes behind because Step 2 rewrites the rulebook and Step 3 rewrites `src/`.

**Validation criterion:** the implementing agent has a concrete list of upstream files to cherry-pick.

**Estimated effort:** 30 min.

---

### Task 1.2: Cherry-pick non-code upstream improvements

**Files:**
- Variable — pulled selectively.

- [ ] **Step 1: Cherry-pick infra-only commits**

For each commit identified in Task 1.1 that touches only docs/scripts (not `src/`, not `rulesbook/codegen/template-generation/`, not `rulesbook/codegen/guides/patterns/`):

```bash
git -C /Users/sarthak/PycharmProjects/references/grace cherry-pick <sha>
```

If a cherry-pick conflicts, abort it and skip — we're not investing in conflict resolution here.

```bash
git -C /Users/sarthak/PycharmProjects/references/grace cherry-pick --abort
```

- [ ] **Step 2: Commit a no-op "upstream sync marker" if nothing landed**

If no cherry-picks succeeded, create an empty commit documenting that upstream had nothing to pull at this checkpoint:

```bash
git -C /Users/sarthak/PycharmProjects/references/grace commit --allow-empty -m "chore: upstream sync marker (nothing relevant to merge from juspay-prism at this checkpoint)"
```

**Validation criterion:** `git log --oneline -5` shows either cherry-picks from upstream or the sync marker; subsequent steps proceed from a documented baseline.

**Estimated effort:** 30 min – 2 hr (highly variable based on upstream divergence).

---

## Step 2 — Python rulebook + templates

Replace the Rust-targeted rulebook with one that describes the Python `Connector` ABC and a Jinja2 marker template. This is the "what Grace tells Claude Code to produce" knowledge.

### Task 2.1: Delete the Rust templates and out-of-scope patterns

**Files:**
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/template-generation/connector.rs.template`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/template-generation/test.rs.template`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/template-generation/transformers.rs.template`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/template-generation/macro_templates.md`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_authorize.md`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_capture.md`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_void.md`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_void_pc.md`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_setup_mandate.md`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_mandate_revoke.md`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_payment_method_token.md`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_session_token.md`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_IncrementalAuthorization_flow.md`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_repeat_payment_flow.md`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_accept_dispute.md`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_defend_dispute.md`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_submit_evidence.md`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/authorize/` (entire subdir if present)
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/flow_macro_guide.md`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/macro_patterns_reference.md`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_CreateAccessToken_flow.md`

- [ ] **Step 1: Remove the files in one batch**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace rm \
  rulesbook/codegen/template-generation/connector.rs.template \
  rulesbook/codegen/template-generation/test.rs.template \
  rulesbook/codegen/template-generation/transformers.rs.template \
  rulesbook/codegen/template-generation/macro_templates.md \
  rulesbook/codegen/guides/patterns/pattern_authorize.md \
  rulesbook/codegen/guides/patterns/pattern_capture.md \
  rulesbook/codegen/guides/patterns/pattern_void.md \
  rulesbook/codegen/guides/patterns/pattern_void_pc.md \
  rulesbook/codegen/guides/patterns/pattern_setup_mandate.md \
  rulesbook/codegen/guides/patterns/pattern_mandate_revoke.md \
  rulesbook/codegen/guides/patterns/pattern_payment_method_token.md \
  rulesbook/codegen/guides/patterns/pattern_session_token.md \
  rulesbook/codegen/guides/patterns/pattern_IncrementalAuthorization_flow.md \
  rulesbook/codegen/guides/patterns/pattern_repeat_payment_flow.md \
  rulesbook/codegen/guides/patterns/pattern_accept_dispute.md \
  rulesbook/codegen/guides/patterns/pattern_defend_dispute.md \
  rulesbook/codegen/guides/patterns/pattern_submit_evidence.md \
  rulesbook/codegen/guides/patterns/flow_macro_guide.md \
  rulesbook/codegen/guides/patterns/macro_patterns_reference.md \
  rulesbook/codegen/guides/patterns/pattern_CreateAccessToken_flow.md
git -C /Users/sarthak/PycharmProjects/references/grace rm -r rulesbook/codegen/guides/patterns/authorize 2>/dev/null || true
```

- [ ] **Step 2: Commit**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "chore(rulebook): drop Rust templates + out-of-scope flow patterns"
```

**Validation criterion:** `ls /Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/template-generation/` is empty; `ls .../guides/patterns/` shows only patterns kept for v1 (`pattern_createorder.md`, `pattern_psync.md`, `pattern_refund.md`, `pattern_rsync.md`, `pattern_IncomingWebhook_flow.md`, `README.md`).

**Estimated effort:** 15 min.

---

### Task 2.2: Create the Python connector rulebook

The rulebook tells Claude Code exactly what to build. It is plain Markdown — Claude reads it as part of the context bundle.

**Files:**
- Create: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/python/README.md`
- Create: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/python/connector_abc.md`
- Create: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/python/domain_types.md`
- Create: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/python/file_layout.md`
- Create: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/python/status_mapping.md`
- Create: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/python/webhook_handling.md`
- Create: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/python/marker.md`
- Create: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/python/testing.md`
- Create: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/python/ground_rules.md`

- [ ] **Step 1: Write `python/README.md`**

Contents must explain:
- Grace generates one Python package per PSP under `lens/connectors/<psp>/`.
- The package must implement the locked `Connector` ABC from Lens (see `connector_abc.md`).
- Every emitted Python file starts with the constitution §4 marker (see `marker.md`).
- The reading order: `ground_rules.md` → `connector_abc.md` → `domain_types.md` → `file_layout.md` → `status_mapping.md` → `webhook_handling.md` → `testing.md` → `marker.md`.

- [ ] **Step 2: Write `python/connector_abc.md`**

Paste the exact `Connector` ABC from `SUBPROJECT_LENS.md` §4.2 (the verbatim `class Connector(ABC):` block with all four flow methods, `handle_webhook`, `close`, plus the four properties). Add a header note: "This is the locked surface. Do not invent additional methods. Do not rename properties. Hand-edits to the surface are forbidden."

- [ ] **Step 3: Write `python/domain_types.md`**

Paste verbatim from `SUBPROJECT_LENS.md` §4.4 (the full block from `class Amount(BaseModel):` through `class WebhookEvent(BaseModel):`) and §4.6 (all enums). Add a header note: "These types live in `lens.domain_types` and `lens.enums`. Import them; do not redefine them. Never widen an enum locally."

- [ ] **Step 4: Write `python/file_layout.md`**

Paste verbatim from `SUBPROJECT_GRACE_CODEGEN.md` §3.2 (the `connectors/<psp>/` tree). Add for each file a one-sentence "what goes here":

```
__init__.py     — Module scope: declare requires_lens = "<constraint>".
                   At the bottom: from .connector import <Psp>; ConnectorFactory.register("<psp>", <Psp>).
connector.py    — class <Psp>(Connector). Implements all four flows + handle_webhook + close.
                   Each flow: validate input, build PSP request, call self._client, parse response, return domain response.
                   Wrap httpx.HTTPStatusError -> _map_http_error; httpx.HTTPError -> ConnectorError(PSP_UNAVAILABLE).
auth.py         — signing helpers. Credentials typed Maskable[str].
models.py       — wire-level Pydantic models. extra="forbid"; frozen=True on request models.
status_map.py   — PSP-specific status string -> (PaymentAttemptStatus, PaymentFailureCode).
                   Define a single dict; have a function map_status(s: str) -> tuple[..., ...] that
                   returns (PENDING/SUCCESS/FAILED, code-or-None) and falls back to
                   (FAILED, PaymentFailureCode.UNKNOWN) with a structlog.warning for unknown values.
tests/test_create_order.py — httpx.MockTransport-backed test of the happy path + a 4xx path.
tests/test_sync_payment.py — single-attempt + multi-attempt (first FAILED, second SUCCESS) cases.
tests/test_refund.py       — happy path + already-refunded path.
tests/test_sync_refund.py  — PENDING and SUCCESS paths.
tests/test_webhook.py      — signed PAYMENT_SUCCESS, signed PAYMENT_FAILED, signed REFUND_SUCCESS,
                               tampered payload -> ConnectorError(WEBHOOK_SIGNATURE_FAILED).
```

- [ ] **Step 5: Write `python/status_mapping.md`**

Paste verbatim the Cashfree table from `SUBPROJECT_LENS.md` §5.2 as a worked example. Then add:

> Every PSP has its own vocabulary. Read the PSP's docs for the full status list, then produce `status_map.py` with one entry per documented status. Unknown statuses must fall back to `(PaymentAttemptStatus.FAILED, PaymentFailureCode.UNKNOWN)` and `structlog.warning("unknown_psp_status", value=<raw>)`.

- [ ] **Step 6: Write `python/webhook_handling.md`**

Distill `SUBPROJECT_LENS.md` §5.3's `handle_webhook` example into a step list:
1. Verify signature using `auth.py` helper. On failure: `raise ConnectorError(reason=WEBHOOK_SIGNATURE_FAILED)`.
2. Parse `raw_payload` as JSON into the PSP's webhook event model.
3. Branch on event type. For PAYMENT_* events: populate `WebhookEvent.attempt: PaymentAttempt`. For REFUND_* events: populate `WebhookEvent.refund: RefundEvent`. For ORDER_EXPIRED: neither.
4. Return `WebhookEvent(event_type=..., psp_event_id=..., psp_order_id=..., attempt=..., refund=..., raw_payload=...)`.
5. Unknown event type: log a warning and return a `WebhookEvent` with `event_type` set to the closest known value or raise nothing — Orbit decides what to do.

- [ ] **Step 7: Write `python/marker.md`**

Paste the constitution §4 marker block verbatim. Add: "This block is the FIRST non-shebang content in every .py file Grace writes. The block is rendered by `templates/marker.j2` in Grace; the rendered output must match the format exactly. No blank line before the marker; one blank line after."

- [ ] **Step 8: Write `python/testing.md`**

Distill from constitution §6 + SUBPROJECT §6:
- Use `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`).
- Use `httpx.MockTransport` for all HTTP-touching tests. Never hit a live PSP.
- Cover all four flows + webhook (5 test files).
- Aim for `pytest --cov` ≥ 80% line coverage on the generated package.
- Multi-attempt test must show two `PaymentAttempt` instances in the `SyncPaymentResponse.attempts` list with `PaymentAttemptStatus.FAILED` followed by `PaymentAttemptStatus.SUCCESS`.

- [ ] **Step 9: Write `python/ground_rules.md`**

Paste verbatim from `SUBPROJECT_LENS.md` §3 (rules 1–16). Add a note at the top: "These rules are non-negotiable. Violations fail the quality rubric."

- [ ] **Step 10: Commit**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace add rulesbook/codegen/python/
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "feat(rulebook): add Python connector rulebook targeting Lens Connector ABC"
```

**Validation criterion:** `ls rulesbook/codegen/python/` lists all nine files. Open each and verify the verbatim quotes match the spec sources (no rewording of locked surfaces).

**Estimated effort:** 1 day.

---

### Task 2.3: Curate the upstream Python pattern files

The upstream `rulesbook/codegen/guides/patterns/` directory has Python-friendly patterns we want to keep but adapt: `pattern_createorder.md`, `pattern_psync.md`, `pattern_refund.md`, `pattern_rsync.md`, `pattern_IncomingWebhook_flow.md`. These were written for Rust. Adapt them.

**Files:**
- Modify: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_createorder.md`
- Modify: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_psync.md`
- Modify: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_refund.md`
- Modify: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_rsync.md`
- Modify: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/pattern_IncomingWebhook_flow.md`
- Modify: `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/patterns/README.md`
- Delete (Rust types reference, no longer applicable): `/Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/guides/types/types.md`

- [ ] **Step 1: Open each pattern file and rewrite for Python + the Connector ABC**

Each file must end up structured as:

```markdown
# Pattern: <flow name>

## Domain types involved
- Request: `<DomainRequestType>` (from `lens.domain_types`)
- Response: `<DomainResponseType>` (from `lens.domain_types`)

## Method signature (in `connector.py`)
```python
async def <flow>(self, request: <DomainRequestType>) -> <DomainResponseType>:
    ...
```

## Implementation skeleton
[Python pseudocode showing: build wire request from domain request -> sign -> POST/GET via self._client
 -> raise_for_status -> parse wire response -> build domain response -> return]

## Errors to surface
- httpx.HTTPStatusError 4xx -> map via _map_http_error
- httpx.HTTPError network -> ConnectorError(PSP_UNAVAILABLE)
- Validation failures of wire response -> ConnectorError(INTERNAL) with psp_message=str(e)

## Tests
[Outline of the test cases the rubric expects in tests/test_<flow>.py]
```

Reference `SUBPROJECT_LENS.md` §5.3 (the Cashfree `create_order` worked example) as the canonical shape — patterns describe this shape generically without referring to Cashfree.

- [ ] **Step 2: Rewrite `pattern_IncomingWebhook_flow.md`** following the steps in `python/webhook_handling.md`.

- [ ] **Step 3: Rewrite `patterns/README.md`** to list only the five v1 patterns above and reference `../python/` as the entry point.

- [ ] **Step 4: Delete the old types reference**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace rm rulesbook/codegen/guides/types/types.md
```

The Python equivalent lives in `rulesbook/codegen/python/domain_types.md`.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace add rulesbook/codegen/guides/patterns/ rulesbook/codegen/guides/types/
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "refactor(rulebook): rewrite v1 flow patterns for Python + Connector ABC"
```

**Validation criterion:** the five pattern files compile as readable Markdown, contain Python code blocks (not Rust), and reference the domain types from `SUBPROJECT_LENS.md` §4.4 by name.

**Estimated effort:** 0.5 day.

---

### Task 2.4: Create the marker Jinja2 template

**Files:**
- Create: `/Users/sarthak/PycharmProjects/references/grace/src/grace/templates/marker.j2`
- Create: `/Users/sarthak/PycharmProjects/references/grace/src/grace/templates/__init__.py`
- Create: `/Users/sarthak/PycharmProjects/references/grace/src/grace/__init__.py`

- [ ] **Step 1: Create the package directories**

```bash
mkdir -p /Users/sarthak/PycharmProjects/references/grace/src/grace/templates
touch /Users/sarthak/PycharmProjects/references/grace/src/grace/__init__.py
touch /Users/sarthak/PycharmProjects/references/grace/src/grace/templates/__init__.py
```

- [ ] **Step 2: Write `marker.j2`**

```jinja2
# ──────────────────────────────────────────────────────────────────────
#  DO NOT EDIT — autogenerated by Grace.
#  Source: {{ psp_name }} {{ source_version }}
#  Generated: {{ generated_utc_iso8601 }}
#  Generator: grace {{ grace_version }}
#  Regenerate: grace generate {{ psp_name }} --from {{ source_uri }}
# ──────────────────────────────────────────────────────────────────────
```

Match the constitution §4 format byte-for-byte: six lines, leading `# `, en-dash box, identical field labels.

- [ ] **Step 3: Write a focused test for the marker template**

Create: `/Users/sarthak/PycharmProjects/references/grace/tests/test_marker_template.py`

```python
from __future__ import annotations

from pathlib import Path

import jinja2


def _env() -> jinja2.Environment:
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(
            Path(__file__).parent.parent / "src" / "grace" / "templates"
        ),
        keep_trailing_newline=True,
        autoescape=False,
    )


def test_marker_has_six_lines_and_constitution_field_labels() -> None:
    rendered = _env().get_template("marker.j2").render(
        psp_name="cashfree",
        source_version="2024-09-01",
        generated_utc_iso8601="2026-05-20T12:00:00Z",
        grace_version="0.1.0",
        source_uri="https://docs.cashfree.com/openapi.yaml",
    )
    lines = rendered.strip("\n").splitlines()
    assert len(lines) == 6, lines
    assert lines[0].startswith("# ─")
    assert lines[1] == "#  DO NOT EDIT — autogenerated by Grace."
    assert lines[2] == "#  Source: cashfree 2024-09-01"
    assert lines[3] == "#  Generated: 2026-05-20T12:00:00Z"
    assert lines[4] == "#  Generator: grace 0.1.0"
    assert lines[5].startswith("#  Regenerate: grace generate cashfree --from ")
```

Note: the closing `# ─` line is part of the same box pattern; the test deliberately checks first/last lines start with `# ─` and the four middle lines match the locked labels. Adjust your template so the test passes.

Wait — re-read: the constitution shows seven lines if both the top `# ──...──` and bottom `# ──...──` are counted; the four middle data lines sit between two box-rule lines. Re-do the template:

```jinja2
# ──────────────────────────────────────────────────────────────────────
#  DO NOT EDIT — autogenerated by Grace.
#  Source: {{ psp_name }} {{ source_version }}
#  Generated: {{ generated_utc_iso8601 }}
#  Generator: grace {{ grace_version }}
#  Regenerate: grace generate {{ psp_name }} --from {{ source_uri }}
# ──────────────────────────────────────────────────────────────────────
```

That is seven lines. Update the test:

```python
def test_marker_format_matches_constitution_section_4() -> None:
    rendered = _env().get_template("marker.j2").render(
        psp_name="cashfree",
        source_version="2024-09-01",
        generated_utc_iso8601="2026-05-20T12:00:00Z",
        grace_version="0.1.0",
        source_uri="https://docs.cashfree.com/openapi.yaml",
    )
    lines = rendered.strip("\n").splitlines()
    assert len(lines) == 7, lines
    assert lines[0].startswith("# ─") and lines[6].startswith("# ─")
    assert lines[1] == "#  DO NOT EDIT — autogenerated by Grace."
    assert lines[2] == "#  Source: cashfree 2024-09-01"
    assert lines[3] == "#  Generated: 2026-05-20T12:00:00Z"
    assert lines[4] == "#  Generator: grace 0.1.0"
    assert lines[5] == "#  Regenerate: grace generate cashfree --from https://docs.cashfree.com/openapi.yaml"
```

- [ ] **Step 4: Run the test, confirm it passes**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest tests/test_marker_template.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace add src/grace tests/test_marker_template.py
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "feat(templates): add marker.j2 matching constitution §4 format"
```

**Validation criterion:** `pytest tests/test_marker_template.py` passes. Manually render the template with a known input and confirm output exactly matches the constitution §4 block.

**Estimated effort:** 2 hr.

---

### Task 2.5: Create a per-PSP package-skeleton template

Grace doesn't generate the connector code itself — Claude Code does. But Grace pre-creates the empty directory skeleton with the marker stub in each file, so Claude is filling in known-shaped files. Skip if Step 3's pipeline decides Claude should create the files cold; otherwise create skeleton files Claude overwrites. Decision: skip skeleton creation in v1. The runner sets working directory; Claude creates files itself. Document this in the pattern files (Task 2.3 already covers it).

**Files:**
- None.

- [ ] **Step 1: No-op task; advance to Step 3.**

**Validation criterion:** none.

**Estimated effort:** 0 — placeholder so the task numbering stays stable.

---

## Step 3 — `ClaudeCodeRunner` + pipeline + CLI

This is the engine. One concrete `ClaudeCodeRunner`. A `pipeline` package with `context.py`, `runner.py`, `gates.py`, and `__init__.py` orchestration. A `cli.py` with `generate`, `regenerate`, `doctor`, `--version`. No provider abstraction.

### Task 3.1: Tear out the old `src/` modules

**Files:**
- Delete: `/Users/sarthak/PycharmProjects/references/grace/src/ai/`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/src/workflows/`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/src/tools/`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/src/utils/ai_utils.py`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/src/utils/transformations.py`
- Delete: `/Users/sarthak/PycharmProjects/references/grace/src/cli.py` (will be re-created at `src/grace/cli.py`)
- Delete: `/Users/sarthak/PycharmProjects/references/grace/src/config.py` (will be re-created at `src/grace/config.py`)
- Delete: `/Users/sarthak/PycharmProjects/references/grace/src/types/`

- [ ] **Step 1: Remove old layout**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace rm -r src/ai src/workflows src/tools src/types
git -C /Users/sarthak/PycharmProjects/references/grace rm src/utils/ai_utils.py src/utils/transformations.py src/cli.py src/config.py
```

- [ ] **Step 2: Keep `src/utils/validations.py` for now**

If it has anything reusable (regex helpers, etc.), it can be re-homed in `src/grace/` later. Leave it in place; we'll evaluate during Step 3.3.

- [ ] **Step 3: Commit**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "refactor: remove LangGraph/litellm/firecrawl stack; new grace package coming"
```

**Validation criterion:** `ls src/` shows only `utils/` (and the empty `grace/` from Task 2.4). `uv run python -c "import grace"` succeeds (empty package).

**Estimated effort:** 30 min.

---

### Task 3.2: Define `GraceError` and supporting types

**Files:**
- Create: `/Users/sarthak/PycharmProjects/references/grace/src/grace/errors.py`
- Create: `/Users/sarthak/PycharmProjects/references/grace/tests/test_errors.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_errors.py
from __future__ import annotations

import pytest

from grace.errors import GraceError, GraceErrorReason


def test_grace_error_carries_reason_and_detail() -> None:
    e = GraceError(reason=GraceErrorReason.CLAUDE_CODE_NOT_FOUND, detail="binary missing")
    assert e.reason is GraceErrorReason.CLAUDE_CODE_NOT_FOUND
    assert e.detail == "binary missing"
    assert "CLAUDE_CODE_NOT_FOUND" in str(e)


def test_grace_error_reasons_locked() -> None:
    expected = {
        "CLAUDE_CODE_NOT_FOUND",
        "CLAUDE_CODE_NOT_AUTHENTICATED",
        "CLAUDE_CODE_TIMEOUT",
        "CLAUDE_CODE_FAILED",
        "CONTEXT_BUNDLE_INVALID",
        "QUALITY_GATE_FAILED",
        "SOURCE_FETCH_FAILED",
        "CONFIG_INVALID",
    }
    assert {r.value for r in GraceErrorReason} == expected
```

- [ ] **Step 2: Run the test, confirm it fails**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest tests/test_errors.py -v
```
Expected: `ImportError: cannot import name 'GraceError'`.

- [ ] **Step 3: Implement**

```python
# src/grace/errors.py
from __future__ import annotations

from enum import StrEnum


class GraceErrorReason(StrEnum):
    CLAUDE_CODE_NOT_FOUND = "CLAUDE_CODE_NOT_FOUND"
    CLAUDE_CODE_NOT_AUTHENTICATED = "CLAUDE_CODE_NOT_AUTHENTICATED"
    CLAUDE_CODE_TIMEOUT = "CLAUDE_CODE_TIMEOUT"
    CLAUDE_CODE_FAILED = "CLAUDE_CODE_FAILED"
    CONTEXT_BUNDLE_INVALID = "CONTEXT_BUNDLE_INVALID"
    QUALITY_GATE_FAILED = "QUALITY_GATE_FAILED"
    SOURCE_FETCH_FAILED = "SOURCE_FETCH_FAILED"
    CONFIG_INVALID = "CONFIG_INVALID"


class GraceError(Exception):
    def __init__(self, *, reason: GraceErrorReason, detail: str | None = None):
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason.value}: {detail}" if detail else reason.value)
```

- [ ] **Step 4: Run the test, confirm it passes**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest tests/test_errors.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace add src/grace/errors.py tests/test_errors.py
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "feat(errors): add GraceError + GraceErrorReason enum"
```

**Validation criterion:** `pytest tests/test_errors.py` passes.

**Estimated effort:** 30 min.

---

### Task 3.3: Config loading

**Files:**
- Create: `/Users/sarthak/PycharmProjects/references/grace/src/grace/config.py`
- Create: `/Users/sarthak/PycharmProjects/references/grace/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from __future__ import annotations

from pathlib import Path

import pytest

from grace.config import GraceConfig, load_config
from grace.errors import GraceError, GraceErrorReason


def test_default_config_when_file_absent(tmp_path: Path) -> None:
    cfg = load_config(config_path=tmp_path / "missing.yaml")
    assert cfg.claude_code.cli_path is None
    assert cfg.claude_code.timeout_s == 1800
    assert cfg.quality.mypy_strict is True
    assert cfg.quality.min_coverage_pct == 80
    assert cfg.quality.min_rubric_score == 60
    assert cfg.lens.version_constraint == "^0.1"


def test_config_loaded_from_yaml(tmp_path: Path) -> None:
    p = tmp_path / "config.yaml"
    p.write_text(
        "claude_code:\n"
        "  cli_path: /usr/local/bin/claude\n"
        "  timeout_s: 600\n"
        "quality:\n"
        "  mypy_strict: false\n"
        "  min_coverage_pct: 85\n"
        "  min_rubric_score: 70\n"
        "lens:\n"
        "  version_constraint: '^0.2'\n"
    )
    cfg = load_config(config_path=p)
    assert str(cfg.claude_code.cli_path) == "/usr/local/bin/claude"
    assert cfg.claude_code.timeout_s == 600
    assert cfg.quality.mypy_strict is False
    assert cfg.quality.min_coverage_pct == 85
    assert cfg.quality.min_rubric_score == 70
    assert cfg.lens.version_constraint == "^0.2"


def test_invalid_yaml_raises_config_invalid(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("claude_code: not-a-mapping")
    with pytest.raises(GraceError) as exc:
        load_config(config_path=p)
    assert exc.value.reason is GraceErrorReason.CONFIG_INVALID
```

- [ ] **Step 2: Run the test, confirm it fails**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest tests/test_config.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement**

```python
# src/grace/config.py
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from grace.errors import GraceError, GraceErrorReason


class ClaudeCodeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    cli_path: Path | None = None
    timeout_s: float = 1800.0


class QualityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    mypy_strict: bool = True
    min_coverage_pct: int = 80
    min_rubric_score: int = 60


class LensConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version_constraint: str = "^0.1"


class GraceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    claude_code: ClaudeCodeConfig = Field(default_factory=ClaudeCodeConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    lens: LensConfig = Field(default_factory=LensConfig)


def load_config(config_path: Path | None = None) -> GraceConfig:
    """Load ~/.grace/config.yaml (or the path argument). Returns defaults if absent."""
    path = config_path if config_path is not None else Path.home() / ".grace" / "config.yaml"
    if not path.exists():
        return GraceConfig()
    try:
        raw: Any = yaml.safe_load(path.read_text()) or {}
        if not isinstance(raw, dict):
            raise GraceError(reason=GraceErrorReason.CONFIG_INVALID, detail=f"root must be a mapping in {path}")
        return GraceConfig.model_validate(raw)
    except yaml.YAMLError as e:
        raise GraceError(reason=GraceErrorReason.CONFIG_INVALID, detail=str(e)) from e
    except ValidationError as e:
        raise GraceError(reason=GraceErrorReason.CONFIG_INVALID, detail=str(e)) from e
```

- [ ] **Step 4: Run the test, confirm it passes**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest tests/test_config.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace add src/grace/config.py tests/test_config.py
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "feat(config): add GraceConfig + load_config (~/.grace/config.yaml)"
```

**Validation criterion:** `pytest tests/test_config.py` passes.

**Estimated effort:** 1 hr.

---

### Task 3.4: `GenerationContext` and `GenerationResult` dataclasses

**Files:**
- Create: `/Users/sarthak/PycharmProjects/references/grace/src/grace/pipeline/__init__.py`
- Create: `/Users/sarthak/PycharmProjects/references/grace/src/grace/pipeline/types.py`
- Create: `/Users/sarthak/PycharmProjects/references/grace/tests/test_pipeline_types.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pipeline_types.py
from __future__ import annotations

from pathlib import Path

from grace.pipeline.types import GenerationContext, GenerationResult, PspDocs


def test_psp_docs_local_file(tmp_path: Path) -> None:
    spec = tmp_path / "openapi.yaml"
    spec.write_text("openapi: 3.0.0")
    docs = PspDocs(source_uri=str(spec), source_kind="local_file", local_paths=[spec], content_bytes=None)
    assert docs.source_kind == "local_file"
    assert docs.local_paths == [spec]


def test_generation_context_construction(tmp_path: Path) -> None:
    ctx = GenerationContext(
        psp_name="cashfree",
        rulebook_paths=[tmp_path / "rb1.md"],
        psp_docs=PspDocs(source_uri="x", source_kind="url", local_paths=[], content_bytes=b"x"),
        output_dir=tmp_path / "out",
        target_module="lens.connectors.cashfree",
        lens_version_constraint="^0.1",
        grace_version="0.1.0",
        source_version="2024-09-01",
    )
    assert ctx.psp_name == "cashfree"
    assert ctx.target_module == "lens.connectors.cashfree"


def test_generation_result_carries_paths(tmp_path: Path) -> None:
    r = GenerationResult(
        output_dir=tmp_path,
        files_written=[tmp_path / "connector.py"],
        stdout="ok",
        stderr="",
        exit_code=0,
    )
    assert r.exit_code == 0
    assert r.files_written[0].name == "connector.py"
```

- [ ] **Step 2: Run the test, confirm it fails**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest tests/test_pipeline_types.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement**

```python
# src/grace/pipeline/__init__.py
from grace.pipeline.types import GenerationContext, GenerationResult, PspDocs

__all__ = ["GenerationContext", "GenerationResult", "PspDocs"]
```

```python
# src/grace/pipeline/types.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


SourceKind = Literal["url", "local_file", "local_dir"]


@dataclass(frozen=True)
class PspDocs:
    """A reference to the target PSP's API documentation, plus any cached content."""
    source_uri: str                       # original URL or path the user passed
    source_kind: SourceKind
    local_paths: list[Path] = field(default_factory=list)  # paths Claude can read
    content_bytes: bytes | None = None    # populated for URLs after fetch


@dataclass(frozen=True)
class GenerationContext:
    """Everything the pipeline needs to invoke Claude Code."""
    psp_name: str                                          # e.g., "cashfree"
    rulebook_paths: list[Path]                             # absolute paths to rulebook files
    psp_docs: PspDocs
    output_dir: Path                                       # working dir for Claude Code
    target_module: str                                     # e.g., "lens.connectors.cashfree"
    lens_version_constraint: str              # e.g., "^0.1"
    grace_version: str                                     # populated from package metadata
    source_version: str                                    # commit/timestamp written into marker


@dataclass(frozen=True)
class GenerationResult:
    """What the runner produces after Claude Code exits."""
    output_dir: Path
    files_written: list[Path]
    stdout: str
    stderr: str
    exit_code: int
```

- [ ] **Step 4: Run the test, confirm it passes**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest tests/test_pipeline_types.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace add src/grace/pipeline tests/test_pipeline_types.py
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "feat(pipeline): add GenerationContext + GenerationResult dataclasses"
```

**Validation criterion:** `pytest tests/test_pipeline_types.py` passes.

**Estimated effort:** 1 hr.

---

### Task 3.5: Context assembly — `pipeline/context.py`

**Files:**
- Create: `/Users/sarthak/PycharmProjects/references/grace/src/grace/pipeline/context.py`
- Create: `/Users/sarthak/PycharmProjects/references/grace/tests/test_pipeline_context.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pipeline_context.py
from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from grace.errors import GraceError, GraceErrorReason
from grace.pipeline.context import assemble_context, default_rulebook_paths, resolve_source


REPO_ROOT = Path(__file__).parent.parent


def test_default_rulebook_paths_returns_python_rulebook() -> None:
    paths = default_rulebook_paths(repo_root=REPO_ROOT)
    rels = {p.relative_to(REPO_ROOT).as_posix() for p in paths}
    assert "rulesbook/codegen/python/README.md" in rels
    assert "rulesbook/codegen/python/connector_abc.md" in rels
    assert "rulesbook/codegen/python/file_layout.md" in rels
    assert "rulesbook/codegen/python/marker.md" in rels


def test_resolve_source_local_file(tmp_path: Path) -> None:
    f = tmp_path / "openapi.yaml"
    f.write_text("openapi: 3.0.0")
    docs = resolve_source(str(f))
    assert docs.source_kind == "local_file"
    assert docs.local_paths == [f.resolve()]


def test_resolve_source_local_dir(tmp_path: Path) -> None:
    (tmp_path / "a.yaml").write_text("x: 1")
    (tmp_path / "b.md").write_text("hello")
    docs = resolve_source(str(tmp_path))
    assert docs.source_kind == "local_dir"
    assert len(docs.local_paths) == 2


def test_resolve_source_url_fetches(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get(url: str, **kwargs: object) -> httpx.Response:
        req = httpx.Request("GET", url)
        return httpx.Response(200, text="openapi: 3.0.0", request=req)
    monkeypatch.setattr(httpx, "get", mock_get)
    docs = resolve_source("https://example.com/openapi.yaml")
    assert docs.source_kind == "url"
    assert docs.content_bytes == b"openapi: 3.0.0"


def test_resolve_source_url_404_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get(url: str, **kwargs: object) -> httpx.Response:
        req = httpx.Request("GET", url)
        return httpx.Response(404, text="not found", request=req)
    monkeypatch.setattr(httpx, "get", mock_get)
    with pytest.raises(GraceError) as exc:
        resolve_source("https://example.com/missing")
    assert exc.value.reason is GraceErrorReason.SOURCE_FETCH_FAILED


def test_assemble_context_end_to_end(tmp_path: Path) -> None:
    spec = tmp_path / "openapi.yaml"
    spec.write_text("openapi: 3.0.0")
    ctx = assemble_context(
        psp_name="cashfree",
        source=str(spec),
        output_dir=tmp_path / "out",
        lens_version_constraint="^0.1",
        grace_version="0.1.0",
        source_version="2024-09-01",
        repo_root=REPO_ROOT,
    )
    assert ctx.psp_name == "cashfree"
    assert ctx.target_module == "lens.connectors.cashfree"
    assert (tmp_path / "out").is_dir()
    assert any("python/connector_abc.md" in p.as_posix() for p in ctx.rulebook_paths)
```

- [ ] **Step 2: Run the test, confirm it fails**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest tests/test_pipeline_context.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement**

```python
# src/grace/pipeline/context.py
from __future__ import annotations

from pathlib import Path

import httpx

from grace.errors import GraceError, GraceErrorReason
from grace.pipeline.types import GenerationContext, PspDocs


RULEBOOK_FILES = [
    "rulesbook/codegen/python/README.md",
    "rulesbook/codegen/python/ground_rules.md",
    "rulesbook/codegen/python/connector_abc.md",
    "rulesbook/codegen/python/domain_types.md",
    "rulesbook/codegen/python/file_layout.md",
    "rulesbook/codegen/python/status_mapping.md",
    "rulesbook/codegen/python/webhook_handling.md",
    "rulesbook/codegen/python/testing.md",
    "rulesbook/codegen/python/marker.md",
    "rulesbook/codegen/guides/patterns/pattern_createorder.md",
    "rulesbook/codegen/guides/patterns/pattern_psync.md",
    "rulesbook/codegen/guides/patterns/pattern_refund.md",
    "rulesbook/codegen/guides/patterns/pattern_rsync.md",
    "rulesbook/codegen/guides/patterns/pattern_IncomingWebhook_flow.md",
]


def default_rulebook_paths(*, repo_root: Path) -> list[Path]:
    """Return absolute paths to every rulebook file Claude Code should read."""
    paths: list[Path] = []
    for rel in RULEBOOK_FILES:
        p = (repo_root / rel).resolve()
        if not p.exists():
            raise GraceError(
                reason=GraceErrorReason.CONTEXT_BUNDLE_INVALID,
                detail=f"rulebook file missing: {p}",
            )
        paths.append(p)
    return paths


def resolve_source(source: str) -> PspDocs:
    """Resolve `source` into a PspDocs.

    Accepts: a URL (http/https), a local file path, or a local directory.
    """
    if source.startswith(("http://", "https://")):
        try:
            resp = httpx.get(source, timeout=30.0, follow_redirects=True)
        except httpx.HTTPError as e:
            raise GraceError(reason=GraceErrorReason.SOURCE_FETCH_FAILED, detail=str(e)) from e
        if resp.status_code >= 400:
            raise GraceError(
                reason=GraceErrorReason.SOURCE_FETCH_FAILED,
                detail=f"GET {source} -> HTTP {resp.status_code}",
            )
        return PspDocs(
            source_uri=source,
            source_kind="url",
            local_paths=[],
            content_bytes=resp.content,
        )

    p = Path(source).expanduser().resolve()
    if not p.exists():
        raise GraceError(
            reason=GraceErrorReason.SOURCE_FETCH_FAILED,
            detail=f"source not found: {p}",
        )
    if p.is_file():
        return PspDocs(source_uri=str(p), source_kind="local_file", local_paths=[p])
    return PspDocs(
        source_uri=str(p),
        source_kind="local_dir",
        local_paths=sorted(child.resolve() for child in p.iterdir() if child.is_file()),
    )


def assemble_context(
    *,
    psp_name: str,
    source: str,
    output_dir: Path,
    lens_version_constraint: str,
    grace_version: str,
    source_version: str,
    repo_root: Path,
) -> GenerationContext:
    """Build the full GenerationContext for a generate run."""
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return GenerationContext(
        psp_name=psp_name,
        rulebook_paths=default_rulebook_paths(repo_root=repo_root),
        psp_docs=resolve_source(source),
        output_dir=output_dir,
        target_module=f"lens.connectors.{psp_name}",
        lens_version_constraint=lens_version_constraint,
        grace_version=grace_version,
        source_version=source_version,
    )
```

- [ ] **Step 4: Run the test, confirm it passes**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest tests/test_pipeline_context.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace add src/grace/pipeline/context.py tests/test_pipeline_context.py
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "feat(pipeline): add context assembly (rulebook + PSP source resolution)"
```

**Validation criterion:** `pytest tests/test_pipeline_context.py` passes; all six rulebook references resolve.

**Estimated effort:** 3 hr.

---

### Task 3.6: `ClaudeCodeRunner`

**Files:**
- Create: `/Users/sarthak/PycharmProjects/references/grace/src/grace/pipeline/runner.py`
- Create: `/Users/sarthak/PycharmProjects/references/grace/src/grace/pipeline/prompt.py`
- Create: `/Users/sarthak/PycharmProjects/references/grace/tests/test_pipeline_runner.py`

- [ ] **Step 1: Write the prompt builder first**

```python
# src/grace/pipeline/prompt.py
from __future__ import annotations

from grace.pipeline.types import GenerationContext


PROMPT_TEMPLATE = """\
You are generating a Python PSP connector for the Orbit Lens.

Target package layout (you will create these files in the current working directory):

  __init__.py
  connector.py
  auth.py
  models.py
  status_map.py
  tests/test_create_order.py
  tests/test_sync_payment.py
  tests/test_refund.py
  tests/test_sync_refund.py
  tests/test_webhook.py

Hard constraints:
  1. Every .py file MUST start with the generated-file marker exactly as defined in the rulebook.
  2. The class implements the locked Connector ABC. Do not rename properties or methods.
  3. Use only the domain types from lens.domain_types and lens.enums.
  4. mypy --strict must be clean. No `Any`.
  5. Tests use httpx.MockTransport. Do not hit live PSPs.
  6. PSP-specific status terms must be mapped through status_map.py into PaymentAttemptStatus + PaymentFailureCode.

Context — read these files in order:
{rulebook_block}

PSP source — the target PSP's documentation:
{source_block}

Target module: {target_module}
Generator version: grace {grace_version}
Source version: {source_version}
Lens version constraint: {lens_version_constraint}

Generate the package. Do not ask follow-up questions. Write the files and exit.
"""


def build_prompt(ctx: GenerationContext) -> str:
    rulebook_block = "\n".join(f"  - {p}" for p in ctx.rulebook_paths)
    if ctx.psp_docs.source_kind == "url":
        source_block = (
            f"  - URL: {ctx.psp_docs.source_uri}\n"
            f"  - Content fetched at generation time (use the Read tool on the cached file: see CWD)."
        )
    else:
        source_block = "\n".join(f"  - {p}" for p in ctx.psp_docs.local_paths)
    return PROMPT_TEMPLATE.format(
        rulebook_block=rulebook_block,
        source_block=source_block,
        target_module=ctx.target_module,
        grace_version=ctx.grace_version,
        source_version=ctx.source_version,
        lens_version_constraint=ctx.lens_version_constraint,
    )
```

- [ ] **Step 2: Write the failing test for the runner**

```python
# tests/test_pipeline_runner.py
from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from grace.errors import GraceError, GraceErrorReason
from grace.pipeline.runner import ClaudeCodeRunner
from grace.pipeline.types import GenerationContext, PspDocs


@pytest.fixture
def fake_ctx(tmp_path: Path) -> GenerationContext:
    rb = tmp_path / "rb.md"
    rb.write_text("# rulebook")
    return GenerationContext(
        psp_name="cashfree",
        rulebook_paths=[rb],
        psp_docs=PspDocs(source_uri=str(rb), source_kind="local_file", local_paths=[rb]),
        output_dir=tmp_path / "out",
        target_module="lens.connectors.cashfree",
        lens_version_constraint="^0.1",
        grace_version="0.1.0",
        source_version="2024-09-01",
    )


def test_is_available_missing_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: None)
    healthy, detail = asyncio.run(ClaudeCodeRunner().is_available())
    assert healthy is False
    assert "not found" in detail.lower()


def test_is_available_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    binary = tmp_path / "claude"
    binary.write_text("#!/bin/sh\nexit 0")
    binary.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda _: str(binary))

    class _Proc:
        returncode = 0
        async def communicate(self, _input: bytes | None = None) -> tuple[bytes, bytes]:
            return (b"Claude Code v0.1.0", b"")

    async def _exec(*a: Any, **k: Any) -> _Proc:
        return _Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)

    healthy, detail = asyncio.run(ClaudeCodeRunner().is_available())
    assert healthy is True


def test_generate_raises_when_binary_missing(monkeypatch: pytest.MonkeyPatch, fake_ctx: GenerationContext) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(GraceError) as exc:
        asyncio.run(ClaudeCodeRunner().generate(fake_ctx))
    assert exc.value.reason is GraceErrorReason.CLAUDE_CODE_NOT_FOUND


def test_generate_raises_on_timeout(monkeypatch: pytest.MonkeyPatch, fake_ctx: GenerationContext, tmp_path: Path) -> None:
    binary = tmp_path / "claude"
    binary.write_text("#!/bin/sh\nsleep 60")
    binary.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda _: str(binary))

    class _Proc:
        returncode: int | None = None
        async def communicate(self, _input: bytes | None = None) -> tuple[bytes, bytes]:
            raise TimeoutError("simulated")
        def kill(self) -> None: ...
        async def wait(self) -> int:
            return -9

    async def _exec(*a: Any, **k: Any) -> _Proc:
        return _Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)

    with pytest.raises(GraceError) as exc:
        asyncio.run(ClaudeCodeRunner(timeout_s=0.05).generate(fake_ctx))
    assert exc.value.reason is GraceErrorReason.CLAUDE_CODE_TIMEOUT


def test_generate_raises_on_nonzero_exit(monkeypatch: pytest.MonkeyPatch, fake_ctx: GenerationContext, tmp_path: Path) -> None:
    binary = tmp_path / "claude"
    binary.write_text("#!/bin/sh\nexit 2")
    binary.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda _: str(binary))

    class _Proc:
        returncode = 2
        async def communicate(self, _input: bytes | None = None) -> tuple[bytes, bytes]:
            return (b"bad", b"auth error")

    async def _exec(*a: Any, **k: Any) -> _Proc:
        return _Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _exec)

    with pytest.raises(GraceError) as exc:
        asyncio.run(ClaudeCodeRunner().generate(fake_ctx))
    assert exc.value.reason in {GraceErrorReason.CLAUDE_CODE_FAILED, GraceErrorReason.CLAUDE_CODE_NOT_AUTHENTICATED}
```

- [ ] **Step 3: Run the test, confirm it fails**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest tests/test_pipeline_runner.py -v
```
Expected: ImportError.

- [ ] **Step 4: Implement the runner**

```python
# src/grace/pipeline/runner.py
from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass
from pathlib import Path

from grace.errors import GraceError, GraceErrorReason
from grace.pipeline.prompt import build_prompt
from grace.pipeline.types import GenerationContext, GenerationResult


@dataclass(frozen=True)
class ClaudeCodeRunner:
    """Invokes the local Claude Code CLI to generate a connector package.

    There is exactly one AI backend. No abstraction. No registry. No fallback.
    """
    cli_path: Path | None = None
    timeout_s: float = 1800.0

    def _resolve_binary(self) -> Path:
        if self.cli_path is not None:
            if not self.cli_path.exists():
                raise GraceError(
                    reason=GraceErrorReason.CLAUDE_CODE_NOT_FOUND,
                    detail=f"configured cli_path does not exist: {self.cli_path}",
                )
            return self.cli_path
        found = shutil.which("claude")
        if found is None:
            raise GraceError(
                reason=GraceErrorReason.CLAUDE_CODE_NOT_FOUND,
                detail="`claude` binary not found in PATH; install Claude Code first",
            )
        return Path(found)

    async def is_available(self) -> tuple[bool, str]:
        """For `grace doctor`. Returns (healthy, detail)."""
        try:
            binary = self._resolve_binary()
        except GraceError as e:
            return (False, e.detail or e.reason.value)
        try:
            proc = await asyncio.create_subprocess_exec(
                str(binary), "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        except (TimeoutError, asyncio.TimeoutError):
            return (False, "claude --version timed out")
        except OSError as e:
            return (False, f"failed to spawn claude: {e}")
        if proc.returncode != 0:
            return (False, (stderr or stdout).decode(errors="replace").strip() or "non-zero exit")
        return (True, stdout.decode(errors="replace").strip())

    async def generate(self, context: GenerationContext) -> GenerationResult:
        """Spawn Claude Code in `context.output_dir` with the assembled prompt as stdin."""
        binary = self._resolve_binary()
        prompt = build_prompt(context)
        context.output_dir.mkdir(parents=True, exist_ok=True)

        # If the source is a URL, dump the fetched bytes into the output dir so Claude can read it.
        if context.psp_docs.source_kind == "url" and context.psp_docs.content_bytes is not None:
            cached = context.output_dir / "_psp_source_cache"
            cached.write_bytes(context.psp_docs.content_bytes)

        # Headless invocation: feed the prompt via stdin; expect Claude to write files.
        proc = await asyncio.create_subprocess_exec(
            str(binary), "-p", "--permission-mode", "acceptEdits",
            cwd=str(context.output_dir),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=prompt.encode("utf-8")),
                timeout=self.timeout_s,
            )
        except (TimeoutError, asyncio.TimeoutError) as e:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            await proc.wait()
            raise GraceError(
                reason=GraceErrorReason.CLAUDE_CODE_TIMEOUT,
                detail=f"claude did not finish within {self.timeout_s}s",
            ) from e

        rc = proc.returncode or 0
        stderr_text = stderr.decode(errors="replace")
        stdout_text = stdout.decode(errors="replace")
        if rc != 0:
            reason = (
                GraceErrorReason.CLAUDE_CODE_NOT_AUTHENTICATED
                if "auth" in stderr_text.lower() or "login" in stderr_text.lower()
                else GraceErrorReason.CLAUDE_CODE_FAILED
            )
            raise GraceError(reason=reason, detail=stderr_text.strip() or stdout_text.strip())

        files = sorted(p for p in context.output_dir.rglob("*.py"))
        return GenerationResult(
            output_dir=context.output_dir,
            files_written=files,
            stdout=stdout_text,
            stderr=stderr_text,
            exit_code=rc,
        )
```

- [ ] **Step 5: Run the runner tests**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest tests/test_pipeline_runner.py -v
```
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace add src/grace/pipeline/prompt.py src/grace/pipeline/runner.py tests/test_pipeline_runner.py
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "feat(pipeline): add ClaudeCodeRunner + prompt builder"
```

**Validation criterion:** `pytest tests/test_pipeline_runner.py` passes. The runner has zero references to `openai`, `anthropic`, `litellm`, or any provider-abstraction concept.

**Estimated effort:** 4 hr.

---

### Task 3.7: Marker emission post-processor

Claude is told via the rulebook to emit the marker, but the rubric will score it deterministically. As belt-and-suspenders, Grace post-processes any .py file that's missing a well-formed marker and prepends one. This is the "Grace adds the marker" enforcement.

**Files:**
- Create: `/Users/sarthak/PycharmProjects/references/grace/src/grace/pipeline/marker.py`
- Create: `/Users/sarthak/PycharmProjects/references/grace/tests/test_pipeline_marker.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_pipeline_marker.py
from __future__ import annotations

from pathlib import Path

from grace.pipeline.marker import has_marker, render_marker, ensure_marker


def test_render_marker_seven_lines() -> None:
    text = render_marker(
        psp_name="cashfree",
        source_version="v1",
        generated_utc_iso8601="2026-05-20T12:00:00Z",
        grace_version="0.1.0",
        source_uri="https://docs.cashfree.com/openapi.yaml",
    )
    lines = text.splitlines()
    assert len(lines) == 7
    assert lines[1] == "#  DO NOT EDIT — autogenerated by Grace."


def test_has_marker_recognizes_well_formed(tmp_path: Path) -> None:
    p = tmp_path / "x.py"
    p.write_text(
        "# ──────────────────────────────────────────────────────────────────────\n"
        "#  DO NOT EDIT — autogenerated by Grace.\n"
        "#  Source: cashfree v1\n"
        "#  Generated: 2026-05-20T12:00:00Z\n"
        "#  Generator: grace 0.1.0\n"
        "#  Regenerate: grace generate cashfree --from x\n"
        "# ──────────────────────────────────────────────────────────────────────\n"
        "\n"
        "x = 1\n"
    )
    assert has_marker(p) is True


def test_has_marker_rejects_missing(tmp_path: Path) -> None:
    p = tmp_path / "x.py"
    p.write_text("x = 1\n")
    assert has_marker(p) is False


def test_ensure_marker_prepends_when_absent(tmp_path: Path) -> None:
    p = tmp_path / "x.py"
    p.write_text("x = 1\n")
    ensure_marker(
        p,
        psp_name="cashfree", source_version="v1",
        generated_utc_iso8601="2026-05-20T12:00:00Z", grace_version="0.1.0",
        source_uri="x",
    )
    text = p.read_text()
    assert text.startswith("# ─")
    assert "x = 1" in text


def test_ensure_marker_idempotent(tmp_path: Path) -> None:
    p = tmp_path / "x.py"
    p.write_text("x = 1\n")
    args = dict(
        psp_name="cashfree", source_version="v1",
        generated_utc_iso8601="2026-05-20T12:00:00Z", grace_version="0.1.0",
        source_uri="x",
    )
    ensure_marker(p, **args)  # type: ignore[arg-type]
    once = p.read_text()
    ensure_marker(p, **args)  # type: ignore[arg-type]
    twice = p.read_text()
    assert once == twice
```

- [ ] **Step 2: Run, confirm fail**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest tests/test_pipeline_marker.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement**

```python
# src/grace/pipeline/marker.py
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import jinja2

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(_TEMPLATE_DIR),
    keep_trailing_newline=True,
    autoescape=False,
)


def render_marker(
    *,
    psp_name: str,
    source_version: str,
    generated_utc_iso8601: str | None = None,
    grace_version: str,
    source_uri: str,
) -> str:
    ts = generated_utc_iso8601 or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return _env.get_template("marker.j2").render(
        psp_name=psp_name,
        source_version=source_version,
        generated_utc_iso8601=ts,
        grace_version=grace_version,
        source_uri=source_uri,
    )


def has_marker(path: Path) -> bool:
    """Return True iff the first non-empty content of `path` is a well-formed marker block."""
    lines = path.read_text().splitlines()
    if len(lines) < 7:
        return False
    if not lines[0].startswith("# ─"):
        return False
    if lines[1].strip() != "#  DO NOT EDIT — autogenerated by Grace.":
        return False
    for i, prefix in enumerate(("#  Source:", "#  Generated:", "#  Generator:", "#  Regenerate:"), start=2):
        if not lines[i].startswith(prefix):
            return False
    if not lines[6].startswith("# ─"):
        return False
    return True


def ensure_marker(
    path: Path,
    *,
    psp_name: str,
    source_version: str,
    generated_utc_iso8601: str | None = None,
    grace_version: str,
    source_uri: str,
) -> None:
    if has_marker(path):
        return
    marker = render_marker(
        psp_name=psp_name,
        source_version=source_version,
        generated_utc_iso8601=generated_utc_iso8601,
        grace_version=grace_version,
        source_uri=source_uri,
    )
    body = path.read_text()
    path.write_text(marker + "\n" + body if not marker.endswith("\n") else marker + body)
```

- [ ] **Step 4: Run, confirm pass**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest tests/test_pipeline_marker.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace add src/grace/pipeline/marker.py tests/test_pipeline_marker.py
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "feat(pipeline): add marker render/detect/ensure helpers"
```

**Validation criterion:** `pytest tests/test_pipeline_marker.py` passes.

**Estimated effort:** 1.5 hr.

---

### Task 3.8: Pipeline orchestration `pipeline/__init__.py`

**Files:**
- Modify: `/Users/sarthak/PycharmProjects/references/grace/src/grace/pipeline/__init__.py`
- Create: `/Users/sarthak/PycharmProjects/references/grace/src/grace/pipeline/orchestrate.py`
- Create: `/Users/sarthak/PycharmProjects/references/grace/tests/test_pipeline_orchestrate.py`

- [ ] **Step 1: Failing test (uses a stub runner)**

```python
# tests/test_pipeline_orchestrate.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import pytest

from grace.pipeline.orchestrate import run_pipeline, PipelineHooks
from grace.pipeline.types import GenerationContext, GenerationResult, PspDocs


@dataclass
class _StubRunner:
    files_to_create: list[tuple[str, str]]
    async def is_available(self) -> tuple[bool, str]:
        return (True, "ok")
    async def generate(self, ctx: GenerationContext) -> GenerationResult:
        written: list[Path] = []
        for name, body in self.files_to_create:
            p = ctx.output_dir / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body)
            written.append(p)
        return GenerationResult(output_dir=ctx.output_dir, files_written=written, stdout="", stderr="", exit_code=0)


@pytest.fixture
def stub_ctx(tmp_path: Path) -> GenerationContext:
    rb = tmp_path / "rb.md"; rb.write_text("rb")
    return GenerationContext(
        psp_name="cashfree",
        rulebook_paths=[rb],
        psp_docs=PspDocs(source_uri="x", source_kind="local_file", local_paths=[rb]),
        output_dir=tmp_path / "out",
        target_module="lens.connectors.cashfree",
        lens_version_constraint="^0.1",
        grace_version="0.1.0",
        source_version="2024-09-01",
    )


def test_run_pipeline_post_processes_marker(stub_ctx: GenerationContext) -> None:
    runner = _StubRunner(files_to_create=[("connector.py", "x = 1\n")])
    asyncio.run(run_pipeline(ctx=stub_ctx, runner=runner, hooks=PipelineHooks(run_gates=False)))
    out = (stub_ctx.output_dir / "connector.py").read_text()
    assert out.startswith("# ─")
    assert "x = 1" in out


def test_run_pipeline_skips_existing_marker(stub_ctx: GenerationContext) -> None:
    marker = (
        "# ──────────────────────────────────────────────────────────────────────\n"
        "#  DO NOT EDIT — autogenerated by Grace.\n"
        "#  Source: cashfree 2024-09-01\n"
        "#  Generated: 2026-05-20T12:00:00Z\n"
        "#  Generator: grace 0.1.0\n"
        "#  Regenerate: grace generate cashfree --from x\n"
        "# ──────────────────────────────────────────────────────────────────────\n"
    )
    runner = _StubRunner(files_to_create=[("connector.py", marker + "\nx = 1\n")])
    asyncio.run(run_pipeline(ctx=stub_ctx, runner=runner, hooks=PipelineHooks(run_gates=False)))
    out = (stub_ctx.output_dir / "connector.py").read_text()
    assert out.count("DO NOT EDIT — autogenerated by Grace.") == 1
```

- [ ] **Step 2: Implement**

```python
# src/grace/pipeline/orchestrate.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from grace.pipeline.marker import ensure_marker
from grace.pipeline.types import GenerationContext, GenerationResult


class _RunnerProto(Protocol):
    async def is_available(self) -> tuple[bool, str]: ...
    async def generate(self, ctx: GenerationContext) -> GenerationResult: ...


@dataclass(frozen=True)
class PipelineHooks:
    run_gates: bool = True
    """Set False for tests that only exercise marker-ensure + orchestration."""


async def run_pipeline(
    *,
    ctx: GenerationContext,
    runner: _RunnerProto,
    hooks: PipelineHooks = PipelineHooks(),
) -> GenerationResult:
    """Three-step pipeline: context → invoke → gates.

    Context assembly happens upstream of this function (callers use
    grace.pipeline.context.assemble_context). This function:
      1. Calls runner.generate(ctx).
      2. Post-processes any emitted .py file missing a marker.
      3. (Optional) runs quality gates — implemented in pipeline/gates.py.
    """
    result = await runner.generate(ctx)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for p in result.output_dir.rglob("*.py"):
        ensure_marker(
            p,
            psp_name=ctx.psp_name,
            source_version=ctx.source_version,
            generated_utc_iso8601=generated_at,
            grace_version=ctx.grace_version,
            source_uri=ctx.psp_docs.source_uri,
        )

    if hooks.run_gates:
        from grace.pipeline.gates import run_gates_blocking
        run_gates_blocking(ctx=ctx, result=result)

    return result
```

```python
# src/grace/pipeline/__init__.py  (replace)
from grace.pipeline.orchestrate import PipelineHooks, run_pipeline
from grace.pipeline.types import GenerationContext, GenerationResult, PspDocs

__all__ = [
    "GenerationContext",
    "GenerationResult",
    "PspDocs",
    "PipelineHooks",
    "run_pipeline",
]
```

(`gates.py` is added in Step 4 below; the `run_gates=False` path lets us unit-test orchestration ahead of that.)

- [ ] **Step 3: Run, confirm pass**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest tests/test_pipeline_orchestrate.py -v
```
Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace add src/grace/pipeline/orchestrate.py src/grace/pipeline/__init__.py tests/test_pipeline_orchestrate.py
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "feat(pipeline): orchestrate context → invoke → ensure-marker → gates"
```

**Validation criterion:** `pytest tests/test_pipeline_orchestrate.py` passes; gates module not yet present but pipeline is importable.

**Estimated effort:** 2 hr.

---

### Task 3.9: CLI — `grace doctor`, `grace generate`, `grace regenerate`, `grace --version`

**Files:**
- Create: `/Users/sarthak/PycharmProjects/references/grace/src/grace/cli.py`
- Create: `/Users/sarthak/PycharmProjects/references/grace/tests/test_cli.py`

- [ ] **Step 1: Failing test using Click's `CliRunner`**

```python
# tests/test_cli.py
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner

from grace.cli import main


def test_version_flag() -> None:
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "grace" in result.output.lower()


def test_doctor_reports_status(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_is_available(self: object) -> tuple[bool, str]:
        return (True, "Claude Code v0.1.0")
    monkeypatch.setattr("grace.pipeline.runner.ClaudeCodeRunner.is_available", fake_is_available)
    result = CliRunner().invoke(main, ["doctor"])
    assert result.exit_code == 0
    assert "healthy" in result.output.lower() or "ok" in result.output.lower()


def test_doctor_reports_unhealthy(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_is_available(self: object) -> tuple[bool, str]:
        return (False, "binary not found")
    monkeypatch.setattr("grace.pipeline.runner.ClaudeCodeRunner.is_available", fake_is_available)
    result = CliRunner().invoke(main, ["doctor"])
    assert result.exit_code == 1
    assert "binary not found" in result.output


def test_generate_calls_pipeline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    called: dict[str, object] = {}
    async def fake_run_pipeline(*, ctx: object, runner: object, hooks: object) -> None:
        called["psp"] = ctx.psp_name  # type: ignore[attr-defined]
        called["target"] = ctx.target_module  # type: ignore[attr-defined]
        return None
    monkeypatch.setattr("grace.cli._run_pipeline", fake_run_pipeline)

    spec = tmp_path / "openapi.yaml"
    spec.write_text("openapi: 3.0.0")
    out = tmp_path / "out"
    result = CliRunner().invoke(main, ["generate", "cashfree", "--from", str(spec), "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert called["psp"] == "cashfree"
    assert called["target"] == "lens.connectors.cashfree"
```

- [ ] **Step 2: Implement**

```python
# src/grace/cli.py
from __future__ import annotations

import asyncio
import importlib.metadata
import json
from pathlib import Path
from typing import Any

import click

from grace.config import load_config
from grace.errors import GraceError
from grace.pipeline import GenerationContext, PipelineHooks, run_pipeline
from grace.pipeline.context import assemble_context
from grace.pipeline.runner import ClaudeCodeRunner


def _grace_version() -> str:
    try:
        return importlib.metadata.version("grace-cli")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0+local"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent  # src/grace/cli.py → repo root


def _last_run_path() -> Path:
    return Path.home() / ".grace" / "last_run.json"


def _save_last_run(*, psp: str, source: str, output: Path) -> None:
    p = _last_run_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"psp": psp, "source": source, "output": str(output)}))


def _load_last_run(psp: str) -> dict[str, str]:
    p = _last_run_path()
    if not p.exists():
        raise click.ClickException("no previous run on record (run `grace generate` first)")
    data: Any = json.loads(p.read_text())
    if not isinstance(data, dict) or data.get("psp") != psp:
        raise click.ClickException(f"no previous run for {psp}")
    return {str(k): str(v) for k, v in data.items()}


async def _run_pipeline(*, ctx: GenerationContext, runner: ClaudeCodeRunner, hooks: PipelineHooks) -> None:
    await run_pipeline(ctx=ctx, runner=runner, hooks=hooks)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=_grace_version(), prog_name="grace")
def main() -> None:
    """Grace — generate Python PSP connectors for the Orbit Lens."""


@main.command()
def doctor() -> None:
    """Check whether Claude Code is reachable."""
    cfg = load_config()
    runner = ClaudeCodeRunner(cli_path=cfg.claude_code.cli_path, timeout_s=cfg.claude_code.timeout_s)
    healthy, detail = asyncio.run(runner.is_available())
    if healthy:
        click.echo(f"healthy: {detail}")
        raise SystemExit(0)
    click.echo(f"unhealthy: {detail}", err=False)
    raise SystemExit(1)


@main.command()
@click.argument("psp")
@click.option("--from", "source", required=True, help="URL, local file, or local directory of PSP docs.")
@click.option("--output", "output", type=click.Path(path_type=Path), default=None,
              help="Output directory. Defaults to ./lens/connectors/<psp>/.")
@click.option("--config", "config", type=click.Path(path_type=Path), default=None,
              help="Path to grace config.yaml; defaults to ~/.grace/config.yaml.")
def generate(psp: str, source: str, output: Path | None, config: Path | None) -> None:
    """Generate a connector package for PSP from the given source."""
    cfg = load_config(config_path=config)
    out = output or (Path.cwd() / "lens" / "connectors" / psp)
    try:
        ctx = assemble_context(
            psp_name=psp,
            source=source,
            output_dir=out,
            lens_version_constraint=cfg.lens.version_constraint,
            grace_version=_grace_version(),
            source_version=source,  # for v1, the URL/path stands as the source version
            repo_root=_repo_root(),
        )
        runner = ClaudeCodeRunner(cli_path=cfg.claude_code.cli_path, timeout_s=cfg.claude_code.timeout_s)
        asyncio.run(_run_pipeline(ctx=ctx, runner=runner, hooks=PipelineHooks(run_gates=True)))
        _save_last_run(psp=psp, source=source, output=out)
        click.echo(f"OK: wrote {out}")
    except GraceError as e:
        raise click.ClickException(f"{e.reason.value}: {e.detail or ''}")


@main.command()
@click.argument("psp")
def regenerate(psp: str) -> None:
    """Re-run the previous `generate` invocation for PSP with the same args."""
    last = _load_last_run(psp)
    ctx_args = ["generate", psp, "--from", last["source"], "--output", last["output"]]
    ctx = click.get_current_context()
    ctx.invoke(generate, psp=psp, source=last["source"], output=Path(last["output"]), config=None)
```

- [ ] **Step 3: Run, confirm pass**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest tests/test_cli.py -v
```
Expected: 4 passed.

- [ ] **Step 4: Quick smoke test**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run grace --version
cd /Users/sarthak/PycharmProjects/references/grace && uv run grace --help
```
Expected: prints version and the three subcommands (`doctor`, `generate`, `regenerate`).

- [ ] **Step 5: Commit**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace add src/grace/cli.py tests/test_cli.py
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "feat(cli): add doctor / generate / regenerate / --version"
```

**Validation criterion:** `uv run grace --help` shows the four expected commands; `pytest tests/test_cli.py` passes.

**Estimated effort:** 3 hr.

---

## Step 4 — Quality gates + 6-dimension rubric

The pipeline orchestrator imports `run_gates_blocking` from `pipeline/gates.py`. Build it now. The rubric lives in `grace.quality_rubric` per the sub-project §3 layout.

### Task 4.1: Subprocess wrappers — `mypy` and `pytest --cov`

**Files:**
- Create: `/Users/sarthak/PycharmProjects/references/grace/src/grace/pipeline/gates.py`
- Create: `/Users/sarthak/PycharmProjects/references/grace/tests/test_pipeline_gates.py`

- [ ] **Step 1: Failing test (uses fake mypy/pytest scripts)**

```python
# tests/test_pipeline_gates.py
from __future__ import annotations

from pathlib import Path

import pytest

from grace.errors import GraceError, GraceErrorReason
from grace.pipeline.gates import run_mypy, run_pytest_with_cov


def _make_clean_pkg(root: Path) -> Path:
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("x: int = 1\n")
    return pkg


def _make_broken_pkg(root: Path) -> Path:
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("x: int = 'oops'\n")
    return pkg


def test_run_mypy_clean(tmp_path: Path) -> None:
    pkg = _make_clean_pkg(tmp_path)
    report = run_mypy(target=pkg, strict=True)
    assert report.passed is True


def test_run_mypy_fails_on_type_error(tmp_path: Path) -> None:
    pkg = _make_broken_pkg(tmp_path)
    report = run_mypy(target=pkg, strict=True)
    assert report.passed is False
    assert "incompatible" in report.stdout.lower() or "error" in report.stdout.lower()


def test_run_pytest_with_cov_no_tests(tmp_path: Path) -> None:
    pkg = _make_clean_pkg(tmp_path)
    report = run_pytest_with_cov(target=pkg)
    assert report.coverage_pct == 0.0 or report.coverage_pct is None
```

- [ ] **Step 2: Implement**

```python
# src/grace/pipeline/gates.py
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from grace.errors import GraceError, GraceErrorReason
from grace.pipeline.types import GenerationContext, GenerationResult


@dataclass(frozen=True)
class MypyReport:
    passed: bool
    stdout: str
    stderr: str


@dataclass(frozen=True)
class PytestReport:
    passed: bool
    coverage_pct: float | None
    stdout: str
    stderr: str


def run_mypy(*, target: Path, strict: bool = True) -> MypyReport:
    """Invoke `mypy --strict <target>` (or non-strict) as a subprocess."""
    cmd = [sys.executable, "-m", "mypy"]
    if strict:
        cmd.append("--strict")
    cmd.append(str(target))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return MypyReport(passed=proc.returncode == 0, stdout=proc.stdout, stderr=proc.stderr)


def run_pytest_with_cov(*, target: Path) -> PytestReport:
    """Invoke pytest with coverage on the target package; parse the JSON report."""
    json_report = target.parent / "_grace_coverage.json"
    cmd = [
        sys.executable, "-m", "pytest",
        "--cov", str(target),
        "--cov-report", f"json:{json_report}",
        "-q",
        str(target),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    pct: float | None = None
    if json_report.exists():
        try:
            data = json.loads(json_report.read_text())
            pct = float(data.get("totals", {}).get("percent_covered", 0.0))
        except (ValueError, OSError):
            pct = None
    # pytest exits 5 when no tests collected — treat as 0% rather than failure.
    passed = proc.returncode in (0, 5)
    return PytestReport(passed=passed, coverage_pct=pct, stdout=proc.stdout, stderr=proc.stderr)


def run_gates_blocking(*, ctx: GenerationContext, result: GenerationResult) -> None:
    """Run mypy + pytest + rubric. Raise GraceError if any gate fails."""
    from grace.quality_rubric import score_rubric, RubricReport  # late import to avoid cycle

    mypy_report = run_mypy(target=result.output_dir, strict=True)
    pytest_report = run_pytest_with_cov(target=result.output_dir)
    rubric: RubricReport = score_rubric(
        ctx=ctx,
        output_dir=result.output_dir,
        mypy_report=mypy_report,
        pytest_report=pytest_report,
    )
    # Always write the report next to the package.
    (result.output_dir / "quality_report.json").write_text(rubric.to_json())

    failures: list[str] = []
    if not mypy_report.passed:
        failures.append(f"mypy: {mypy_report.stdout.strip().splitlines()[-1] if mypy_report.stdout else 'failed'}")
    if pytest_report.coverage_pct is not None and pytest_report.coverage_pct < 80.0:
        failures.append(f"coverage: {pytest_report.coverage_pct:.1f}% < 80%")
    if rubric.total < 60:
        failures.append(f"rubric: {rubric.total} < 60")
    if failures:
        raise GraceError(
            reason=GraceErrorReason.QUALITY_GATE_FAILED,
            detail="; ".join(failures),
        )
```

- [ ] **Step 3: Add `pytest-cov` to dev deps**

Edit `pyproject.toml` — add `"pytest-cov>=5.0.0"` to the `dev` extra. Run `uv lock && uv sync --extra dev`.

- [ ] **Step 4: Run, confirm pass**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest tests/test_pipeline_gates.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace add src/grace/pipeline/gates.py tests/test_pipeline_gates.py pyproject.toml uv.lock
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "feat(gates): wrap mypy + pytest --cov as subprocesses"
```

**Validation criterion:** `pytest tests/test_pipeline_gates.py` passes; mypy and pytest both invokable on generated package layouts.

**Estimated effort:** 3 hr.

---

### Task 4.2: 6-dimension rubric — `grace.quality_rubric`

Per sub-project §5, score on six dimensions, ≥60/100 passes:
- Marker conformance (5)
- Type correctness (20)
- Test coverage (25)
- Public-surface conformance (20)
- Error handling (20)
- PII discipline (10)

**Files:**
- Create: `/Users/sarthak/PycharmProjects/references/grace/src/grace/quality_rubric.py`
- Create: `/Users/sarthak/PycharmProjects/references/grace/tests/test_quality_rubric.py`

- [ ] **Step 1: Failing test, six dimensions**

```python
# tests/test_quality_rubric.py
from __future__ import annotations

from pathlib import Path

import pytest

from grace.pipeline.gates import MypyReport, PytestReport
from grace.pipeline.types import GenerationContext, PspDocs
from grace.quality_rubric import score_rubric


def _ctx(tmp_path: Path) -> GenerationContext:
    rb = tmp_path / "rb.md"; rb.write_text("rb")
    return GenerationContext(
        psp_name="demo",
        rulebook_paths=[rb],
        psp_docs=PspDocs(source_uri="x", source_kind="local_file", local_paths=[rb]),
        output_dir=tmp_path / "pkg",
        target_module="lens.connectors.demo",
        lens_version_constraint="^0.1",
        grace_version="0.1.0",
        source_version="x",
    )


def _write_marker(p: Path, psp: str = "demo") -> None:
    p.write_text(
        "# ──────────────────────────────────────────────────────────────────────\n"
        "#  DO NOT EDIT — autogenerated by Grace.\n"
        f"#  Source: {psp} x\n"
        "#  Generated: 2026-05-20T12:00:00Z\n"
        "#  Generator: grace 0.1.0\n"
        f"#  Regenerate: grace generate {psp} --from x\n"
        "# ──────────────────────────────────────────────────────────────────────\n\n"
    )


def _scaffold_full_pkg(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name in ["__init__.py", "connector.py", "auth.py", "models.py", "status_map.py"]:
        f = out / name
        _write_marker(f)
        if name == "connector.py":
            f.write_text(f.read_text() +
                "from lens.connector import Connector\n"
                "class Demo(Connector):\n"
                "    async def create_order(self, request): ...\n"
                "    async def sync_payment(self, request): ...\n"
                "    async def refund(self, request): ...\n"
                "    async def sync_refund(self, request): ...\n"
                "    async def handle_webhook(self, raw_payload, headers): ...\n"
                "    async def close(self): ...\n"
            )
        elif name == "__init__.py":
            f.write_text(f.read_text() +
                "requires_lens = \"^0.1\"\n"
                "from .connector import Demo\n"
                "from lens.factory import ConnectorFactory\n"
                "ConnectorFactory.register(\"demo\", Demo)\n"
            )
        elif name == "auth.py":
            f.write_text(f.read_text() +
                "from lens.common import Maskable\n"
                "def sign(secret: Maskable[str], payload: bytes) -> str: ...\n"
            )
    tests = out / "tests"; tests.mkdir()
    for t in ["test_create_order.py", "test_sync_payment.py", "test_refund.py", "test_sync_refund.py", "test_webhook.py"]:
        f = tests / t; _write_marker(f)


def test_rubric_full_score_when_everything_is_clean(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    _scaffold_full_pkg(ctx.output_dir)
    report = score_rubric(
        ctx=ctx,
        output_dir=ctx.output_dir,
        mypy_report=MypyReport(passed=True, stdout="", stderr=""),
        pytest_report=PytestReport(passed=True, coverage_pct=95.0, stdout="", stderr=""),
    )
    assert report.total == 100, report.to_json()
    assert all(d.score == d.max for d in report.dimensions)


def test_rubric_marker_dimension_fails_when_marker_missing(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    _scaffold_full_pkg(ctx.output_dir)
    # break one file's marker
    (ctx.output_dir / "auth.py").write_text("def x(): ...\n")
    report = score_rubric(
        ctx=ctx, output_dir=ctx.output_dir,
        mypy_report=MypyReport(passed=True, stdout="", stderr=""),
        pytest_report=PytestReport(passed=True, coverage_pct=95.0, stdout="", stderr=""),
    )
    marker_dim = next(d for d in report.dimensions if d.name == "marker_conformance")
    assert marker_dim.score == 0


def test_rubric_public_surface_fails_when_class_missing(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    _scaffold_full_pkg(ctx.output_dir)
    (ctx.output_dir / "connector.py").write_text(
        "# ──────────────────────────────────────────────────────────────────────\n"
        "#  DO NOT EDIT — autogenerated by Grace.\n"
        "#  Source: demo x\n"
        "#  Generated: 2026-05-20T12:00:00Z\n"
        "#  Generator: grace 0.1.0\n"
        "#  Regenerate: grace generate demo --from x\n"
        "# ──────────────────────────────────────────────────────────────────────\n"
        "x = 1\n"
    )
    report = score_rubric(
        ctx=ctx, output_dir=ctx.output_dir,
        mypy_report=MypyReport(passed=True, stdout="", stderr=""),
        pytest_report=PytestReport(passed=True, coverage_pct=95.0, stdout="", stderr=""),
    )
    surface_dim = next(d for d in report.dimensions if d.name == "public_surface")
    assert surface_dim.score < surface_dim.max


def test_rubric_passes_with_60(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    _scaffold_full_pkg(ctx.output_dir)
    report = score_rubric(
        ctx=ctx, output_dir=ctx.output_dir,
        mypy_report=MypyReport(passed=False, stdout="", stderr=""),    # -20
        pytest_report=PytestReport(passed=True, coverage_pct=50.0, stdout="", stderr=""),  # -25
    )
    assert report.total < 100
    assert report.total >= 55  # marker 5 + surface 20 + error 20 + pii 10 = 55 worst case
```

- [ ] **Step 2: Implement**

```python
# src/grace/quality_rubric.py
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from grace.pipeline.gates import MypyReport, PytestReport
from grace.pipeline.marker import has_marker
from grace.pipeline.types import GenerationContext


@dataclass(frozen=True)
class Dimension:
    name: str
    max: int
    score: int
    detail: str


@dataclass(frozen=True)
class RubricReport:
    dimensions: list[Dimension]

    @property
    def total(self) -> int:
        return sum(d.score for d in self.dimensions)

    def to_json(self) -> str:
        return json.dumps(
            {
                "total": self.total,
                "passed": self.total >= 60,
                "dimensions": [
                    {"name": d.name, "max": d.max, "score": d.score, "detail": d.detail}
                    for d in self.dimensions
                ],
            },
            indent=2,
        )


# --- required public surface (per SUBPROJECT_GRACE_CODEGEN.md §3.2 + §5) ---
REQUIRED_FILES = ["__init__.py", "connector.py", "auth.py", "models.py", "status_map.py"]
REQUIRED_TEST_FILES = [
    "tests/test_create_order.py",
    "tests/test_sync_payment.py",
    "tests/test_refund.py",
    "tests/test_sync_refund.py",
    "tests/test_webhook.py",
]
REQUIRED_FLOW_METHODS = {"create_order", "sync_payment", "refund", "sync_refund", "handle_webhook", "close"}


def _score_marker(output_dir: Path) -> Dimension:
    py_files = list(output_dir.rglob("*.py"))
    if not py_files:
        return Dimension("marker_conformance", 5, 0, "no .py files emitted")
    missing = [str(p.relative_to(output_dir)) for p in py_files if not has_marker(p)]
    if missing:
        return Dimension("marker_conformance", 5, 0, f"missing/malformed marker: {missing[:3]}")
    return Dimension("marker_conformance", 5, 5, "all files carry the §4 marker")


def _score_type_correctness(mypy_report: MypyReport) -> Dimension:
    if mypy_report.passed:
        return Dimension("type_correctness", 20, 20, "mypy --strict clean")
    return Dimension("type_correctness", 20, 0, f"mypy failed: {mypy_report.stdout.strip()[:200]}")


def _score_coverage(pytest_report: PytestReport) -> Dimension:
    pct = pytest_report.coverage_pct or 0.0
    if pct >= 80.0:
        return Dimension("test_coverage", 25, 25, f"coverage {pct:.1f}% ≥ 80%")
    # linear scale: at 80% you get 25; at 0% you get 0
    score = int(round((pct / 80.0) * 25))
    return Dimension("test_coverage", 25, score, f"coverage {pct:.1f}% < 80%")


def _score_public_surface(ctx: GenerationContext, output_dir: Path) -> Dimension:
    issues: list[str] = []
    for name in REQUIRED_FILES:
        if not (output_dir / name).is_file():
            issues.append(f"missing {name}")
    for name in REQUIRED_TEST_FILES:
        if not (output_dir / name).is_file():
            issues.append(f"missing {name}")

    connector_py = output_dir / "connector.py"
    if connector_py.is_file():
        try:
            tree = ast.parse(connector_py.read_text())
        except SyntaxError as e:
            issues.append(f"connector.py: parse error {e}")
            tree = None
        if tree is not None:
            class_node = next(
                (n for n in tree.body if isinstance(n, ast.ClassDef) and n.name.lower() == ctx.psp_name.lower()),
                None,
            )
            if class_node is None:
                issues.append(f"connector.py: no class named (case-insensitive) {ctx.psp_name}")
            else:
                method_names = {
                    n.name for n in class_node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                }
                missing = REQUIRED_FLOW_METHODS - method_names
                if missing:
                    issues.append(f"connector class missing methods: {sorted(missing)}")

    init_py = output_dir / "__init__.py"
    if init_py.is_file():
        text = init_py.read_text()
        if "ConnectorFactory.register" not in text:
            issues.append("__init__.py: does not call ConnectorFactory.register")
        if "requires_lens" not in text:
            issues.append("__init__.py: missing requires_lens")

    status_map_py = output_dir / "status_map.py"
    if status_map_py.is_file():
        if "PaymentAttemptStatus" not in status_map_py.read_text():
            issues.append("status_map.py: does not reference PaymentAttemptStatus")

    if not issues:
        return Dimension("public_surface", 20, 20, "all required files + methods + registration present")
    # subtract 4 per issue down to 0
    penalty = min(20, 4 * len(issues))
    return Dimension("public_surface", 20, 20 - penalty, "; ".join(issues[:5]))


def _score_error_handling(output_dir: Path) -> Dimension:
    issues: list[str] = []
    connector_py = output_dir / "connector.py"
    if connector_py.is_file():
        text = connector_py.read_text()
        if "WEBHOOK_SIGNATURE_FAILED" not in text:
            issues.append("connector.py: handle_webhook does not raise ConnectorError(WEBHOOK_SIGNATURE_FAILED)")
        if "ConnectorError" not in text:
            issues.append("connector.py: no ConnectorError references")
        if "httpx" in text and "raise_for_status" not in text and "HTTPStatusError" not in text:
            issues.append("connector.py: httpx errors not wrapped")
    else:
        issues.append("connector.py missing")
    if not issues:
        return Dimension("error_handling", 20, 20, "ConnectorError + signature check present")
    penalty = min(20, 7 * len(issues))
    return Dimension("error_handling", 20, 20 - penalty, "; ".join(issues))


def _score_pii_discipline(output_dir: Path) -> Dimension:
    issues: list[str] = []
    auth_py = output_dir / "auth.py"
    if auth_py.is_file():
        text = auth_py.read_text()
        if "Maskable" not in text:
            issues.append("auth.py: credentials not typed Maskable")
    else:
        issues.append("auth.py missing")
    # Forbidden tokens directly logged at module scope. Heuristic.
    forbidden_re = re.compile(r"(structlog|logger|logging)\.\w+\([^)]*\bsecret\b", re.IGNORECASE)
    for p in output_dir.rglob("*.py"):
        if forbidden_re.search(p.read_text()):
            issues.append(f"{p.relative_to(output_dir)}: secret in log call")
    if not issues:
        return Dimension("pii_discipline", 10, 10, "Maskable used; no obvious PII in logs")
    penalty = min(10, 4 * len(issues))
    return Dimension("pii_discipline", 10, 10 - penalty, "; ".join(issues))


def score_rubric(
    *,
    ctx: GenerationContext,
    output_dir: Path,
    mypy_report: MypyReport,
    pytest_report: PytestReport,
) -> RubricReport:
    return RubricReport(
        dimensions=[
            _score_marker(output_dir),
            _score_type_correctness(mypy_report),
            _score_coverage(pytest_report),
            _score_public_surface(ctx, output_dir),
            _score_error_handling(output_dir),
            _score_pii_discipline(output_dir),
        ]
    )
```

- [ ] **Step 3: Run, confirm pass**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest tests/test_quality_rubric.py -v
```
Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace add src/grace/quality_rubric.py tests/test_quality_rubric.py
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "feat(rubric): score generated package across the 6 dimensions"
```

**Validation criterion:** `pytest tests/test_quality_rubric.py` passes; a deliberately clean scaffold scores 100; a missing marker drops the marker dim to 0.

**Estimated effort:** 4 hr.

---

### Task 4.3: Integration test — run-pipeline-with-real-gates against a hand-crafted fixture

**Files:**
- Create: `/Users/sarthak/PycharmProjects/references/grace/tests/integration/test_pipeline_with_gates.py`

- [ ] **Step 1: Test**

```python
# tests/integration/test_pipeline_with_gates.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import pytest

from grace.errors import GraceError, GraceErrorReason
from grace.pipeline import PipelineHooks, run_pipeline
from grace.pipeline.types import GenerationContext, GenerationResult, PspDocs


pytestmark = pytest.mark.integration


@dataclass
class _StubRunner:
    files: list[tuple[str, str]]
    async def is_available(self) -> tuple[bool, str]:
        return (True, "ok")
    async def generate(self, ctx: GenerationContext) -> GenerationResult:
        written: list[Path] = []
        for name, body in self.files:
            p = ctx.output_dir / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body)
            written.append(p)
        return GenerationResult(output_dir=ctx.output_dir, files_written=written, stdout="", stderr="", exit_code=0)


def test_pipeline_raises_when_rubric_fails(tmp_path: Path) -> None:
    rb = tmp_path / "rb.md"; rb.write_text("rb")
    ctx = GenerationContext(
        psp_name="demo",
        rulebook_paths=[rb],
        psp_docs=PspDocs(source_uri="x", source_kind="local_file", local_paths=[rb]),
        output_dir=tmp_path / "out",
        target_module="lens.connectors.demo",
        lens_version_constraint="^0.1",
        grace_version="0.1.0",
        source_version="x",
    )
    # Empty package: no required files. Rubric will score very low; gate fails.
    runner = _StubRunner(files=[])
    with pytest.raises(GraceError) as exc:
        asyncio.run(run_pipeline(ctx=ctx, runner=runner, hooks=PipelineHooks(run_gates=True)))
    assert exc.value.reason is GraceErrorReason.QUALITY_GATE_FAILED
```

- [ ] **Step 2: Run**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest tests/integration/test_pipeline_with_gates.py -v
```
Expected: 1 passed.

- [ ] **Step 3: Commit**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace add tests/integration/test_pipeline_with_gates.py
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "test(integration): pipeline raises QUALITY_GATE_FAILED on empty output"
```

**Validation criterion:** `pytest tests/integration/` passes.

**Estimated effort:** 1 hr.

---

## Step 5 — Regenerate Cashfree, diff against hand-written reference

This is the moment the system gets honest. The hand-written Cashfree reference lives at `/Users/sarthak/PycharmProjects/references/lens/lens/connectors/cashfree/` after Lens Step 3 lands. If it doesn't exist yet, escalate to the Lens implementing agent — Step 5 cannot start.

### Task 5.1: Verify the hand-written reference exists

**Files:**
- Read-only.

- [ ] **Step 1: Confirm presence**

```bash
ls /Users/sarthak/PycharmProjects/references/lens/lens/connectors/cashfree/
```
Expected: `__init__.py`, `connector.py`, `auth.py`, `models.py`, `status_map.py`, `tests/`.

- [ ] **Step 2: Snapshot hash for later comparison**

```bash
cd /Users/sarthak/PycharmProjects/references/lens && \
  find lens/connectors/cashfree -name '*.py' -print0 | \
  sort -z | xargs -0 shasum -a 256 > /tmp/cashfree_handwritten.sha256
cat /tmp/cashfree_handwritten.sha256
```

**Validation criterion:** reference package exists and snapshot file written. If absent, stop and ask the Lens agent.

**Estimated effort:** 15 min.

---

### Task 5.2: Run `grace doctor`

**Files:**
- None.

- [ ] **Step 1: Confirm Claude Code is reachable**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run grace doctor
```
Expected: prints `healthy: Claude Code v...`, exit code 0. If unhealthy, run `claude login` and retry.

**Validation criterion:** `grace doctor` exits 0.

**Estimated effort:** 5 min – 15 min (depending on auth state).

---

### Task 5.3: Run `grace generate cashfree`

**Files:**
- Create (via Grace): `/tmp/grace_cashfree_run1/lens/connectors/cashfree/*`

- [ ] **Step 1: Pick the Cashfree API doc source**

The constitution OQ-1 default says Cashfree is hand-written. For the regen test, use Cashfree's published OpenAPI URL (e.g., `https://docs.cashfree.com/openapi/...`) if available, or download the spec locally and pass the path. Document the URL in the run record.

- [ ] **Step 2: Generate**

```bash
mkdir -p /tmp/grace_cashfree_run1
cd /Users/sarthak/PycharmProjects/references/grace && \
  uv run grace generate cashfree \
    --from <cashfree_openapi_url_or_local_path> \
    --output /tmp/grace_cashfree_run1/lens/connectors/cashfree
```
Expected: exits 0 with `OK: wrote ...`. If any quality gate fails, the command exits 1 with a per-dimension breakdown — iterate the rulebook (see Task 5.5).

**Validation criterion:** `cat /tmp/grace_cashfree_run1/lens/connectors/cashfree/quality_report.json | python -m json.tool` shows `"passed": true` and `total ≥ 60`.

**Estimated effort:** 30 min – 4 hr (depending on Claude latency + retry count).

---

### Task 5.4: Diff against hand-written reference

**Files:**
- Compare: `/tmp/grace_cashfree_run1/...` vs `/Users/sarthak/PycharmProjects/references/lens/lens/connectors/cashfree/`

- [ ] **Step 1: Structural diff**

```bash
diff -ruN \
  /Users/sarthak/PycharmProjects/references/lens/lens/connectors/cashfree \
  /tmp/grace_cashfree_run1/lens/connectors/cashfree \
  > /tmp/grace_cashfree_diff.patch
wc -l /tmp/grace_cashfree_diff.patch
```

- [ ] **Step 2: Categorize differences**

Expected diff classes (acceptable):
- Comment phrasing.
- Local helper function ordering.
- Internal helper names (e.g., `_map_http_error` vs `_translate_http_error`).
- Test fixture spellings.
- Marker-block timestamps (Grace's run has its own).

Unacceptable diff classes (must fix the rulebook and rerun):
- Method signatures on `Cashfree(Connector)` differ.
- Missing required files.
- `__init__.py` doesn't call `ConnectorFactory.register("cashfree", Cashfree)`.
- `status_map.py` is missing any of: `SUCCESS`, `FAILED`, `USER_DROPPED`, `CANCELLED`, `FLAGGED`, `PENDING`, `NOT_ATTEMPTED`.
- `handle_webhook` doesn't raise `ConnectorError(WEBHOOK_SIGNATURE_FAILED)` on bad signature.
- Wire-level `Decimal` conversion missing for `order_amount`.

- [ ] **Step 3: Record the assessment**

Write a short note to `/tmp/grace_cashfree_run1/diff_assessment.md` listing acceptable/unacceptable findings.

**Validation criterion:** all unacceptable diff classes resolved (rulebook iteration in Task 5.5 if needed).

**Estimated effort:** 1 hr.

---

### Task 5.5: Iterate rulebook (if necessary) and re-generate

**Files:**
- Modify: `rulesbook/codegen/python/*.md` as required by Task 5.4 findings.

- [ ] **Step 1: For each unacceptable finding, edit the rulebook**

Example: if `handle_webhook` is missing signature verification, sharpen `python/webhook_handling.md` step 1 and add an explicit Python snippet.

- [ ] **Step 2: Commit each iteration**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace add rulesbook/codegen/python/
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "fix(rulebook): clarify <thing> after Cashfree regen iteration N"
```

- [ ] **Step 3: Re-run `grace generate cashfree`**

```bash
rm -rf /tmp/grace_cashfree_run<N>
cd /Users/sarthak/PycharmProjects/references/grace && uv run grace generate cashfree --from <source> --output /tmp/grace_cashfree_run<N>/lens/connectors/cashfree
```

- [ ] **Step 4: Re-diff**

Repeat Task 5.4. Stop when all unacceptable findings are clean.

**Validation criterion:** Cashfree diff against the hand-written reference contains only "acceptable" diff classes.

**Estimated effort:** 2 hr – 1 day (depends on rulebook gaps).

---

## Step 6 — Generate Razorpay from scratch

The from-scratch test. No hand-written reference; Razorpay must pass quality gates on its own merits.

### Task 6.1: Identify the Razorpay source

**Files:**
- None.

- [ ] **Step 1: Choose source**

Use Razorpay's published API docs URL (e.g., `https://razorpay.com/docs/api/...` or a local mirror). Document the choice.

**Validation criterion:** source URL or local path written into Task 6.2's command.

**Estimated effort:** 30 min.

---

### Task 6.2: Run `grace generate razorpay`

**Files:**
- Create (via Grace): `/tmp/grace_razorpay/lens/connectors/razorpay/*`

- [ ] **Step 1: Generate**

```bash
mkdir -p /tmp/grace_razorpay
cd /Users/sarthak/PycharmProjects/references/grace && \
  uv run grace generate razorpay \
    --from <razorpay_source> \
    --output /tmp/grace_razorpay/lens/connectors/razorpay
```
Expected: exits 0 with `OK: wrote ...`. Gates pass.

- [ ] **Step 2: Inspect quality report**

```bash
cat /tmp/grace_razorpay/lens/connectors/razorpay/quality_report.json | python -m json.tool
```
Expected: `"passed": true`, `total ≥ 60`.

- [ ] **Step 3: Confirm public surface manually**

```bash
ls /tmp/grace_razorpay/lens/connectors/razorpay/
ls /tmp/grace_razorpay/lens/connectors/razorpay/tests/
grep -n "class Razorpay" /tmp/grace_razorpay/lens/connectors/razorpay/connector.py
grep -n "ConnectorFactory.register" /tmp/grace_razorpay/lens/connectors/razorpay/__init__.py
```
Expected: all five files + five tests; class `Razorpay(Connector)`; registration line present.

**Validation criterion:** Razorpay package emitted, quality gates pass without manual intervention.

**Estimated effort:** 30 min – 4 hr (depending on Razorpay doc complexity + iteration).

---

### Task 6.3: Razorpay rubric iteration (if necessary)

**Files:**
- Modify: rulebook (as in Task 5.5).

- [ ] **Step 1: If gates fail, iterate the rulebook**

Same loop as Task 5.5. Each iteration commits.

- [ ] **Step 2: Final clean run**

```bash
rm -rf /tmp/grace_razorpay
cd /Users/sarthak/PycharmProjects/references/grace && \
  uv run grace generate razorpay --from <source> --output /tmp/grace_razorpay/lens/connectors/razorpay
cat /tmp/grace_razorpay/lens/connectors/razorpay/quality_report.json | python -m json.tool
```
Expected: `"passed": true`.

**Validation criterion:** clean run + clean rubric.

**Estimated effort:** 0 – 1 day (depends on doc clarity).

---

### Task 6.4: Document the Razorpay run

**Files:**
- Modify: `/Users/sarthak/PycharmProjects/references/grace/docs/v1_acceptance_log.md` (create if absent).

- [ ] **Step 1: Append run record**

Contents:
```
## v1 Acceptance Log

### 2026-MM-DD — Cashfree regen
- Source: <url>
- Commit at regen: <sha>
- Diff against hand-written: <N lines, N acceptable, 0 unacceptable>
- quality_report.json total: <X>/100

### 2026-MM-DD — Razorpay from-scratch
- Source: <url>
- Commit at regen: <sha>
- quality_report.json total: <X>/100
```

- [ ] **Step 2: Commit**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace add docs/v1_acceptance_log.md
git -C /Users/sarthak/PycharmProjects/references/grace commit -m "docs(acceptance): record Cashfree regen + Razorpay from-scratch runs"
```

**Validation criterion:** log file lists both runs with their quality totals.

**Estimated effort:** 30 min.

---

## Step 7 — Merge `python-support` into `main`

Per constitution OQ-3 and sub-project §3.3, v1 acceptance includes landing `python-support` on `main` and deleting the feature branch.

### Task 7.1: Final lint/typecheck/test sweep on `python-support`

**Files:**
- None (test runners).

- [ ] **Step 1: Run the full suite locally**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run ruff check src tests
cd /Users/sarthak/PycharmProjects/references/grace && uv run mypy --strict src tests
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest -v
```
Expected: ruff clean, mypy clean, pytest all green (unit + integration).

**Validation criterion:** all three exit 0.

**Estimated effort:** 30 min.

---

### Task 7.2: Rebase `python-support` onto `main`

**Files:**
- None (git operations).

- [ ] **Step 1: Fetch and rebase**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace fetch origin
git -C /Users/sarthak/PycharmProjects/references/grace checkout python-support
git -C /Users/sarthak/PycharmProjects/references/grace rebase origin/main
```
Expected: clean rebase. Resolve conflicts if any (likely few — `main` is the pre-fork starting point).

- [ ] **Step 2: Re-run tests post-rebase**

```bash
cd /Users/sarthak/PycharmProjects/references/grace && uv run pytest -v
```
Expected: all green.

**Validation criterion:** `python-support` is now linear atop `origin/main`.

**Estimated effort:** 15 min – 1 hr.

---

### Task 7.3: Fast-forward `main` to `python-support`

**Files:**
- None (git).

- [ ] **Step 1: Update `main`**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace checkout main
git -C /Users/sarthak/PycharmProjects/references/grace merge --ff-only python-support
```
Expected: `Fast-forward`. If not a fast-forward, something diverged in Task 7.2 — re-rebase.

- [ ] **Step 2: Push `main`**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace push origin main
```

- [ ] **Step 3: Delete `python-support` locally and on origin**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace branch -d python-support
git -C /Users/sarthak/PycharmProjects/references/grace push origin --delete python-support
```

**Validation criterion:** `main` contains the Grace v1 implementation; `python-support` no longer exists locally or on origin.

**Estimated effort:** 15 min.

---

### Task 7.4: Tag v0.1.0

**Files:**
- None (git).

- [ ] **Step 1: Tag**

```bash
git -C /Users/sarthak/PycharmProjects/references/grace tag -a v0.1.0 -m "Grace v0.1.0 — Python codegen for Orbit Lens"
git -C /Users/sarthak/PycharmProjects/references/grace push origin v0.1.0
```

**Validation criterion:** `git -C ... tag -l` includes `v0.1.0`.

**Estimated effort:** 5 min.

---

## Verification gates

A single checklist mapping to sub-project §8 acceptance criteria. Re-run all before declaring v1 done.

| # | Gate | How to verify |
|---|---|---|
| V1 | `grace --version` prints the version | `uv run grace --version` |
| V2 | `grace --help` shows `doctor`, `generate`, `regenerate` | `uv run grace --help` |
| V3 | `grace doctor` reports Claude Code reachable | `uv run grace doctor` → exit 0 |
| V4 | `grace generate cashfree` produces a passing package | Task 5.3 → `quality_report.json.passed == true` |
| V5 | Regenerated Cashfree diff is acceptable vs hand-written reference | Task 5.4 |
| V6 | `grace generate razorpay` produces a passing package | Task 6.2 |
| V7 | `grace regenerate cashfree` re-runs with same args | `uv run grace regenerate cashfree` after a generate, output matches |
| V8 | Generated `__init__.py` self-registers with `ConnectorFactory.register("<psp>", <Psp>)` | `grep ConnectorFactory.register /tmp/grace_cashfree_run<N>/.../__init__.py` |
| V9 | Every emitted .py file has the constitution §4 marker | rubric `marker_conformance` dim == 5 |
| V10 | mypy --strict clean on emitted packages | rubric `type_correctness` dim == 20 |
| V11 | pytest --cov ≥ 80% on emitted packages | rubric `test_coverage` dim == 25 |
| V12 | No `openai`, `anthropic`, `litellm`, `langgraph` in dependencies | `uv pip list \| grep -Ei 'openai\|anthropic\|litellm\|langgraph'` returns nothing |
| V13 | `python-support` branch merged into `main` and deleted | `git branch -a` on the Grace fork shows only `main` (local + origin) |
| V14 | Tag `v0.1.0` pushed | `git tag -l v0.1.0` |
| V15 | No `AIProvider` ABC, no provider-registry abstraction in `src/grace/` | `grep -r "class AIProvider\|class AIBackend\|provider_registry" src/grace/` returns nothing |

If any gate fails: revert to the relevant Step, iterate, re-verify the full table.

---

## Handoff notes

**For the implementing agent:**

1. **One AI backend.** This is the single most important constraint. If, mid-implementation, you feel the urge to add an `AIProvider` ABC "for future flexibility," stop and re-read constitution OQ-7 and sub-project §1 "Out of scope." Adding it violates the spec; the v1 design is deliberately concrete.

2. **The Rust → Python transformation is mostly rulebook work.** The original fork generated Rust because its rulebook described Rust. Replace the rulebook content. The pipeline machinery (Grace's `src/`) is orthogonal: it doesn't know what language Claude will emit.

3. **Don't over-engineer the prompt.** The `build_prompt` function in Task 3.6 hands Claude file paths and a short directive. Resist the temptation to inline the rulebook contents into the prompt — Claude reads files. If something is missing from Claude's output, sharpen the rulebook, not the prompt.

4. **Rubric thresholds are guides, not floors.** The 60/100 threshold is from the spec; a healthy generated package should score 85+. If a clean Cashfree run lands at 62, something is wrong even though gates pass — investigate.

5. **The hand-written Cashfree reference is the source of truth for "what Grace should produce."** If Grace's Cashfree output disagrees with the reference on a load-bearing detail, the rulebook is the bug, not the reference.

6. **Steps 5 and 6 are the loop.** Expect to iterate the rulebook several times during Step 5 before Cashfree lands clean. Each iteration is fast — minutes — because the rulebook is just Markdown. Razorpay (Step 6) tests whether your rulebook generalizes; if the only PSP Grace can generate is Cashfree, you've overfit.

7. **Subprocess invocation of `claude`.** The exact CLI flags vary by Claude Code version. The reference invocation in Task 3.6 uses `-p` (print mode) with `--permission-mode acceptEdits`. If a future Claude Code release changes these, update `runner.py`; the spec doesn't pin them and isn't expected to.

8. **`pyproject.toml` does not depend on `claude-agent-sdk`.** The local Claude CLI is an external runtime dependency, not a Python package. Grace shells out to `claude`; it never imports it.

9. **Out-of-scope flows.** If you find yourself adding patterns for `authorize`, `capture`, `void`, `setup_mandate`, etc., stop — those are explicitly out of v1 scope (constitution §7). They live in `../specs/FUTURE_S2S_INTERFACE.md` for the next slice.

10. **Step 0 is non-negotiable.** Do not skip the inventory in Task 0.3 even though it doesn't produce code. The existing fork is large and confusing; the inventory is what keeps Step 3.1's deletions honest.

**Interpretations applied where the spec was ambiguous** (the implementing agent should adopt these unless they have a strong reason otherwise):

- The constitution §4 marker is rendered as seven lines (top rule + four data lines + bottom rule). The spec shows the block as a code fence; the count was implicit. Tests in Task 2.4 and Task 3.7 lock it in at seven lines.
- The runner invokes the local `claude` CLI with `-p` (print/headless mode) and `--permission-mode acceptEdits`. The spec says "headless subprocess" without naming flags.
- `regenerate` is implemented via a tiny per-`~/.grace/last_run.json` record holding `(psp, source, output)`. The spec doesn't pin the storage location.
- "Marker enforcement" is belt-and-suspenders: the rulebook tells Claude to emit it; Grace's `ensure_marker` post-processor backstops anything Claude misses. The spec strictly requires the marker; it does not say Grace must do the post-process, but it's the cheapest way to satisfy "marker conformance" deterministically.
- Quality rubric dimensions are scored linearly within their max where partial credit makes sense (coverage, public_surface) and binary where it doesn't (type_correctness — mypy is pass/fail).
- Marker template lives in `src/grace/templates/marker.j2`; the rulebook describes the format but the renderer is Python. There's a small duplication risk (template format vs rulebook description) — Tasks 2.4 and 3.7 share a single Jinja2 template so they don't drift.
