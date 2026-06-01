# Grace Domain-Modular Mandate Codegen — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend Grace (v0.5 → **v0.6**) to generate domain-modular, mandate-capable PSP connectors against lens 0.2.0, driven by a `--domain {orders|subscriptions|all}` axis with incremental per-domain regeneration; validate entirely via Grace's own pytest suite (the live Cashfree regen is deferred).

**Architecture:** `fetch-docs` groups doc pages by domain and scaffolds a per-PSP `connector_docs/<psp>.md` spec. `generate` reads the domain-scoped bundle, Claude writes per-domain capability **mixins** (`<Psp>Orders(_<Psp>Base, PaymentsConnector)`, `<Psp>Subscriptions(_<Psp>Base, MandateConnector)`) over a shared `core/` base; **Grace itself** templates the deterministic compose surface (root `connector.py`/`webhooks.py`/`__init__.py`) from the present domains. The rubric discovers the registered class from the `register()` call and checks capability composition statically.

**Tech Stack:** Python 3.11, `click`, `jinja2`, `httpx`, `pytest`, `mypy`; lens 0.2.0 (capability ABCs + `WebhookRouter`/`WebhookHandlers`).

**Source of truth:** the spec `docs/superpowers/specs/2026-05-31-grace-domain-codegen-implementation-spec.md` (requirements R1–R10, Cross-Cutting C1–C3) and `SUBPROJECT_GRACE_CODEGEN.md` §3.2/§5. Read the spec's R-section before each phase.

**Conventions:** run everything from the Grace repo root with `uv run`. Tests live under `tests/`. Commit after every green step. Never hand-edit a marker-stamped generated file.

---

## File Structure

**Grace source (modified):**
- `src/grace/fetch_docs.py` — domain presets, per-URL bucket routing, `<psp>.md` scaffold (Phase A).
- `src/grace/cli.py` — `--domain` option on `fetch-docs` + `generate`; thread to context (Phase A/C).
- `src/grace/pipeline/types.py` — `GenerationContext.domain` field (Phase C).
- `src/grace/pipeline/context.py` — domain-scoped doc bundle + domain-keyed rulebook selection (Phase C).
- `src/grace/pipeline/prompt.py` — domain-aware prompt, new locked-surface guardrails (Phase C).
- `src/grace/pipeline/orchestrate.py` — wire the compose step in before the marker loop (Phase C).
- `src/grace/quality_rubric.py` — register-arg discovery + composition/per-domain/typing checks (Phase D).
- `src/grace/docs_build.py` — composed-class discovery, capability-keyed flows (Phase E).
- `pyproject.toml` — version → 0.6 (Phase E).

**Grace source (created):**
- `src/grace/pipeline/compose.py` — Grace-owned compose-surface generator (Phase C).

**Rulebook / docs (modified/created):**
- `rulesbook/codegen/python/{connector_abc,domain_types,webhook_handling,status_mapping,file_layout,testing,pitfalls,README}.md` — reshaped (Phase B).
- `rulesbook/codegen/guides/patterns/pattern_{create_subscription,sync_subscription,manage_mandate,mandate_webhook}.md` — created; `pattern_IncomingWebhook_flow.md` rewritten (Phase B).
- `connector_docs/cashfree.md` — authored §6 normalization (Phase A).
- `src/grace/skills_templates/add-connector/**` — review checklist + flow-patterns + rubric-checklist (Phase E).

**Tests (created):** `tests/test_fetch_docs_domain.py`, `tests/test_cashfree_spec.py`, `tests/pipeline/test_context_domain.py`, `tests/pipeline/test_prompt_domain.py`, `tests/pipeline/test_compose.py`, `tests/pipeline/test_orchestrate_compose.py`, `tests/test_quality_rubric_v2.py`, `tests/fixtures/connectors/**` (synthetic packages), `tests/test_docs_build_v2.py`.

> Confirm the exact existing test layout first: `Run: ls tests/ && ls tests/pipeline 2>/dev/null`. Match the established directory/naming convention if it differs from the above.

---

## Phase A — fetch-docs `--domain` + the Cashfree spec

### Task 1: Domain glob presets + per-URL bucket classifier

**Files:**
- Modify: `src/grace/fetch_docs.py`
- Test: `tests/test_fetch_docs_domain.py`

- [ ] **Step 1: Read the current globs.** `Run: sed -n '29,103p' src/grace/fetch_docs.py` (confirm `DEFAULT_INCLUDE_GLOBS`/`DEFAULT_EXCLUDE_GLOBS`, and that `*subscription/*`, `*mandate*`, `*setup-mandate*`, `*subscriptionsv1*` are excludes).

- [ ] **Step 2: Write the failing test.**

```python
# tests/test_fetch_docs_domain.py
from grace.fetch_docs import bucket_for_url, filter_urls_by_domain

URLS = [
    "https://x/docs/api-reference/payments/latest/orders/create.md",
    "https://x/docs/api-reference/payments/latest/refunds/create.md",
    "https://x/docs/api-reference/subscription/mandate/create.md",
    "https://x/docs/api-reference/subscription/plans/create.md",
    "https://x/docs/api-reference/authentication.md",
    "https://x/docs/payments/online/webhooks/signature-verification.md",
    "https://x/docs/api-reference/subscriptionsv1/overview.md",  # legacy — must drop
]

def test_orders_domain_keeps_orders_and_shared_only() -> None:
    kept = filter_urls_by_domain(URLS, domain="orders")
    assert any("orders/create" in u for u in kept)
    assert any("authentication" in u for u in kept)          # shared
    assert not any("subscription/" in u for u in kept)
    assert not any("subscriptionsv1" in u for u in kept)

def test_subscriptions_domain_keeps_subs_and_shared_not_orders() -> None:
    kept = filter_urls_by_domain(URLS, domain="subscriptions")
    assert any("subscription/mandate/create" in u for u in kept)
    assert any("signature-verification" in u for u in kept)  # shared
    assert not any("/orders/" in u for u in kept)
    assert not any("subscriptionsv1" in u for u in kept)

def test_all_domain_is_union_minus_legacy() -> None:
    kept = filter_urls_by_domain(URLS, domain="all")
    assert any("orders/create" in u for u in kept)
    assert any("subscription/mandate/create" in u for u in kept)
    assert not any("subscriptionsv1" in u for u in kept)

def test_bucket_for_url() -> None:
    assert bucket_for_url("https://x/docs/api-reference/payments/latest/orders/create.md") == "orders"
    assert bucket_for_url("https://x/docs/api-reference/subscription/mandate/create.md") == "subscriptions"
    assert bucket_for_url("https://x/docs/api-reference/authentication.md") == "_shared"
```

