# Sub-project: Grace (codegen)

**Inherits from**: `ORBIT_CONSTITUTION.md`. Conflicts resolve in favor of the constitution.
**Owner**: TBD per implementing agent.
**Location**: `/Users/sarthak/PycharmProjects/references/grace/` — the team's fork (`github.com/HR-intention/grace`) of `juspay-prism/grace/` (`github.com/juspay/hyperswitch-prism`).
**Status**: v0.5 — aligned with constitution v0.5. Mandate-capable codegen via a **domain-modular connector**: per-capability mixins (`<Psp>Orders(PaymentsConnector)`, `<Psp>Subscriptions(MandateConnector)`) composed into one registered `<Psp>Connector` over a shared `core/` base, plus the shared `WebhookHandlers` builder. Adds a `--domain {orders|subscriptions|all}` axis to `fetch-docs`/`generate` with **incremental, per-domain regeneration**. A **major Grace *tool* bump** (rulebook + prompt + rubric + CLI shape change, per constitution §8); `ClaudeCodeRunner` is unaffected. **The lens-facing contract is unchanged** — the registered class still isinstance-composes the locked capability interfaces and self-registers via `register` + `register_webhook`; only Grace's CLI ergonomics and the generated package's internal structure evolved. The handoff spec (`2026-05-30-grace-mandate-codegen-handoff.md`) remains authoritative for the lens ABCs (§3), the webhook mechanism (§4), and the Cashfree→lens normalization (§6); **this doc (§3.2) supersedes its §5 flat single-class layout** with the domain-modular structure below.

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
- **Mandate-capable connectors**: Grace emits capability-interface classes (`PaymentsConnector`/`MandateConnector`), never bare `Connector`; plus a shared `WebhookHandlers` builder (`build_webhook_handlers`) registered via `ConnectorFactory.register_webhook`. This is a **major Grace bump** (rulebook + prompt + rubric shape change); `ClaudeCodeRunner` is unaffected.
- **Domain-modular connectors + a `--domain` axis**: each PSP capability is generated as its own mixin in its own subpackage (`orders/`, `subscriptions/`) over a shared `core/` base, then composed into one registered `<Psp>Connector`. `fetch-docs` and `generate` take `--domain {orders|subscriptions|all}` (default `all`). `generate --domain X` regenerates **only** domain `X`'s files plus the small compose surface, leaving other domains and `core/` untouched — so extending a connector to a new domain is cheap and low-risk.
- **Per-PSP doc bundle**: `fetch-docs` groups pages by domain under `connector_docs/<psp>/{_shared,orders,subscriptions}/` and scaffolds a developer-editable `connector_docs/<psp>.md` spec that carries the authoritative §6 normalization decisions. `connector_docs/` is now tracked in git so the pinned snapshot + spec ship with the generated code.

**Authoritative detailed spec for mandate codegen:** `2026-05-30-grace-mandate-codegen-handoff.md` (co-located in the Grace repo under `docs/superpowers/specs/`). That document is the source of truth for the locked capability-interface ABCs (§3), the concrete `WebhookHandlers`/`register_webhook` mechanism (§4), the Cashfree→lens normalization tables (§6), and the per-file generation plan (§5). This spec governs at the scope/policy level; the handoff doc governs at the implementation level. **Exception (locked 2026-05-31):** §3.2 of *this* doc supersedes the handoff's §5 per-file layout (a flat single class) with a domain-modular structure (`core/` + per-domain mixins + a composed `<Psp>Connector`) and an incremental `--domain` workflow. The lens public contract the handoff pins — the §3 ABCs, the §4 webhook mechanism, and the §6 normalization values — is unchanged; only Grace's generated-package internals and CLI ergonomics differ.

**Out of scope for v1**

- Any AI backend other than Claude Code (no OpenAI, no Anthropic API, no Bedrock, no Gemini).
- Runtime / production execution. Grace runs only on dev machines or CI.
- A pluggable provider abstraction. If we ever add a second backend, *then* we extract an ABC; not before.
- PSPs other than the two demos.
- Generating code in any language other than Python.
- On-demand mandate debit (`execute_mandate_debit` / `notify_pre_debit`) — periodic mode is PSP-driven; those are deferred.

---

## §2. Public surface

Grace's public surface is its CLI; internal APIs are not public.

