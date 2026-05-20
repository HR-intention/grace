# Sub-project: Grace (codegen)

**Inherits from**: `ORBIT_CONSTITUTION.md`. Conflicts resolve in favor of the constitution.
**Owner**: TBD per implementing agent.
**Location**: `/Users/sarthak/PycharmProjects/references/grace/` — the team's fork (`github.com/HR-intention/grace`) of `juspay-prism/grace/` (`github.com/juspay/hyperswitch-prism`).
**Status**: v0.4 — aligned with constitution v0.4 (Order + PaymentAttempt entity model; simplified status enums + locked failure-code taxonomy). No changes to the Grace CLI surface, pipeline, or `ClaudeCodeRunner`; only generated-code targets evolved.

---

## §1. Purpose & scope

Grace is a build-time CLI tool. It reads a PSP's API documentation and generates a Python connector package conforming to Lens's locked `Connector` ABC. Upstream Grace already does this for Rust; this sub-project extends the team's fork to emit Python.

**Grace's job, in one sentence**: gather the right context (Grace's rulebook + the target PSP's docs), hand it to **Claude Code**, and validate the output. Nothing fancier than that.

**In scope for v1**

- `python-support` branch landed on `main`: Grace emits Python instead of Rust.
- One AI backend: Claude Code, invoked via the local CLI session.
- A single `ClaudeCodeRunner` class — no `AIProvider` abstraction layer.
- Quality-gate pipeline (`mypy --strict`, `pytest --cov`, rubric ≥ 60/100) on generated output.
- Generated-file marker emission per constitution §4.
- End-to-end demos: regenerate Cashfree (matches hand-written reference); generate Razorpay from scratch (passes gates).

**Out of scope for v1**

- Any AI backend other than Claude Code (no OpenAI, no Anthropic API, no Bedrock, no Gemini).
- Runtime / production execution. Grace runs only on dev machines or CI.
- A pluggable provider abstraction. If we ever add a second backend, *then* we extract an ABC; not before.
- PSPs other than the two demos.
- Generating code in any language other than Python.

---

## §2. Public surface

Grace's public surface is its CLI; internal APIs are not public.

```
$ grace --help
$ grace generate   <psp> --from <source> [--output <dir>] [--config <file>]
$ grace regenerate <psp>                              # re-run last generation with same args
$ grace doctor                                        # is Claude Code reachable?
$ grace --version
```

`<source>` accepts:

- A URL to OpenAPI / API docs.
- A local file path (OpenAPI YAML/JSON, Markdown, or other supported formats).
- A directory of doc files.

CLI flag precedence (low → high): config file → environment variables → CLI flags.

Files emitted carry the constitution §4 marker.

---

## §3. Internal architecture

```
grace/
  src/grace/
    cli.py                  # entrypoint (click)
    pipeline/
      __init__.py           # orchestrates context-prep → invoke → gates
      context.py            # gather rulebook + PSP docs into a context bundle
      runner.py             # ClaudeCodeRunner: invoke Claude Code with the bundle
      gates.py              # mypy / pytest / rubric on the output
    rules/                  # rulebook/codegen (synced from upstream juspay-prism/grace)
    templates/              # Jinja2 helpers (header marker, package skeleton)
    config.py               # ~/.grace/config.yaml + env loading
    quality_rubric.py       # rubric scoring
```

### 3.1 Pipeline — three steps, not five

1. **Gather context.** Read the rulebook (`rules/`), read the target PSP's docs (URL or local files), assemble a context bundle that has everything Claude Code needs.
2. **Invoke Claude Code.** Hand it the context bundle and a short instruction ("generate a Python connector that implements `lens.Connector` for this PSP, following the rulebook"). Claude Code reads, navigates, writes files in the output directory.
3. **Run quality gates.** `mypy --strict` + `pytest --cov` + the rubric (§5) on the generated package. If any gate fails, surface a clear error; don't promote the package to its final destination.

That's it. No macro-prompt engineering, no tech-spec intermediate IR. Claude Code is capable enough to produce a correct connector given the rulebook + PSP docs; the value Grace adds is consistent context-gathering, the file marker, and the quality gates.

### 3.2 Output layout

For each PSP, Grace emits a package matching Lens's expected layout (see `SUBPROJECT_LENS.md` §5.1):

```
connectors/<psp>/
  __init__.py            # imports + ConnectorFactory.register("<psp>", <PspClass>)
  connector.py           # class <Psp>(Connector): ...
  auth.py                # signing helpers
  models.py              # PSP-specific wire-level Pydantic models
  status_map.py          # PSP-specific term → (PaymentAttemptStatus, PaymentFailureCode)
                         # per SUBPROJECT_LENS.md §5.2
  tests/
    test_create_order.py
    test_sync_payment.py
    test_refund.py
    test_sync_refund.py
    test_webhook.py
```