- [ ] **Step 3: Run it to confirm it fails.** `Run: uv run pytest tests/test_fetch_docs_domain.py -q` → FAIL (ImportError: `bucket_for_url`).

- [ ] **Step 4: Implement the presets + classifier in `fetch_docs.py`.** Add near the existing glob constants:

```python
# Pages every domain's connector needs (auth, identity, error shapes, webhook signing).
SHARED_INCLUDE_GLOBS: tuple[str, ...] = (
    "*api*authentication*", "*api*overview*", "*api*enums*", "*api*errors*",
    "*webhooks*signature*", "*webhooks*security*",
)
DOMAIN_INCLUDE_GLOBS: dict[str, tuple[str, ...]] = {
    "orders": ("*api*orders*", "*api*payments*", "*api*refunds*", "*payments*webhook*"),
    "subscriptions": (
        "*subscription/*", "*subscription/plans*", "*subscription/mandate*",
        "*subscription/payment*", "*subscription*webhook*",
    ),
}
# subscriptionsv1 (legacy, body-embedded sig) is never wanted.
LEGACY_EXCLUDE_GLOBS: tuple[str, ...] = ("*subscriptionsv1*", "*previous/*", "*v2022-*", "*v2023-*", "*v2024-*")

def _domain_includes(domain: str) -> tuple[str, ...]:
    if domain == "all":
        merged = set(SHARED_INCLUDE_GLOBS)
        for globs in DOMAIN_INCLUDE_GLOBS.values():
            merged.update(globs)
        return tuple(sorted(merged))
    if domain not in DOMAIN_INCLUDE_GLOBS:
        raise GraceError(reason=GraceErrorReason.SOURCE_FETCH_FAILED, detail=f"unknown domain {domain!r}")
    return SHARED_INCLUDE_GLOBS + DOMAIN_INCLUDE_GLOBS[domain]

def filter_urls_by_domain(urls: list[str], *, domain: str) -> list[str]:
    return filter_urls(urls, include=list(_domain_includes(domain)), exclude=list(LEGACY_EXCLUDE_GLOBS))

def bucket_for_url(url: str) -> str:
    path = _path_of(url)
    for dom, globs in DOMAIN_INCLUDE_GLOBS.items():
        if any(fnmatch.fnmatch(path, g) for g in globs):
            return dom
    return "_shared"
```

- [ ] **Step 5: Run the test to confirm it passes.** `Run: uv run pytest tests/test_fetch_docs_domain.py -q` → PASS. (If a real Cashfree URL lands in the wrong bucket, tune the globs in `DOMAIN_INCLUDE_GLOBS` and re-run — `subscription/*` must win over `payments*` for subscription pages; `bucket_for_url` checks domains before falling back to `_shared`.)

- [ ] **Step 6: Commit.** `git add src/grace/fetch_docs.py tests/test_fetch_docs_domain.py && git commit -m "feat(fetch-docs): domain glob presets + per-URL bucket classifier"`

### Task 2: Route writes into `_shared/<domain>` + thread `--domain`

**Files:**
- Modify: `src/grace/fetch_docs.py` (`fetch_docs()` signature + write loop), `src/grace/cli.py` (`fetch_docs_cmd`)
- Test: `tests/test_fetch_docs_domain.py` (extend)

- [ ] **Step 1: Write the failing test** (local-llms.txt + a stub httpx client so no network):

```python
def test_fetch_writes_into_domain_subfolders(tmp_path, monkeypatch) -> None:
    import httpx
    from grace.fetch_docs import fetch_docs
    pages = {
        "https://x/orders/create.md": b"# orders create",
        "https://x/subscription/mandate/create.md": b"# mandate create",
        "https://x/api-reference/authentication.md": b"# auth",
    }
    llms = "\n".join(pages) + "\n"
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("llms.txt"):
            return httpx.Response(200, text=llms)
        return httpx.Response(200, content=pages[str(req.url)])
    client = httpx.Client(transport=httpx.MockTransport(handler))
    out = tmp_path / "cashfree"
    fetch_docs(psp_name="cashfree", source="https://x/llms.txt", output_dir=out, domain="all", client=client)
    assert (out / "_shared").is_dir()
    assert list((out / "orders").glob("*orders*create*.md"))
    assert list((out / "subscriptions").glob("*mandate*create*.md"))
```

- [ ] **Step 2: Run → FAIL** (`fetch_docs()` has no `domain` kwarg). `Run: uv run pytest tests/test_fetch_docs_domain.py::test_fetch_writes_into_domain_subfolders -q`

- [ ] **Step 3: Implement.** Add `domain: str = "all"` to `fetch_docs(...)`. Replace the `filter_urls(...)` call with `filter_urls_by_domain(all_urls, domain=domain)`. In the write loop, route each kept URL by bucket:

```python
        for idx, url in enumerate(kept):
            ...  # existing GET + raise_for_status
            bucket = bucket_for_url(url)
            target_dir = output_dir / bucket
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / derive_filename(url, idx)
            target.write_bytes(resp.content)
            written.append(target)
```

- [ ] **Step 4: Add the CLI option.** In `cli.py` `fetch_docs_cmd`, add `@click.option("--domain", type=click.Choice(["orders","subscriptions","all"]), default="all")` and pass `domain=domain` into `fetch_docs(...)`. (Keep `--include`/`--exclude` as manual overrides — when explicitly provided they bypass the domain preset; document that in the help text.)

- [ ] **Step 5: Run → PASS** (`uv run pytest tests/test_fetch_docs_domain.py -q`), then `uv run grace fetch-docs --help` shows `--domain`.

- [ ] **Step 6: Commit.** `git add src/grace/fetch_docs.py src/grace/cli.py tests/test_fetch_docs_domain.py && git commit -m "feat(fetch-docs): route pages into _shared/<domain> + --domain CLI option"`