```
$ grace --help
$ grace fetch-docs <psp> --from <llms.txt> [--domain orders|subscriptions|all]   # snapshot docs (domain-grouped) + scaffold connector_docs/<psp>.md
$ grace generate   <psp> [--from <source>] [--domain orders|subscriptions|all] [--output <dir>] [--config <file>]
$ grace regenerate <psp>                              # re-run last generation with same args
$ grace docs                                          # rebuild docs-generated/ catalog (AST introspection)
$ grace doctor                                        # is Claude Code reachable?
$ grace --version
```

`<source>` accepts:

- A URL to OpenAPI / API docs.
- A local file path (OpenAPI YAML/JSON, Markdown, or other supported formats).
- A directory of doc files.

`--domain` (default `all`) selects which capability/domain to fetch or (re)generate; `generate --domain X` is **incremental** — it rewrites only domain `X`'s files plus the compose surface (see §3.2).

CLI flag precedence (low → high): config file → environment variables → CLI flags.

Files emitted carry the constitution §4 marker.

---

## §3. Internal architecture

```
grace/
  src/grace/
    cli.py                  # entrypoint (click): generate / regenerate / fetch-docs / docs / doctor / config
    fetch_docs.py           # `fetch-docs`: snapshot PSP docs (domain-grouped) + scaffold connector_docs/<psp>.md
    docs_build.py           # `docs`: docs-generated/ catalog via AST introspection
    pipeline/
      __init__.py           # orchestrates context-prep → invoke → gates
      context.py            # gather rulebook + (domain-scoped) PSP docs into a context bundle
      prompt.py             # domain-aware generation prompt (locked-surface guardrails + self-check)
      runner.py             # ClaudeCodeRunner: invoke Claude Code with the bundle
      gates.py              # mypy / pytest / rubric on the output
    templates/marker.j2     # constitution §4 header marker
    config.py               # <cwd>/.grace/config.yaml + env loading
    quality_rubric.py       # rubric scoring
  rulesbook/codegen/        # the rulebook fed to Claude Code (REPO ROOT — there is no src/grace/rules)
    python/*.md             # generic Python codegen rules (connector_abc, domain_types, status_mapping, …)
    guides/patterns/*.md    # per-flow patterns (payment + mandate)
  connector_docs/<psp>/     # committed, domain-grouped PSP doc snapshots; + connector_docs/<psp>.md spec
```

### 3.1 Pipeline — three steps, not five

1. **Gather context.** Read the rulebook (`rulesbook/codegen/`), the target PSP's docs (the domain-scoped `connector_docs/<psp>/_shared/` + the active `--domain` folder, or a URL), and the per-PSP `connector_docs/<psp>.md` spec; assemble a context bundle scoped to the domain(s) being generated.
2. **Invoke Claude Code.** Hand it the context bundle and a short instruction ("generate a Python connector that implements `lens.Connector` for this PSP, following the rulebook"). Claude Code reads, navigates, writes files in the output directory.
3. **Run quality gates.** `mypy --strict` + `pytest --cov` + the rubric (§5) on the generated package. If any gate fails, surface a clear error; don't promote the package to its final destination.

That's it. No macro-prompt engineering, no tech-spec intermediate IR. Claude Code is capable enough to produce a correct connector given the rulebook + PSP docs; the value Grace adds is consistent context-gathering, the file marker, and the quality gates.

### 3.2 Output layout

For each PSP, Grace emits a **domain-modular** package under the Lens monorepo (`/Users/sarthak/PycharmProjects/symplora/sylibs/packages/lens/`):

```
<sylibs>/packages/lens/src/lens/connectors/<psp>/
  __init__.py            # requires_lens = "^0.2"
                         # ConnectorFactory.register("<psp>", <Psp>Connector)
                         # ConnectorFactory.register_webhook("<psp>", build_webhook_handlers)
  connector.py           # MERGED, registered: class <Psp>Connector(<Psp>Orders, <Psp>Subscriptions): ...
  webhooks.py            # build_webhook_handlers(config) -> WebhookHandlers ; _classify (event -> family)
  core/
    base.py              # _<Psp>Base(Connector): name, base_url, close, __init__ (the ONE httpx client), _config
    auth.py              # build_auth_headers + verify_signature (shared HMAC, family-agnostic)
    status.py            # shared enums + failure free-text -> (PaymentFailureCode, FailureClass)
    models.py            # shared wire models (webhook envelope, error body)
  orders/                # domain: PaymentsConnector
    connector.py         # class <Psp>Orders(_<Psp>Base, PaymentsConnector): create_order/sync_payment/refund/sync_refund + 2 props
    models.py            # payment wire models
    status_map.py        # PSP payment status -> (PaymentAttemptStatus, PaymentFailureCode)
    webhooks.py          # _parse_payment_webhook(bytes) -> PaymentWebhookEvent
  subscriptions/         # domain: MandateConnector
    connector.py         # class <Psp>Subscriptions(_<Psp>Base, MandateConnector): 5 lifecycle + 4 introspection
    models.py            # subscription / plan / mandate wire models
    status_map.py        # subscription_status -> MandateStatus ; event -> WebhookEventType
    webhooks.py          # _parse_mandate_webhook(bytes) -> MandateWebhookEvent
```