Every file starts with the constitution §4 generated-file marker. The marker is rendered by `templates/marker.j2`. Required marker fields: PSP name, source version/commit, generation timestamp (UTC ISO-8601), Grace version, regeneration command.

### 3.3 Sync with upstream juspay/hyperswitch-prism

Per constitution OQ-3, the default is **track upstream**:

- `python-support` is a feature branch off `main` *only until merged*. v1 acceptance (§8) requires merging `python-support` into `main`. After that, the branch is deleted; future Python work happens on `main` directly.
- `main` periodically merges (subtree-merge) from `juspay-prism/grace/`.
- Conflicts resolved manually at merge time.
- Cadence: at least quarterly; sooner if upstream lands a major rulebook change.

---

## §4. `ClaudeCodeRunner`

A single concrete class. No ABC, no registry, no fallback.

```python
# grace/pipeline/runner.py

@dataclass
class GenerationContext:
    rulebook_paths: list[Path]
    psp_docs: PspDocs            # URL+fetched content, or local paths
    output_dir: Path             # where the connector package will land
    target_module: str           # e.g. "lens.connectors.cashfree"
    lens_version: str  # so the generated package can pin it


class ClaudeCodeRunner:
    """Invokes the local Claude Code CLI to generate a connector package."""

    def __init__(self, *, cli_path: Path | None = None, timeout_s: float = 1800.0):
        """`cli_path` defaults to `which claude`; override for tests."""
        ...

    async def is_available(self) -> tuple[bool, str]:
        """Returns (healthy, detail) — used by `grace doctor`.
        Checks the binary exists and the session is authenticated."""
        ...

    async def generate(self, context: GenerationContext) -> GenerationResult:
        """Spawns Claude Code with the context bundle. Returns when the
        subprocess exits cleanly; raises on timeout or non-zero exit."""
        ...
```

Implementation notes:

- The runner spawns Claude Code as a subprocess in headless mode, working directory set to `context.output_dir`.
- The context bundle is passed as the initial prompt; key files (rulebook, PSP docs) are referenced by path so Claude can read them via its own file tools.
- stdout is captured and surfaced to the user; stderr to the log.
- Failure modes:
  - Binary missing → `ConnectorError` analogue at the Grace level: `GraceError(reason=CLAUDE_CODE_NOT_FOUND, detail="`claude` binary not found in PATH")`.
  - Not authenticated → `GraceError(reason=CLAUDE_CODE_NOT_AUTHENTICATED, detail="run `claude login`")`.
  - Timeout → `GraceError(reason=CLAUDE_CODE_TIMEOUT)`.

The runner doesn't know or care which Claude model is active; the local CLI session decides. This is intentional: it matches the user's "in most simple manner" directive and avoids leaking model-selection into Grace.

---

## §5. Quality rubric (6 dimensions)

The generator's output is scored:

| Dimension | Max | Check |
|---|---|---|
| Marker conformance | 5 | Constitution §4 marker present and well-formed in every emitted file. |
| Type correctness | 20 | `mypy --strict` clean on the emitted package. |
| Test coverage | 25 | `pytest --cov` ≥ 80% on the emitted package. |
| Public-surface conformance | 20 | File layout matches §3.2; `<Psp>(Connector)` class exists with all four flow methods (`create_order`, `sync_payment`, `refund`, `sync_refund`) + `handle_webhook` + `close`; `__init__.py` self-registers; `status_map.py` maps every PSP-specific status term to (`PaymentAttemptStatus`, `PaymentFailureCode`) — unmapped terms fall back to `PaymentFailureCode.UNKNOWN` with a warning. |
| Error handling | 20 | `handle_webhook` raises `ConnectorError(WEBHOOK_SIGNATURE_FAILED)` on bad signature; all `httpx` failures wrapped in `ConnectorError` with the right reason. |
| PII discipline | 10 | No raw PII in logs; `Maskable` used for credentials in `auth.py`; tests verify masked logs. |

Pass threshold: **≥ 60 / 100**.

Scored by `grace.quality_rubric` after generation. Outputs `quality_report.json` next to the generated package; on failure shows the per-dimension breakdown so a re-run can target the gap.

(Note: this is six dimensions, not the seven I had in v0.1 — I dropped "ABC conformance" as a separate dimension since "Public-surface conformance" already covers it.)

---

## §6. Configuration

`~/.grace/config.yaml`:

```yaml
# v1 has exactly one backend — included here for shape, not for choice.
claude_code:
  cli_path: null         # null ⇒ auto-detect via `which claude`
  timeout_s: 1800

quality:
  mypy_strict: true
  min_coverage_pct: 80
  min_rubric_score: 60

lens:
  # The Lens version this Grace targets. Emitted into the
  # generated package's __init__.py as `requires_lens`.
  version_constraint: "^0.1"
```

CLI flag overrides shadow config. No secret values live in this file — there are no provider API keys to manage.

---

## §7. Dependencies

- Python ≥ 3.11.
- `click` (CLI).
- `jinja2` (header-marker template, package skeleton).
- `pyyaml` (config).
- `httpx` (fetching remote PSP docs).
- `mypy`, `pytest`, `coverage` — invoked as subprocesses on generated code, not runtime deps.
- The Claude Code CLI must be installed and authenticated on the machine running Grace. Grace does not bundle it.

No `openai` or `anthropic` SDK dependencies.

Upstream: tracks `juspay-prism/grace/` per constitution OQ-3.

---

## §8. Acceptance criteria for v1

- [ ] `grace generate cashfree --from <cashfree-openapi-url>` produces a working `connectors/cashfree/` package that:
    - Includes `connector.py`, `auth.py`, `models.py`, `__init__.py`, and tests for all four v1 flows (`create_order`, `sync_payment`, `refund`, `sync_refund`) + webhook.
    - Every file has the constitution §4 marker.
    - `mypy --strict` clean.
    - `pytest --cov` ≥ 80%.
    - Rubric ≥ 60/100.
    - The class `Cashfree(Connector)` exists and is registered via `ConnectorFactory.register("cashfree", Cashfree)`.
- [ ] `grace generate razorpay --from <razorpay-openapi-url>` produces a complete connector from scratch passing all gates (no hand-written reference for diff).
- [ ] `grace doctor` reports whether Claude Code is reachable and authenticated.
- [ ] `grace regenerate cashfree` re-runs the previous generation with the same arguments.
- [ ] The `python-support` branch is merged into `main`.

---

## §9. Roadmap

Maps to constitution §9 Steps 4 + 5.

1. **Sync rulebook with upstream**. ~0.5 day.
2. **Replace Rust templates with Python**. Update `rules/` + `templates/` so the rulebook describes the Python `Connector` ABC, not the Rust trait. ~3 days.
3. **Build `ClaudeCodeRunner`** + `pipeline/` + `gates.py` + CLI entrypoint. ~2 days.
4. **End-to-end regenerate Cashfree**. Diff against hand-written reference from `SUBPROJECT_LENS.md` §9 Step 3. Iterate the rulebook until parity. ~2 days.
5. **Generate Razorpay**. Fresh PSP; must pass gates. ~2 days.
6. **Merge `python-support` into `main`**. ~0.5 day.

Total: ~10 days single-agent. Steps 2 and 3 can split between two agents; everything else is serial.

---

## §10. Open questions for the implementing agent

- **Q1** (constitution OQ-3): hard-fork or track upstream? **Recommendation**: track upstream. The team's added value is `python-support`; upstream rule improvements are worth pulling. Diverge in branches but `main` merges quarterly.
- **Q2**: How does Grace know which Lens version to target? **Recommendation**: read `lens.version_constraint` from config; emit it into the generated `__init__.py` as `requires_lens`. When the ABC changes, bump Grace and regenerate.
- **Q3**: Cache the Claude Code output for `regenerate`? **Recommendation**: skip caching in v1. Each `regenerate` is a fresh Claude session — it's not expensive enough yet to be worth the complexity. Revisit if a single regenerate exceeds a few minutes.
- **Q4**: How are PSP docs fetched? URLs are simple (`httpx.get`); local files are simple (read from disk). What about multi-file OpenAPI specs with `$ref`s pointing to other files? **Recommendation**: support URL + single local file + local directory in v1. `$ref` resolution is Claude's job, not Grace's pre-processor.
- **Q5**: How does the rubric score "Public-surface conformance" for a PSP that legitimately needs an extra file (e.g., a custom token-refresh helper)? **Recommendation**: rubric only checks *required* files present; extra files don't dock points.
- **Q6**: Should the rulebook be versioned and stored in-repo? **Recommendation**: yes, under `rules/`. Major rulebook changes ⇒ Grace major-version bump (constitution §8).
- **Q7**: How does Grace handle the case where Claude Code emits a file *not* in the expected layout (e.g., extra config.py)? **Recommendation**: allow extras with a warning. Only fail if a *required* file is missing.