### Task 3: Scaffold `connector_docs/<psp>.md` (write-if-absent / `--force`, no clobber)

**Files:**
- Modify: `src/grace/fetch_docs.py` (new `scaffold_psp_spec`, called from `fetch_docs`), `src/grace/cli.py` (`--force`)
- Create: `src/grace/templates/psp_spec.md.j2`
- Test: `tests/test_fetch_docs_domain.py` (extend)

- [ ] **Step 1: Write the failing test.**

```python
def test_scaffold_created_when_absent_not_clobbered(tmp_path) -> None:
    from grace.fetch_docs import scaffold_psp_spec
    spec = tmp_path / "cashfree.md"
    assert scaffold_psp_spec(psp_name="cashfree", spec_path=spec) is True   # created
    spec.write_text(spec.read_text() + "\nDEV EDIT\n")
    assert scaffold_psp_spec(psp_name="cashfree", spec_path=spec) is False  # not clobbered
    assert "DEV EDIT" in spec.read_text()
    assert scaffold_psp_spec(psp_name="cashfree", spec_path=spec, force=True) is True  # forced
    assert "DEV EDIT" not in spec.read_text()
```

- [ ] **Step 2: Run → FAIL.** `Run: uv run pytest tests/test_fetch_docs_domain.py::test_scaffold_created_when_absent_not_clobbered -q`

- [ ] **Step 3: Create the template** `src/grace/templates/psp_spec.md.j2` with a connector-info header + **minimal** skeleton normalization tables whose lens-target columns are fixed and PSP cells are empty (`<!-- fill from fetched docs -->`). Sections: `## Connector Information`, `## Shared / failure free-text → (PaymentFailureCode, FailureClass)`, `## Subscriptions / subscription_status → MandateStatus`, `## Subscriptions / event → WebhookEventType`, `## Subscriptions / create-request field map`. (Pre-fill nothing beyond the PSP name; keep it minimal per the locked decision.)

- [ ] **Step 4: Implement `scaffold_psp_spec`** (renders the template via the existing jinja env pattern; returns `True` if it wrote, `False` if it skipped):

```python
def scaffold_psp_spec(*, psp_name: str, spec_path: Path, force: bool = False) -> bool:
    if spec_path.exists() and not force:
        return False
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(_render_psp_spec_template(psp_name=psp_name))  # jinja render of psp_spec.md.j2
    return True
```

Call it from `fetch_docs()` after the write loop: `scaffold_psp_spec(psp_name=psp_name, spec_path=output_dir.parent / f"{psp_name}.md", force=force)` and add `force: bool = False` to `fetch_docs(...)`. Add `--force` to the CLI command.

- [ ] **Step 5: Run → PASS.** `Run: uv run pytest tests/test_fetch_docs_domain.py -q`

- [ ] **Step 6: Commit.** `git add -A && git commit -m "feat(fetch-docs): scaffold dev-editable connector_docs/<psp>.md (no-clobber, --force)"`

### Task 4: Author `connector_docs/cashfree.md` §6 normalization

**Files:**
- Modify: `connector_docs/cashfree.md` (replace endpoint-dump with the §6 spec)
- Test: `tests/test_cashfree_spec.py`

- [ ] **Step 1: Write the failing grep-AC test** (pins that the load-bearing §6 rows are present):

```python
# tests/test_cashfree_spec.py
from pathlib import Path
SPEC = Path("connector_docs/cashfree.md").read_text()
REQUIRED = [
    "MandateStatus", "WebhookEventType", "FAILURE_CLASS",
    "CARD_EXPIRED", "LINK_EXPIRED", "ON_HOLD",
    "MANDATE_DEBIT_NOTIFIED", "MANDATE_EXPIRING_SOON",
    "USER_CANCELLED", "retry_attempts", "SUBSCRIPTION_REFUND_STATUS",
    "UPI_AUTOPAY", "next_scheduled_time", "plan_recurring_amount",
]
def test_cashfree_spec_has_section_6_rows() -> None:
    missing = [t for t in REQUIRED if t not in SPEC]
    assert not missing, f"cashfree.md missing §6 tokens: {missing}"
```

- [ ] **Step 2: Run → FAIL.** `Run: uv run pytest tests/test_cashfree_spec.py -q`

- [ ] **Step 3: Author the spec.** Rewrite `connector_docs/cashfree.md`: keep a short `## Connector Information` (name, base URLs, auth headers), then transcribe handoff §6 verbatim into the tables — Shared failure substring map (11 rows + default `UNKNOWN`) + the `FAILURE_CLASS` published-data note ("connector sets `failure_code` only; lens never branches on `FailureClass`"); Subscriptions: subscription_status→MandateStatus (incl. `ON_HOLD`→SUSPENDED, `CARD_EXPIRED`→SUSPENDED, `LINK_EXPIRED`→FAILED), event→WebhookEventType (all rows incl. `MANDATE_DEBIT_NOTIFIED`, `MANDATE_EXPIRING_SOON`, `USER_CANCELLED` on cancel, `psp_attempt = retry_attempts`, `SUBSCRIPTION_REFUND_STATUS` note, the *no `*_FAILED_FINAL`* note, **`UPI_AUTOPAY` debit failure → MANDATE_SUSPENDED**), rail→payment_methods, and the full create-request field map (incl. `next_scheduled_time`, `plan_recurring_amount`). Use spec **R8** as the checklist.

- [ ] **Step 4: Run → PASS.** `Run: uv run pytest tests/test_cashfree_spec.py -q`

- [ ] **Step 5: Commit.** `git add connector_docs/cashfree.md tests/test_cashfree_spec.py && git commit -m "docs(cashfree): author §6 lens normalization spec"`

---

## Phase B — Rulebook reshape + mandate patterns

> These are rulebook **markdown** deliverables (no unit tests; validated by review + a structural grep). Write them PSP-agnostic (no Cashfree specifics) so Razorpay-from-scratch still works. Use spec **R6/R7** as the content checklist and the lens source as the authority for signatures/types.

### Task 5: Reshape `rulesbook/codegen/python/*.md`