Tests land in Lens's test tree at `<sylibs>/packages/lens/tests/integration/connectors/<psp>/<domain>/test_*.py`, plus a cross-domain `test_webhook_router.py` that exercises one `WebhookRouter` dispatching both families. (The previous Cashfree connector + tests are quarantined under `legacy/` as the payment-side reference.)

**Domain → capability** (the table codegen keys on): `orders → PaymentsConnector` (class `<Psp>Orders`); `subscriptions → MandateConnector` (class `<Psp>Subscriptions`). `MandateConnector` is singular — `MandatesConnector` does not exist (only the *facade* is plural).

**Composition rules.** `core/base.py` owns identity + lifecycle + the single `httpx.AsyncClient`; each domain class subclasses `(_<Psp>Base, <Capability>)`, so it is a complete, independently-testable connector for that one capability; the merged `<Psp>Connector` composes the present domain classes and resolves `_<Psp>Base` once via C3. Lens is agnostic to this internal structure — it requires only that the **registered** class isinstance-composes ≥1 capability interface, has zero leftover abstract methods, returns `name == "<psp>"`, and accepts `__init__(config)`.

**Incremental, per-domain regeneration.** `generate --domain X` (re)writes only `connectors/<psp>/X/*` plus the small **compose surface** derived from which domain folders exist — the package-root `connector.py` (recomposes `<Psp>Connector`), `webhooks.py` (rewires the domain `parse_*` into `WebhookHandlers`), and `__init__.py` (registration). `core/` and other domains are untouched, so extending a connector to a new domain is cheap and cannot regress existing ones. `--domain all` regenerates everything.

**Input layout.** `fetch-docs` writes domain-grouped snapshots and a developer-editable spec:

```
connector_docs/<psp>.md             # fetch-docs-scaffolded, dev-editable per-PSP spec (carries the §6 normalization)
connector_docs/<psp>/_shared/       # cross-domain pages (auth, overview, errors, webhook signature-verification)
connector_docs/<psp>/orders/        # payment doc pages
connector_docs/<psp>/subscriptions/ # subscription/mandate doc pages (latest; never subscriptionsv1)
```

`generate --domain X` reads `connector_docs/<psp>.md` + `_shared/` + `X/`. The reusable mapping *methodology* lives in the generic rulebook (`rulesbook/codegen/python/status_mapping.md` + the mandate webhook pattern); the PSP-specific *decisions* (e.g. `ON_HOLD → SUSPENDED`, the failure-substring precedence, periodic-mode finality) live in `connector_docs/<psp>.md`, scaffolded by `fetch-docs` and completed by a developer before generation.

**`__init__.py` requirements (constitution v0.5):** declare `requires_lens = "^0.2"` at module scope and call **both** `ConnectorFactory.register(...)` and `ConnectorFactory.register_webhook(...)`. A bare `Connector` subclass implementing no capability interface is rejected by `ConnectorFactory.register` at import time.

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
    lens_version: str            # so the generated package can pin it
    domain: str                  # "orders" | "subscriptions" | "all" — scopes the docs
                                 # bundle + which mixin(s) the prompt tells Claude to (re)write


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
| Type correctness | 20 | `mypy --strict` clean on the emitted package. Generated code must use modern Python 3.11 typing (`dict[str, str]`, `X \| None`, `set[...]`, `StrEnum`) — **never** `Dict`/`List`/`Optional`/`Set` from `typing`. |
| Test coverage | 25 | `pytest --cov` ≥ 80% on the emitted package. Mandate flow tests (create, sync, cancel, pause, resume on all supported rails) and mandate + debit webhook events must be covered; `status_map.py` maps every documented subscription status + webhook event (unmapped → `MandateStatus`/`UNKNOWN` fallbacks with a warning). |
| Public-surface conformance | 20 | Layout matches §3.2 (`core/base.py` + `core/auth.py`, root `connector.py` + `webhooks.py`, and per active domain `connector.py`/`status_map.py`/`webhooks.py`). The rubric discovers the **registered** class from the `ConnectorFactory.register("<psp>", X)` call in `__init__.py` (not by class name) and verifies it isinstance-composes **≥1 capability interface** (`PaymentsConnector`/`MandateConnector`) — **never** bare `Connector` — with **zero leftover abstract methods** (resolved across the MRO). Payment flows present for an `orders`/`PaymentsConnector` domain; the five mandate lifecycle methods + the four introspection methods (`supported_mandate_rails`, `supports_pause`, `supported_intervals`, `max_mandate_amount`) for a `subscriptions`/`MandateConnector` domain. `__init__.py` calls **both** `ConnectorFactory.register(...)` and `ConnectorFactory.register_webhook(...)`; root `webhooks.py` exports `build_webhook_handlers`. Each domain's `status_map.py` maps every documented term — payments → (`PaymentAttemptStatus`, `PaymentFailureCode`), subscriptions → (`MandateStatus`, `WebhookEventType`) — with unmapped terms falling back to `UNKNOWN`/`MandateStatus` defaults + a warning. |
| Error handling | 20 | `WebhookRouter` raises `ConnectorError(WEBHOOK_SIGNATURE_FAILED)` on bad signature (via the `verify` callable in `WebhookHandlers`); all `httpx` failures wrapped in `ConnectorError` with the right reason; unknown webhook family raises `ConnectorError(NOT_SUPPORTED)`. |
| PII discipline | 10 | No raw PII in logs; `Maskable` used for credentials in `auth.py`; `CustomerContact.email` and `CustomerContact.phone` are not logged in plaintext; tests verify masked logs. |

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
  version_constraint: "^0.2"
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

- [ ] `grace fetch-docs cashfree --from <cashfree-llms.txt> --domain all` snapshots domain-grouped pages under `connector_docs/cashfree/{_shared,orders,subscriptions}/` and scaffolds a `connector_docs/cashfree.md` spec.
- [ ] `grace generate cashfree --domain all` produces a working **domain-modular** `connectors/cashfree/` package that:
    - Has the §3.2 layout: root `connector.py` (merged `CashfreeConnector`) + `webhooks.py`; `core/{base,auth,status,models}.py`; `orders/` and `subscriptions/` each with `connector.py`/`models.py`/`status_map.py`/`webhooks.py`; tests under `tests/integration/connectors/cashfree/{orders,subscriptions}/` + `test_webhook_router.py`.
    - Every file carries the constitution §4 marker.
    - `mypy --strict` clean (modern Python 3.11 typing throughout); `pytest --cov` ≥ 80%; rubric ≥ 60/100.
    - The registered class `CashfreeConnector` isinstance-composes `PaymentsConnector` + `MandateConnector` (via `CashfreeOrders`/`CashfreeSubscriptions` over `_CashfreeBase`); `__init__.py` calls both `ConnectorFactory.register("cashfree", CashfreeConnector)` and `ConnectorFactory.register_webhook("cashfree", build_webhook_handlers)`; `requires_lens = "^0.2"` at module scope.
- [ ] `grace generate cashfree --domain subscriptions` on an existing payments-only package adds the mandate mixin **incrementally** — only `subscriptions/*` + the compose surface (root `connector.py`/`webhooks.py`/`__init__.py`) change; `orders/` and `core/` are untouched.
- [ ] `grace generate razorpay --from <razorpay-openapi-url>` produces a complete connector from scratch passing all gates (no hand-written reference for diff).
- [ ] `grace doctor` reports whether Claude Code is reachable and authenticated.
- [ ] `grace regenerate cashfree` re-runs the previous generation with the same arguments.
- [ ] The `python-support` branch is merged into `main`.

---

## §9. Roadmap

Maps to constitution §9 Steps 4 + 5.

1. **Sync rulebook with upstream**. ~0.5 day.
2. **Replace Rust templates with Python**. Update `rulesbook/codegen/` + `templates/` so the rulebook describes the Python `Connector` ABC, not the Rust trait. ~3 days.
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
- **Q6**: Should the rulebook be versioned and stored in-repo? **Recommendation**: yes, under `rulesbook/codegen/` at the repo root (there is no `src/grace/rules/`). Major rulebook changes ⇒ Grace major-version bump (constitution §8).
- **Q7**: How does Grace handle the case where Claude Code emits a file *not* in the expected layout (e.g., extra config.py)? **Recommendation**: allow extras with a warning. Only fail if a *required* file is missing.