**Files (modify):** `connector_abc.md`, `domain_types.md`, `webhook_handling.md`, `status_mapping.md`, `file_layout.md`, `testing.md`, `pitfalls.md`, `README.md`
**Test:** `tests/test_rulebook_shape.py`

- [ ] **Step 1: Failing structural test** — assert the reshaped rules mention the new contract and not the retired one:

```python
# tests/test_rulebook_shape.py
from pathlib import Path
R = Path("rulesbook/codegen/python")
def test_webhook_rule_is_shared_router_not_connector_method() -> None:
    t = (R / "webhook_handling.md").read_text()
    assert "WebhookHandlers" in t and "WebhookFamily" in t and "build_webhook_handlers" in t
    assert "handle_webhook" not in t            # retired in 0.2.0
def test_connector_abc_rule_is_capability_mixins() -> None:
    t = (R / "connector_abc.md").read_text()
    assert "PaymentsConnector" in t and "MandateConnector" in t
    assert "_<Psp>Base" in t or "shared base" in t
def test_status_mapping_has_failure_class_published_note() -> None:
    t = (R / "status_mapping.md").read_text()
    assert "FAILURE_CLASS" in t and "never branch" in t.lower()
```

- [ ] **Step 2: Run → FAIL.** `Run: uv run pytest tests/test_rulebook_shape.py -q`

- [ ] **Step 3: Rewrite the eight files** per spec R6. Key required content: capability split + mixin/compose + shared-base one-client ownership + singular `MandateConnector` (`connector_abc.md`); mandate domain types imported from `lens` (`domain_types.md`); shared `WebhookHandlers`/`WebhookRouter`, `_classify -> WebhookFamily`, two parsers, `WEBHOOK_SIGNATURE_FAILED`/`NOT_SUPPORTED`, assembled by Grace's compose surface (`webhook_handling.md`); the mapping methodology + periodic-mode finality rule + `FAILURE_CLASS` published-data rule, failure-substring map home = `core/status.py` (`status_mapping.md`); `core/{base,auth,status,models}.py` + per-domain + compose surface (`file_layout.md`); per-domain tests + the tampered-signature router test (`testing.md`); modern typing (deprecated aliases only), one-client base, singular `MandateConnector`, no surgical hand-edits (`pitfalls.md`); reading order (`README.md`).

- [ ] **Step 4: Run → PASS.** `Run: uv run pytest tests/test_rulebook_shape.py -q`

- [ ] **Step 5: Commit.** `git add rulesbook/codegen/python tests/test_rulebook_shape.py && git commit -m "docs(rulebook): reshape python rules for capability mixins + shared webhook"`

### Task 6: Add mandate flow-patterns + rewrite incoming-webhook pattern

**Files (create):** `rulesbook/codegen/guides/patterns/pattern_create_subscription.md`, `pattern_sync_subscription.md`, `pattern_manage_mandate.md`, `pattern_mandate_webhook.md`. **(rewrite)** `pattern_IncomingWebhook_flow.md`.
**Test:** extend `tests/test_rulebook_shape.py`

- [ ] **Step 1: Failing test** — required patterns exist with locked signatures + the key §6 rules:

```python
def test_mandate_patterns_exist_and_pin_rules() -> None:
    P = Path("rulesbook/codegen/guides/patterns")
    create = (P / "pattern_create_subscription.md").read_text()
    assert "plan_recurring_amount" in create and "payment_methods" in create and "idempotency_key" in create
    manage = (P / "pattern_manage_mandate.md").read_text()
    assert "ACTIVATE" in manage and "next_scheduled_time" in manage and "idempotency_key" in manage
```

- [ ] **Step 2: Run → FAIL.** `Run: uv run pytest tests/test_rulebook_shape.py -q`

- [ ] **Step 3: Write the patterns** (mirror the existing `pattern_createorder.md` shape: locked signature → step list → skeleton → required tests → pitfalls), per spec R7: `create_subscription` (inline plan; full `CreateSubscriptionRequest` field map incl. `customer_contact.email/.phone` both required, `first_charge_at`→`subscription_first_charge_time` PERIODIC-only, `notification_channel=[SMS,EMAIL]`, `rail`→`authorization_details.payment_methods`, `idempotency_key` token); `sync_subscription`; `manage_mandate` (cancel/pause/`resume`=`ACTIVATE`, `effective_at`→`action_details.next_scheduled_time`, `idempotency_key` on all three); `mandate_webhook` (`_parse_mandate_webhook -> MandateWebhookEvent`). Rewrite `pattern_IncomingWebhook_flow.md` for the shared router (`build_webhook_handlers` + `_classify -> WebhookFamily` + the two parsers; tampered → `WEBHOOK_SIGNATURE_FAILED`).

- [ ] **Step 4: Run → PASS** (`uv run pytest tests/test_rulebook_shape.py -q`).

- [ ] **Step 5: Commit.** `git add rulesbook/codegen/guides/patterns tests/test_rulebook_shape.py && git commit -m "docs(rulebook): add mandate flow-patterns + shared-router webhook pattern"`

---

## Phase C — Prompt + context/types + Grace-owned compose surface

### Task 7: `GenerationContext.domain` + thread through context + CLI

**Files:** Modify `src/grace/pipeline/types.py`, `src/grace/pipeline/context.py`, `src/grace/cli.py`. Test: `tests/pipeline/test_context_domain.py`

- [ ] **Step 1: Failing test.**

```python
# tests/pipeline/test_context_domain.py
from pathlib import Path
from grace.pipeline.context import assemble_context

def test_assemble_context_carries_domain_and_scopes_docs(tmp_path) -> None:
    repo = Path.cwd()
    docs = tmp_path / "connector_docs" / "cashfree"
    (docs / "_shared").mkdir(parents=True); (docs / "subscriptions").mkdir()
    (docs / "_shared" / "auth.md").write_text("x"); (docs / "subscriptions" / "m.md").write_text("y")
    (tmp_path / "connector_docs" / "cashfree.md").write_text("# spec")
    ctx = assemble_context(
        psp_name="cashfree", source=str(docs), output_dir=tmp_path / "out",
        lens_version_constraint="^0.2", grace_version="0.6", source_version="t",
        repo_root=repo, domain="subscriptions",
    )
    assert ctx.domain == "subscriptions"
```

- [ ] **Step 2: Run → FAIL** (`assemble_context` has no `domain`). `Run: uv run pytest tests/pipeline/test_context_domain.py -q`

- [ ] **Step 3: Implement.** Add `domain: str = "all"` to `GenerationContext` (types.py, after `source_version`; it's frozen — keep field order, give a default so existing constructors still work). Add `domain: str = "all"` param to `assemble_context(...)` and set it on the returned context. In `cli.py` `generate`, add `@click.option("--domain", type=click.Choice(["orders","subscriptions","all"]), default="all")` and pass `domain=domain` to `assemble_context`.

- [ ] **Step 4: Run → PASS.** `Run: uv run pytest tests/pipeline/test_context_domain.py -q`

- [ ] **Step 5: Commit.** `git add src/grace/pipeline/types.py src/grace/pipeline/context.py src/grace/cli.py tests/pipeline/test_context_domain.py && git commit -m "feat(pipeline): thread --domain through GenerationContext + assemble_context"`

### Task 8: Domain-keyed rulebook selection + domain-scoped doc bundle

**Files:** Modify `src/grace/pipeline/context.py`. Test: `tests/pipeline/test_context_domain.py` (extend)

- [ ] **Step 1: Failing test** — orders run omits mandate patterns; subscriptions run includes them; both include core rules:

```python
def test_rulebook_selection_is_domain_keyed() -> None:
    from grace.pipeline.context import rulebook_files_for_domain
    orders = " ".join(rulebook_files_for_domain("orders"))
    subs = " ".join(rulebook_files_for_domain("subscriptions"))
    assert "connector_abc.md" in orders and "connector_abc.md" in subs       # core always
    assert "pattern_create_subscription.md" in subs
    assert "pattern_create_subscription.md" not in orders
    assert "pattern_createorder.md" in orders
```

- [ ] **Step 2: Run → FAIL.** `Run: uv run pytest tests/pipeline/test_context_domain.py::test_rulebook_selection_is_domain_keyed -q`

- [ ] **Step 3: Implement.** Replace the flat `RULEBOOK_FILES` constant with `CORE_RULEBOOK_FILES` (the `python/*.md` + shared guides) + `DOMAIN_PATTERN_FILES = {"orders": [...payment patterns...], "subscriptions": [...mandate patterns...]}`, and a function `rulebook_files_for_domain(domain) -> list[str]` (core + the domain's patterns; `all` = core + both). Have `default_rulebook_paths(repo_root, domain)` use it, and `assemble_context` pass `ctx.domain`. Also make `resolve_source` (or the doc-bundle step) read `connector_docs/<psp>/_shared/` + the active domain folder + `connector_docs/<psp>.md` when source is the docs dir.

- [ ] **Step 4: Run → PASS.** `Run: uv run pytest tests/pipeline/test_context_domain.py -q`

- [ ] **Step 5: Commit.** `git add src/grace/pipeline/context.py tests/pipeline/test_context_domain.py && git commit -m "feat(pipeline): domain-keyed rulebook + domain-scoped doc bundle"`

### Task 9: Rewrite the generation prompt for the domain-modular shape

**Files:** Modify `src/grace/pipeline/prompt.py`. Test: `tests/pipeline/test_prompt_domain.py`

- [ ] **Step 1: Failing test** — pin the new contract substrings and the retirements:

```python
# tests/pipeline/test_prompt_domain.py
from grace.pipeline.context import assemble_context
from grace.pipeline.prompt import build_prompt
# (build a minimal ctx via assemble_context with domain="subscriptions", as in test_context_domain)

def _ctx(tmp_path, domain):
    ...  # reuse the helper from test_context_domain

def test_prompt_pins_capability_imports_and_drops_retired(tmp_path) -> None:
    p = build_prompt(_ctx(tmp_path, "subscriptions"))
    assert "from lens.mandate_connector import MandateConnector" in p
    assert "from lens.webhook import WebhookHandlers, WebhookFamily" in p
    assert "from lens.enums import" in p and "from lens.factory import" in p
    assert "_<Psp>Base" in p
    assert "handle_webhook" not in p                       # retired
    assert "no `Connector` suffix" not in p                # retired pitfall
    # compose surface is Grace's job, not Claude's:
    assert "build_webhook_handlers" in p                   # named, but as Grace-owned
def test_typing_check_targets_deprecated_aliases_only(tmp_path) -> None:
    p = build_prompt(_ctx(tmp_path, "orders"))
    assert "Optional" in p and "Callable" in p             # mentions both: ban Optional, allow Callable
```

- [ ] **Step 2: Run → FAIL.** `Run: uv run pytest tests/pipeline/test_prompt_domain.py -q`

- [ ] **Step 3: Rewrite `PROMPT_TEMPLATE`** per spec R3: domain-conditional file list (write only the `--domain` mixin + `core/` on first creation; Grace owns the compose surface); the full exact import block (capability ABCs, `lens.webhook` incl. `WebhookFamily`, `lens.factory`, `lens.enums`, mandate `lens.domain_types`); class composition rules (`<Psp>Orders(_<Psp>Base, PaymentsConnector)` etc., one shared httpx client on `_<Psp>Base`); self-check greps for the new structure; modern-typing self-check that **bans** `Dict`/`List`/`Optional`/`Set`/`Tuple`/`FrozenSet`/`Type` and **allows** `Callable`/`Mapping`/`Any`/`Literal`/`Iterable`. Remove the bare-`Connector` + no-suffix pitfalls. `build_prompt` selects the domain-conditional blocks from `ctx.domain`.

- [ ] **Step 4: Run → PASS.** `Run: uv run pytest tests/pipeline/test_prompt_domain.py -q`

- [ ] **Step 5: Commit.** `git add src/grace/pipeline/prompt.py tests/pipeline/test_prompt_domain.py && git commit -m "feat(prompt): domain-aware prompt for capability mixins; retire bare-Connector guidance"`

### Task 10: Grace-owned compose-surface generator

**Files:** Create `src/grace/pipeline/compose.py`. Test: `tests/pipeline/test_compose.py`

- [ ] **Step 1: Failing test** — compose for both domains and orders-only:

```python
# tests/pipeline/test_compose.py
from grace.pipeline.compose import write_compose_surface

def _mk_domain(pkg, domain, cls):
    d = pkg / domain; d.mkdir(parents=True)
    (d / "connector.py").write_text(f"class {cls}:\n    pass\n")
    (d / "__init__.py").write_text("")

def test_compose_both_domains(tmp_path) -> None:
    pkg = tmp_path / "cashfree"
    _mk_domain(pkg, "orders", "CashfreeOrders")
    _mk_domain(pkg, "subscriptions", "CashfreeSubscriptions")
    write_compose_surface(pkg, psp_name="cashfree", lens_version="^0.2")
    conn = (pkg / "connector.py").read_text()
    assert "class CashfreeConnector(CashfreeOrders, CashfreeSubscriptions)" in conn
    init = (pkg / "__init__.py").read_text()
    assert 'ConnectorFactory.register("cashfree", CashfreeConnector)' in init
    assert 'ConnectorFactory.register_webhook("cashfree", build_webhook_handlers)' in init
    assert 'requires_lens = "^0.2"' in init
    hooks = (pkg / "webhooks.py").read_text()
    assert "parse_mandate=" in hooks and "parse_payment=" in hooks

def test_compose_orders_only_has_no_mandate_parser(tmp_path) -> None:
    pkg = tmp_path / "razorpay"
    _mk_domain(pkg, "orders", "RazorpayOrders")
    write_compose_surface(pkg, psp_name="razorpay", lens_version="^0.2")
    assert "class RazorpayConnector(RazorpayOrders)" in (pkg / "connector.py").read_text()
    hooks = (pkg / "webhooks.py").read_text()
    assert "parse_payment=" in hooks
    assert "parse_mandate=" not in hooks      # absent domain omitted (C1)
```

- [ ] **Step 2: Run → FAIL.** `Run: uv run pytest tests/pipeline/test_compose.py -q`

- [ ] **Step 3: Implement `compose.py`.** Scan `pkg/{orders,subscriptions}` for present domains; derive class names (`<Psp><Domain>`); render three files (templated). `connector.py`: import the present domain classes from their modules + `class <Psp>Connector(<present classes>): pass`. `webhooks.py`: `build_webhook_handlers(config)` wiring `verify=verify_signature(config,...)`, `classify=_classify`, and `parse_payment`/`parse_mandate` set only for present domains (else `None`); plus `_classify(raw)->WebhookFamily`. `__init__.py`: `requires_lens`, import `<Psp>Connector` + `build_webhook_handlers`, `register` + `register_webhook`. (Markers are added later by `ensure_marker` in orchestrate — Task 11.) Use the title-case domain→class map (`orders→Orders`, `subscriptions→Subscriptions`).

- [ ] **Step 4: Run → PASS.** `Run: uv run pytest tests/pipeline/test_compose.py -q`

- [ ] **Step 5: Commit.** `git add src/grace/pipeline/compose.py tests/pipeline/test_compose.py && git commit -m "feat(pipeline): Grace-owned compose-surface generator (composes present domains)"`

### Task 11: Wire the compose step into `run_pipeline`

**Files:** Modify `src/grace/pipeline/orchestrate.py`. Test: `tests/pipeline/test_orchestrate_compose.py`

- [ ] **Step 1: Failing test** — a stub runner writes domain folders; run_pipeline produces a marker-stamped compose surface:

```python
# tests/pipeline/test_orchestrate_compose.py
import asyncio
from grace.pipeline.orchestrate import run_pipeline, PipelineHooks
from grace.pipeline.marker import has_marker
# build a stub runner whose generate() writes orders/ + subscriptions/ mixin files into ctx.output_dir
def test_run_pipeline_emits_marked_compose_surface(tmp_path, stub_ctx, stub_runner) -> None:
    asyncio.run(run_pipeline(ctx=stub_ctx, runner=stub_runner, hooks=PipelineHooks(run_gates=False)))
    assert (stub_ctx.output_dir / "connector.py").is_file()
    assert has_marker(stub_ctx.output_dir / "connector.py")     # ensure_marker stamped it
    assert has_marker(stub_ctx.output_dir / "webhooks.py")
```

- [ ] **Step 2: Run → FAIL.** `Run: uv run pytest tests/pipeline/test_orchestrate_compose.py -q`

- [ ] **Step 3: Implement.** In `run_pipeline`, after `result = await runner.generate(ctx)` and **before** the `ensure_marker` loop, call the compose step (so its files get markers for free, satisfying C3):

```python
    result = await runner.generate(ctx)

    from grace.pipeline.compose import write_compose_surface
    write_compose_surface(
        result.output_dir, psp_name=ctx.psp_name,
        lens_version=ctx.lens_version_constraint,
    )

    generated_at = ...   # existing marker loop follows, now also covers the compose files
```

- [ ] **Step 4: Run → PASS.** `Run: uv run pytest tests/pipeline/test_orchestrate_compose.py -q`

- [ ] **Step 5: Commit.** `git add src/grace/pipeline/orchestrate.py tests/pipeline/test_orchestrate_compose.py && git commit -m "feat(pipeline): emit compose surface in run_pipeline before marker stamping"`

---

## Phase D — Rubric rewrite (the main validation gate)

> Largest phase. The rubric is static-AST + Lens-free (`docs_build.py` style). Build the resolver once here; reuse in Phase E. Read `src/grace/quality_rubric.py` fully first: `Run: sed -n '1,90p' src/grace/quality_rubric.py`.

### Task 12: Register-arg discovery + static capability-composition check

**Files:** Modify `src/grace/quality_rubric.py`. Create `tests/fixtures/connectors/compliant/**` + `tests/fixtures/connectors/bare_connector/**`. Test: `tests/test_quality_rubric_v2.py`

- [ ] **Step 1: Build fixtures.** `tests/fixtures/connectors/compliant/` = a minimal domain-modular package (root `__init__.py` with `ConnectorFactory.register("demo", DemoConnector)` + `register_webhook`; `connector.py` `class DemoConnector(DemoOrders, DemoSubscriptions)`; `core/base.py` `_DemoBase(Connector)`; `orders/connector.py` `class DemoOrders(_DemoBase, PaymentsConnector)` with the 4 flows + 2 props; `subscriptions/connector.py` `class DemoSubscriptions(_DemoBase, MandateConnector)` with 5 lifecycle + 4 introspection; `webhooks.py` `build_webhook_handlers`). `bare_connector/` = same but the registered class subclasses bare `Connector`.

- [ ] **Step 2: Failing test.**

```python
# tests/test_quality_rubric_v2.py
from pathlib import Path
from grace.quality_rubric import resolve_registered_class, composition_findings
FX = Path("tests/fixtures/connectors")
def test_resolve_registered_class_from_register_call() -> None:
    cls = resolve_registered_class(FX / "compliant")
    assert cls.name == "DemoConnector"
    assert {"PaymentsConnector", "MandateConnector"} <= set(cls.capability_bases)
def test_bare_connector_flagged() -> None:
    issues = composition_findings(FX / "bare_connector")
    assert any("capability interface" in i for i in issues)
def test_compliant_has_no_composition_issues() -> None:
    assert composition_findings(FX / "compliant") == []
```

- [ ] **Step 3: Run → FAIL.** `Run: uv run pytest tests/test_quality_rubric_v2.py -q`

- [ ] **Step 4: Implement the resolver.** Parse `__init__.py` for the 2nd positional arg of `ConnectorFactory.register(...)`; follow its import to the defining module; AST-walk the class + its base classes across `core/`/domain modules to collect the transitive base names; expose `name` + `capability_bases` (intersection with `{"PaymentsConnector","MandateConnector"}`). `composition_findings(pkg)` returns issues if no capability base is present (bare `Connector`) or a referenced base class can't be resolved.

- [ ] **Step 5: Run → PASS.** `Run: uv run pytest tests/test_quality_rubric_v2.py -q`

- [ ] **Step 6: Commit.** `git add src/grace/quality_rubric.py tests/test_quality_rubric_v2.py tests/fixtures/connectors && git commit -m "feat(rubric): register-arg discovery + static capability-composition check"`

### Task 13: Domain-modular required-files + per-domain method checks (retire `handle_webhook`/flat constants)

**Files:** Modify `src/grace/quality_rubric.py`. Create `tests/fixtures/connectors/missing_mandate_method/**`, `tests/fixtures/connectors/orders_only/**`. Test: extend `tests/test_quality_rubric_v2.py`

- [ ] **Step 1: Failing test** — present-domain methods required; absent domain not penalized (C1):

```python
def test_subscriptions_requires_lifecycle_and_introspection() -> None:
    from grace.quality_rubric import _score_public_surface_v2
    dim = _score_public_surface_v2(FX / "missing_mandate_method")
    assert dim.score < dim.max and "cancel_subscription" in dim.detail
def test_orders_only_not_penalized_for_missing_mandate(tmp_path) -> None:
    from grace.quality_rubric import _score_public_surface_v2
    dim = _score_public_surface_v2(FX / "orders_only")
    assert dim.score == dim.max          # payments-only PSP is complete (C1)
```

- [ ] **Step 2: Run → FAIL.** `Run: uv run pytest tests/test_quality_rubric_v2.py -q`

- [ ] **Step 3: Implement.** Replace `REQUIRED_FLOW_METHODS` (drop `handle_webhook`) and the flat `REQUIRED_FILES`/`REQUIRED_TEST_LEAVES` with domain-modular sets: always `core/base.py`,`core/auth.py`,`core/status.py`,`core/models.py`, root `connector.py`,`webhooks.py`,`__init__.py`; for each **present** domain (detected via the domain subfolders) its `connector.py`/`status_map.py`/`webhooks.py` + the required methods (orders → 4 flows + 2 props; subscriptions → `create_subscription`/`sync_subscription`/`cancel_subscription`/`pause_subscription`/`resume_subscription` + `supported_mandate_rails`/`supports_pause`/`supported_intervals`/`max_mandate_amount`). Resolve methods across the mixin's MRO. Require `ConnectorFactory.register` AND `register_webhook` in `__init__.py`, and `build_webhook_handlers` in root `webhooks.py`.

- [ ] **Step 4: Run → PASS.** `Run: uv run pytest tests/test_quality_rubric_v2.py -q`

- [ ] **Step 5: Commit.** `git add -A && git commit -m "feat(rubric): domain-modular public-surface checks; retire handle_webhook/flat layout"`

### Task 14: Relocate webhook-signature/error-handling check + add modern-typing + status-map coverage checks

**Files:** Modify `src/grace/quality_rubric.py`. Create fixtures `missing_register_webhook/`, `uses_optional/`, `unmapped_subscription_status/`. Test: extend.

- [ ] **Step 1: Failing tests.**

```python
def test_missing_register_webhook_docks_public_surface() -> None:
    from grace.quality_rubric import _score_public_surface_v2
    assert _score_public_surface_v2(FX / "missing_register_webhook").score < 20
def test_deprecated_typing_alias_docks_type_dimension() -> None:
    from grace.quality_rubric import modern_typing_findings
    assert modern_typing_findings(FX / "uses_optional")        # flags `Optional`
    assert not modern_typing_findings(FX / "compliant")         # Callable/Mapping/Any allowed
def test_error_handling_checks_root_webhooks_signature() -> None:
    from grace.quality_rubric import _score_error_handling_v2
    assert _score_error_handling_v2(FX / "compliant").score == 20  # WEBHOOK_SIGNATURE_FAILED in webhooks.py
```

- [ ] **Step 2: Run → FAIL.** `Run: uv run pytest tests/test_quality_rubric_v2.py -q`

- [ ] **Step 3: Implement.** (a) Move the `WEBHOOK_SIGNATURE_FAILED` assertion from `connector.py`/`handle_webhook` to root `webhooks.py` (`build_webhook_handlers` present + `verify` wired). (b) `modern_typing_findings(pkg)` flags imports of `Dict`/`List`/`Optional`/`Set`/`Tuple`/`FrozenSet`/`Type` from `typing` and allows `Callable`/`Mapping`/`Any`/`Literal`/`Iterable`/`Sequence`; fold into `_score_type_correctness` or `_score_public_surface_v2`. (c) status-map coverage: each present domain's `status_map.py` references the right enums (`PaymentAttemptStatus`/`PaymentFailureCode` for orders; `MandateStatus`/`WebhookEventType` for subscriptions). Update `score_rubric` to call the v2 scorers (keep the 6 dimensions + weights).

- [ ] **Step 4: Run → PASS.** `Run: uv run pytest tests/test_quality_rubric_v2.py -q`

- [ ] **Step 5: Commit.** `git add -A && git commit -m "feat(rubric): root-webhook error check + modern-typing + per-domain status-map coverage"`

### Task 15: End-to-end rubric on a fully-runnable compliant fixture (≥60)

**Files:** Make `tests/fixtures/connectors/compliant/` import-clean + add a passing mini test-suite for it. Test: extend.

- [ ] **Step 1: Failing test** — score the compliant fixture through `score_rubric` with real mypy+pytest reports:

```python
def test_compliant_fixture_scores_at_least_60() -> None:
    # run real mypy + pytest --cov on the fixture, then score_rubric(...)
    from grace.pipeline.gates import run_mypy, run_pytest_with_cov
    from grace.quality_rubric import score_rubric
    pkg = FX / "compliant"
    rep = score_rubric(ctx=_ctx_for(pkg), output_dir=pkg,
                       mypy_report=run_mypy(target=pkg),
                       pytest_report=run_pytest_with_cov(target=pkg))
    assert rep.total >= 60, rep.to_json()
```

- [ ] **Step 2: Run → FAIL** (fixture not yet runnable/typed/tested). `Run: uv run pytest tests/test_quality_rubric_v2.py::test_compliant_fixture_scores_at_least_60 -q`

- [ ] **Step 3: Make the fixture real.** Flesh out `compliant/` so it imports `lens` cleanly, passes `mypy --strict`, and ships a small `tests/` (or co-located) suite that exercises ≥80% of its lines (stub HTTP via `httpx.MockTransport`). This is the one runnable fixture; the per-defect fixtures from Tasks 12–14 stay static (assert per-dimension docking only).

- [ ] **Step 4: Run → PASS.** `Run: uv run pytest tests/test_quality_rubric_v2.py -q`

- [ ] **Step 5: Commit.** `git add -A && git commit -m "test(rubric): runnable compliant fixture scores >= 60 end-to-end"`

---

## Phase E — docs_build + skill + version bump

### Task 16: `docs_build.py` understands the composed class

**Files:** Modify `src/grace/docs_build.py`. Test: `tests/test_docs_build_v2.py`

- [ ] **Step 1: Failing test** — `introspect_connector` finds `DemoConnector` + its capabilities for the compliant fixture.

```python
def test_docs_build_finds_composed_class() -> None:
    from grace.docs_build import introspect_connector
    s = introspect_connector(Path("tests/fixtures/connectors/compliant"))
    assert s.class_name == "DemoConnector"
    assert "create_subscription" in s.flows or "subscriptions" in getattr(s, "domains", [])
```

- [ ] **Step 2: Run → FAIL.** `Run: uv run pytest tests/test_docs_build_v2.py -q`

- [ ] **Step 3: Implement.** Reuse Task 12's `resolve_registered_class` (don't build a second resolver). Make `LOCKED_FLOWS` capability-keyed (drop `handle_webhook`; add the mandate lifecycle); gather status-map keys from per-domain `status_map.py`.

- [ ] **Step 4: Run → PASS.** `Run: uv run pytest tests/test_docs_build_v2.py -q`

- [ ] **Step 5: Commit.** `git add src/grace/docs_build.py tests/test_docs_build_v2.py && git commit -m "feat(docs-build): discover composed connector class + capabilities"`

### Task 17: Update the `add-connector` skill for the new shape

**Files:** Modify `src/grace/skills_templates/add-connector/SKILL.md`, `references/rubric-checklist.md`, `references/flow-patterns/**`.

- [ ] **Step 1:** Update the Phase-5 review checklist (class is `<Psp>Connector` composing mixins; `register` + `register_webhook`; `core/`+domain layout; `--domain`); update `rubric-checklist.md` to the new public-surface checks; add mandate flow-patterns + rewrite the webhook one to the shared router.
- [ ] **Step 2: Validate** the skill still installs: `Run: uv run grace skills install --output /tmp/skilltest --force && ls /tmp/skilltest/.skills`.
- [ ] **Step 3: Commit.** `git add src/grace/skills_templates && git commit -m "docs(skill): update add-connector for domain-modular mandate codegen"`

### Task 18: Version bump → 0.6 + full suite

**Files:** Modify `pyproject.toml`.

- [ ] **Step 1:** Bump the project version to `0.6.0`. `Run: sed -n '1,30p' pyproject.toml` to find the exact key first, then edit.
- [ ] **Step 2: Full green run.** `Run: uv run pytest -q` (all Grace tests pass) and `Run: uv run mypy --strict src` (clean).
- [ ] **Step 3: Commit.** `git add pyproject.toml && git commit -m "chore: bump Grace to v0.6 (domain-modular mandate codegen)"`

---

## Self-Review (run before handing off)

- **Spec coverage:** R1→T1–T3; R2→T7–T8; R3→T9; R4→T10–T11; R5→T12–T15; R6→T5; R7→T6; R8→T4; R9→T16; R10→T17; v0.6→T18; C1→T10/T13; C2→T7/T11; C3→T11 (marker loop). No spec requirement is unmapped.
- **Deferred (not in this plan, by design):** live Cashfree regen, un-quarantine, `test_legacy_isolation.py`, sandbox (spec Non-Goals / Phase F).
- **Type consistency:** `resolve_registered_class` (T12) is reused by T13/T16; `write_compose_surface` signature is identical in T10 and T11; `filter_urls_by_domain`/`bucket_for_url` defined in T1 are used in T2.

---

## Open items to confirm during execution (non-blocking)

- OQ-A: exact static class-resolution mechanism (import-following AST vs emitted module→class map) — settle in Task 12.
- OQ-B: whether `--domain all` re-runs overwrite `core/` idempotently (lean yes; never on single-domain runs).
- Verify the real Cashfree subscription doc-page URL shapes when first running `fetch-docs` for real, and tune `DOMAIN_INCLUDE_GLOBS` (Task 1 Step 5) — the globs are a starting set.
