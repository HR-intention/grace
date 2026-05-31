---
name: Grace Domain-Modular Mandate Codegen — Implementation Spec
description: What to change in Grace (fetch-docs, pipeline, a Grace-owned compose step, rulebook, rubric) to emit domain-modular, mandate-capable connectors against lens 0.2.0 with a --domain axis and incremental per-domain regeneration. Scope = extend Grace + validate via Grace's own tests; the live Cashfree regen is deferred.
type: implementation-spec
status: Reviewed — independent review incorporated 2026-05-31; OQ-1 (compose surface) + OQ-4 (v0.6) resolved; ready for /writing-plans.
created: 2026-05-31
authors: Sarthak + Claude
related:
  - docs/superpowers/specs/SUBPROJECT_GRACE_CODEGEN.md   # design of record (§3.2 layout, §5 rubric)
  - docs/superpowers/specs/2026-05-30-grace-mandate-codegen-handoff.md   # lens 0.2.0 ABCs/webhook/§6 normalization
  - docs/superpowers/specs/ORBIT_CONSTITUTION.md         # §4 marker, §8 versioning
---

# Grace Domain-Modular Mandate Codegen — Implementation Spec

> **Design of record:** `SUBPROJECT_GRACE_CODEGEN.md` (§3.2 layout, §5 rubric). This spec
> enumerates the concrete Grace changes, acceptance criteria, validation, phasing, and the
> few remaining open questions. Version target: **Grace v0.6** (major tool bump, pre-1.0).

## Problem Statement

lens 0.2.0 locked a capability-interface model (`Connector` thin base + `PaymentsConnector`
/ `MandateConnector`), a shared `WebhookRouter`/`WebhookHandlers`, and mandate domain types.
Grace's rulebook, generation prompt, and rubric are all still on the old lens-0.1 shape
(bare `class Cashfree(Connector)`, on-connector `handle_webhook`, four payment flows, no
mandates), and `fetch_docs.py` *deliberately excludes* subscription/mandate doc pages. As-is,
the rubric would even **fail a correct 0.2.0 connector** (it requires `handle_webhook` and
matches the class by name). Until Grace is extended, no mandate-capable connector can be
generated, blocking Orbit's Phase-3 periodic mandates.

## Goals

1. Grace generates **domain-modular, mandate-capable** connectors conforming to lens 0.2.0:
   per-capability mixins `<Psp>Orders(_<Psp>Base, PaymentsConnector)` /
   `<Psp>Subscriptions(_<Psp>Base, MandateConnector)` over a shared base `_<Psp>Base(Connector)`,
   composed into one registered `<Psp>Connector`, plus a shared `build_webhook_handlers`
   registered via `register_webhook`.
2. A `--domain {orders|subscriptions|all}` axis on `fetch-docs` and `generate` (default `all`),
   with **incremental per-domain regeneration**. `--domain all` generates exactly the domains the
   PSP supports (skips absent ones — see Cross-Cutting C1).
3. `fetch-docs` pulls subscription/mandate docs (grouped under `_shared/`/`orders/`/`subscriptions/`)
   and scaffolds a developer-editable `connector_docs/<psp>.md` spec that carries the §6 normalization.
4. **Grace owns the deterministic compose surface** (root `connector.py`/`webhooks.py`/`__init__.py`),
   templated from the set of present domains — so incremental regen is robust.
5. The rubric verifies the new shape: `register()`-arg discovery, static capability composition,
   per-domain files, mandate methods + introspection, status-map coverage, modern typing.
6. **Everything is validated by Grace's own `pytest` suite** — no live connector generation is
   required to land this effort.

## Non-Goals (this effort)

- **Live Cashfree regeneration** into the lens repo, **un-quarantining**, or editing
  `tests/unit/test_legacy_isolation.py` — deferred to a later real `grace generate` run.
- **Live Cashfree sandbox** rail testing (UPI Autopay / card e-mandate authorize/debit/decline,
  the `ON_HOLD`→`MANDATE_SUSPENDED` confirmation, handoff §9 "L9") — deferred with the regen.
- **On-demand mandate debit** (`execute_mandate_debit` / `notify_pre_debit`) — out of scope
  (constitution §7; periodic mode is PSP-driven).
- **`ClaudeCodeRunner` / AI-backend changes** — unaffected.
- **Generating a new PSP** (Razorpay) — the generic rulebook must *stay* reusable for it, but no
  new PSP is generated here.
- **Syncing the symplora governance copy** of `SUBPROJECT_GRACE_CODEGEN.md` — synced manually by
  the owner, outside this effort.

## User Stories

- As a **connector author**, I run `grace fetch-docs cashfree --from <llms.txt> --domain all`
  and get domain-grouped doc snapshots plus a `connector_docs/cashfree.md` scaffold I edit before
  generating.
- As a **connector author**, I run `grace generate cashfree --domain all` and get a domain-modular,
  gate-passing connector whose registered `CashfreeConnector` is-a `PaymentsConnector` **and** a
  `MandateConnector`.
- As a **connector author**, I run `grace generate cashfree --domain subscriptions` against an
  existing payments-only package and the mandate capability is added **without touching the payment
  side** (`orders/` and `core/` unchanged).
- As a **connector author** integrating a payments-only PSP, `--domain all` produces just
  `orders/` + `<Psp>Connector(<Psp>Orders)` (a `PaymentsConnector`), with no `subscriptions/`, no
  `parse_mandate`, and no mandate rubric requirements (Cross-Cutting C1).
- As a **Grace maintainer**, the rubric fails a connector that subclasses bare `Connector`, omits
  `register_webhook`/`build_webhook_handlers`, leaves a documented subscription status unmapped, or
  uses `Dict`/`Optional`/bare generics.

## Cross-Cutting Rules

- **C1 — Capability presence ("handle absent domains elegantly").** A PSP supports a domain iff
  `connector_docs/<psp>/<domain>/` exists and is non-empty (populated by `fetch-docs --domain`).
  `generate --domain all` generates exactly the present domains; an absent domain is simply omitted
  — **no empty folder, no stubbed mixin**. The compose surface (R4) composes only present domain
  classes (`<Psp>Connector(<Psp>Orders)` for a payments-only PSP; no `parse_mandate`). The rubric
  (R5) requires only the present domains' surface. An explicit `generate --domain subscriptions`
  for a PSP with no subscriptions docs **errors clearly** (does not silently no-op).
- **C2 — First creation vs incremental.** Initial creation uses `--domain all`, which bootstraps
  `core/` + all present domains + the compose surface in one pass. An incremental single-domain run
  (`--domain subscriptions`) **assumes `core/` exists and never touches it**; it (re)writes only that
  domain's folder and then Grace regenerates the compose surface (R4).
- **C3 — Markers.** Every emitted `.py` carries the constitution §4 marker — including the
  **Grace-templated** compose-surface files (R4), stamped via `templates/marker.j2`, not just the
  Claude-written per-domain/`core/` files.

## Requirements

### P0 — Must have

**R1. `fetch_docs.py`: `--domain` presets + per-URL domain routing + spec scaffold.**
- Add `--domain {orders|subscriptions|all}` (default `all`) to the `fetch-docs` CLI command and
  `fetch_docs()`. Map each domain to an include/exclude preset over today's globs: `orders` =
  current payment globs; `subscriptions` = `*subscription*`/mandate/plans/payment-for-mandate globs;
  both always include the shared set (auth, overview, errors, webhook signature-verification);
  `all` = union. Drop the `*subscription/*` / `*mandate*` / `*setup-mandate*` exclusions; **keep
  excluding the legacy `*subscriptionsv1*`**.
- **Per-URL routing (net-new).** `filter_urls` currently returns a flat kept-list; add a
  classifier that labels each kept URL with its bucket (which domain's glob set matched; shared-set
  → `_shared`) and write pages into `connector_docs/<psp>/_shared/` + `connector_docs/<psp>/<domain>/`.
- **Spec scaffold (net-new).** `fetch_docs()` today writes only fetched pages. Add a step that writes
  `connector_docs/<psp>.md` (sibling to `<psp>/`) **only when absent, or with `--force`** — never
  clobbering developer edits. Fetched per-page files remain index-overwritten as today; only the
  `<psp>.md` spec gets clobber-protection. Scaffold = connector-info header (pre-filled where
  trivially derivable) + **minimal** skeleton normalization tables (lens-target columns fixed,
  PSP-term cells left for the developer). *(Scaffold pre-fill stays minimal — locked, see Decisions.)*
- **AC:** unit tests cover (a) each `--domain` selecting the right globs, (b) per-URL bucket routing
  into `_shared`/`<domain>`, (c) `subscriptionsv1` still excluded, (d) scaffold created when absent,
  (e) scaffold NOT clobbered when present without `--force`, (f) `--force` overwrites it.

**R2. `pipeline/context.py` + `pipeline/types.py`: domain-aware context.**
- Add `domain: str` to the real `GenerationContext` in `types.py`; add a `domain` parameter to
  `assemble_context`. The source bundle = `connector_docs/<psp>.md` + `connector_docs/<psp>/_shared/`
  + the active domain folder(s).
- Convert `RULEBOOK_FILES` (a flat module constant) into a **domain-keyed selection** (function):
  always include the core python rules; include orders patterns for `orders`, mandate patterns for
  `subscriptions`, both for `all`. (Resolves OQ-3: domain-scope the *patterns* to keep incremental
  context lean.)
- **AC:** tests assert the assembled bundle per `--domain` contains the right doc folders, the
  `<psp>.md` spec, and the right rulebook/pattern subset.

**R3. `pipeline/prompt.py`: domain-aware prompt + new locked-surface guardrails.**
- Rewrite `PROMPT_TEMPLATE` for the lens-0.2.0 / domain-modular shape. The prompt asks Claude to
  write **only** the per-domain mixin(s) for the requested `--domain` and (on first creation) the
  `core/` files — **not** the compose surface (Grace owns that, R4).
- **Full, exact import block** (mirror the precision of the current template's item 2):
  `from lens.connector import Connector`; `from lens.payments_connector import PaymentsConnector`;
  `from lens.mandate_connector import MandateConnector`; `from lens.webhook import WebhookHandlers,
  WebhookFamily`; `from lens.factory import ConnectorFactory, ConnectorConfig`; the needed
  `lens.domain_types` mandate types; and `from lens.enums import MandateRail, MandateIntervalType,
  MandateStatus, MandateDebitStatus, WebhookEventType, PaymentFailureCode, FailureClass,
  FAILURE_CLASS, PaymentMethod, ConnectorErrorReason`.
- Class shape: `class <Psp>Orders(_<Psp>Base, PaymentsConnector)` / `class <Psp>Subscriptions(
  _<Psp>Base, MandateConnector)`; `_<Psp>Base(Connector)` owns `name`/`base_url`/`close`/`__init__`
  (the ONE `httpx.AsyncClient`)/`_config`. Domain parsers: `_parse_payment_webhook(raw: bytes) ->
  PaymentWebhookEvent` and `_parse_mandate_webhook(raw: bytes) -> MandateWebhookEvent`; the cross-domain
  `_classify(raw: bytes) -> WebhookFamily` (SUBSCRIPTION_* → `WebhookFamily.MANDATE`, else
  `WebhookFamily.PAYMENT`) is part of the Grace-owned compose surface (R4), not Claude's job.
- **Retire** the bare-`Connector` and "no `Connector` suffix" pitfalls; update the self-check greps
  to the new structure. The modern-typing self-check flags **deprecated aliases only**
  (`Dict`/`List`/`Optional`/`Set`/`Tuple`/`FrozenSet`/`Type` from `typing`) and explicitly allows
  `Callable`/`Mapping`/`Any`/`Literal`/`Iterable` (lens itself imports these).
- Make the prompt **domain-conditional** (emit only the relevant domain's instructions for a scoped run).
- **AC:** tests assert the rendered prompt per `--domain` includes the right imports (incl.
  `WebhookFamily`/`lens.enums`/`lens.factory`), the mixin/base composition rules, the per-domain
  file list, and the deprecated-alias-only typing check; and omits the retired pitfalls + the
  compose-surface instructions.

**R4. Grace-owned compose surface (net-new templated post-step).**
- After Claude writes the per-domain mixins + `core/`, a deterministic Grace step scans the present
  `connectors/<psp>/{orders,subscriptions}/` folders and emits:
  - root `connector.py` — `class <Psp>Connector(<present domain classes>): pass` (e.g.
    `(<Psp>Orders, <Psp>Subscriptions)`, or `(<Psp>Orders)` for a payments-only PSP);
  - root `webhooks.py` — `build_webhook_handlers(config) -> WebhookHandlers` wiring
    `verify=core.auth.verify_signature`, `classify=_classify`, and `parse_payment`/`parse_mandate`
    **only for present domains** (absent → left `None`); plus `_classify`;
  - root `__init__.py` — `requires_lens = "^0.2"`, `ConnectorFactory.register("<psp>", <Psp>Connector)`,
    `ConnectorFactory.register_webhook("<psp>", build_webhook_handlers)`.
- Each templated file is **§4-marker-stamped** via `templates/marker.j2` (C3). Incremental runs
  (C2) regenerate this surface from the then-present domains; first creation generates it once.
- **AC:** unit tests render the compose surface for (a) both domains present and (b) orders-only,
  asserting the composed base list, the `WebhookHandlers` wiring (mandate parser `None` when absent),
  the registration calls, `requires_lens`, and the marker on each file.

**R5. `quality_rubric.py`: register-arg discovery + static composition / per-domain / typing.** *(Largest single item.)*
- **Discovery rewrite (from scratch).** Replace name-match discovery: parse the **second positional
  arg** of `ConnectorFactory.register("<psp>", X)` in `__init__.py`; resolve `X` across the package's
  modules (root `connector.py`'s imports of the domain mixins); compute, **statically (Lens-free
  AST, across the MRO)**, that the registered class isinstance-composes ≥1 capability interface and
  has **zero leftover abstract methods** — never bare `Connector`.
- **Retire old constants/checks:** remove `handle_webhook` from required flow methods; replace the
  flat `REQUIRED_FILES`/`REQUIRED_TEST_LEAVES` with the domain-modular set (`core/base.py`,
  `core/auth.py`, `core/status.py`, `core/models.py`; root `connector.py`+`webhooks.py`+`__init__.py`;
  per **present** domain `connector.py`/`status_map.py`/`webhooks.py`; tests
  `tests/integration/connectors/<psp>/<domain>/` + `test_webhook_router.py`). Relocate the
  webhook-signature assertion from `connector.py`/`handle_webhook` to root `webhooks.py`
  (`build_webhook_handlers` present; `verify` wired; `_classify -> WebhookFamily`).
- **Per-domain requirements:** payment flows for an `orders` domain; the 5 lifecycle + 4
  introspection methods for a `subscriptions` domain; `register` **and** `register_webhook`; per-domain
  `status_map.py` coverage (payments → `PaymentAttemptStatus`/`PaymentFailureCode`; subscriptions →
  `MandateStatus`/`WebhookEventType`; unmapped → fallback + warning). Add a **modern-typing** check
  scoped to deprecated aliases (allow `Callable`/`Mapping`/`Any`/`Literal`/`Iterable`).
- Keep the **6 dimensions + weights** (subproject §5).
- **AC (fixtures):** one **fully-runnable** compliant mini-connector fixture (real `mypy --strict` +
  a passing test suite) scores **≥ 60** (exercising the coverage + type dimensions end-to-end); plus
  **static** per-defect fixtures, one per seeded defect (bare `Connector`; missing `register_webhook`;
  missing a mandate method; unmapped subscription status; an `Optional` import; missing
  `build_webhook_handlers`), each asserting **exactly the matching dimension docks** points.

**R6. `rulesbook/codegen/python/*.md`: reshape the generic rulebook (PSP-agnostic).**
- `connector_abc.md` — capability split; the mixin + compose pattern; shared-base ownership of
  identity/lifecycle/the single httpx client; `MandateConnector` is **singular**.
- `domain_types.md` — mandate request/response + webhook domain types (import from `lens`; never
  redeclare).
- `webhook_handling.md` — the **shared** `WebhookHandlers`/`WebhookRouter` (NOT a connector method);
  `_classify -> WebhookFamily` (PAYMENT/MANDATE); the two parsers; `WEBHOOK_SIGNATURE_FAILED` /
  `NOT_SUPPORTED` semantics; that the router/handlers are assembled by Grace's compose surface.
- `status_mapping.md` — the reusable **methodology**: subscription_status→`MandateStatus`,
  event→`WebhookEventType`, failure free-text→`(PaymentFailureCode, FailureClass)` via ordered
  substring match defaulting `UNKNOWN`; the **periodic-mode finality rule** (*no `*_FAILED_FINAL`
  event; finality = `MANDATE_SUSPENDED` + `psp_attempt`*); and the **`FAILURE_CLASS` published-data
  rule** (connector sets `failure_code` only — `MandateDebitOutcome.failure_code: PaymentFailureCode
  | None`; `FAILURE_CLASS` is imported from `lens` for reference, **never branched on, never
  redeclared**; orbit reads `FAILURE_CLASS[code]`). The shared failure-substring map lives in
  `core/status.py`, consumed by both domains.
- `file_layout.md` — `core/{base,auth,status,models}.py` + per-domain + the Grace-owned compose
  surface. `testing.md` — per-domain tests + the cross-domain webhook-router test (incl. the
  **tampered-signature → `ConnectorError(WEBHOOK_SIGNATURE_FAILED)`** case). `pitfalls.md` — modern
  typing (deprecated aliases), one-client base, singular `MandateConnector`, no surgical hand-edits.
  `README.md` — reading order.
- **AC:** the rulebook stays PSP-agnostic (no Cashfree specifics) so Razorpay-from-scratch still works.

**R7. New mandate flow-patterns under `rulesbook/codegen/guides/patterns/`.**
- `pattern_create_subscription.md` — inline plan; a worked skeleton mapping **every**
  `CreateSubscriptionRequest` field (incl. `customer_contact.email`/`.phone` → both required
  `customer_details.*`; `first_charge_at` → `subscription_first_charge_time` *PERIODIC only*;
  `subscription_meta.notification_channel = [SMS, EMAIL]`; `return_url` → `subscription_meta.return_url`;
  `rail` → `authorization_details.payment_methods`; `upi_vpa`, `description`); `idempotency_key` as
  the Cashfree idempotency token.
- `pattern_sync_subscription.md`; `pattern_manage_mandate.md` (cancel/pause/`resume`=`ACTIVATE`,
  `effective_at`→`action_details.next_scheduled_time`; **`idempotency_key` forwarded on all three**);
  mandate-webhook parsing. Rewrite the incoming-webhook pattern for the shared router (replacing the
  on-connector `handle_webhook`).
- **AC:** each pattern has locked signature, step list, skeleton, required tests, pitfalls — matching
  the existing payment patterns' shape.

**R8. `connector_docs/cashfree.md`: author the §6 normalization (from scratch).**
- The relocated file is an auth/endpoint dump with **no** normalization. **Author** the per-PSP spec
  (the prior endpoint-inventory content is fetched-doc material and is replaced). Transcribe handoff
  §6 into: a **Shared** section (failure free-text → `(PaymentFailureCode, FailureClass)`, the 11-row
  substring map + default `UNKNOWN`; the `FAILURE_CLASS` published-data note) and a **Subscriptions**
  section (subscription_status → `MandateStatus`; event → `WebhookEventType`; rail → payment_methods;
  the full create-request field map).
- **Must explicitly include** the load-bearing edge rows: `INITIALIZED`/`BANK_APPROVAL_PENDING`→
  PENDING_AUTHORIZATION; `ON_HOLD`→SUSPENDED; `CARD_EXPIRED`→SUSPENDED; `LINK_EXPIRED`→FAILED;
  `SUBSCRIPTION_AUTH_STATUS`(ACTIVE/FAILED)→MANDATE_AUTHORIZED/REJECTED; `SUBSCRIPTION_PAYMENT_FAILED`
  → MANDATE_DEBIT_FAILED with `psp_attempt = retry_attempts`; `SUBSCRIPTION_PAYMENT_CANCELLED` →
  MANDATE_DEBIT_FAILED with `failure_code = USER_CANCELLED`; `SUBSCRIPTION_PAYMENT_NOTIFICATION_INITIATED`
  → MANDATE_DEBIT_NOTIFIED; `SUBSCRIPTION_CARD_EXPIRY_REMINDER` → MANDATE_EXPIRING_SOON;
  `SUBSCRIPTION_REFUND_STATUS` → reuse refund handling (out of core mandate scope); the *no
  `*_FAILED_FINAL`* note; and **`UPI_AUTOPAY` debit failure → `MANDATE_SUSPENDED`** (the open L9 item).
- **AC:** a Phase-A test greps `cashfree.md` for: `CARD_EXPIRED`, `LINK_EXPIRED`, `MANDATE_DEBIT_NOTIFIED`,
  `MANDATE_EXPIRING_SOON`, `USER_CANCELLED`, `retry_attempts`, `SUBSCRIPTION_REFUND_STATUS`,
  `UPI_AUTOPAY`, and `FAILURE_CLASS` — all present.

### P1 — Should have

**R9. `docs_build.py`: understand the composed class / capabilities.**
- `_connector_class` won't find `class <Psp>Connector(<Psp>Orders, <Psp>Subscriptions)` (no `Connector`
  base in its bases). **Reuse R5's register-arg + MRO resolver** (don't build a second). Make
  `LOCKED_FLOWS` capability-keyed (drop `handle_webhook`; add mandate methods); gather status-map keys
  from per-domain `status_map.py` files. (`grace docs` is auto-run post-generate; best-effort.)

**R10. `skills_templates/add-connector/`: keep the orchestration skill consistent.**
- Update `SKILL.md` (Phase-5 review checklist), `references/rubric-checklist.md`, and
  `references/flow-patterns/` to the new shape (`--domain`, mixin composition, Grace-owned compose
  surface, shared webhook, mandate flows).

### P2 — Future considerations (design-for, do not build)

- A third domain (e.g. `payouts`) slots in as another `<domain>/` + mixin + a recomposed surface, with
  **no `core/` change**.
- On-demand mandate debit methods (deferred).
- Live Cashfree regen + un-quarantine + sandbox (deferred — see Non-Goals).

## Success Metrics (acceptance gates for THIS effort)

- Grace's own `pytest` suite passes, including the new tests for R1–R5 (and R9 where covered).
- The **fully-runnable** compliant rubric fixture scores **≥ 60** (incl. real coverage + `mypy`), and
  each **static per-defect** fixture docks exactly its matching dimension (R5 AC).
- `mypy --strict` clean on Grace's own `src/`.
- Rulebook/prompt reviewed against the locked lens 0.2.0 surface (imports/types/methods match).
- *(Deferred, not measured now: a generated Cashfree connector passing `mypy`/`pytest --cov ≥ 80`/
  rubric ≥ 60, and the sandbox rails.)*

## Decisions Locked (2026-05-31)

- **Compose surface:** Grace-owned/templated (OQ-1 → R4). Claude writes only per-domain mixins + `core/`.
- **First creation:** `--domain all` bootstraps `core/` + present domains + compose surface;
  incremental single-domain runs assume `core/` exists and never touch it (C2). `--domain all`
  generates only the domains the PSP supports (C1).
- **Version:** Grace **v0.6** (major tool bump, pre-1.0).
- **Scaffold pre-fill:** minimal (write-if-absent / `--force`; never clobber) — not aggressive doc-scan.
- **Governance copy:** symplora mirror synced manually by the owner — out of scope here.

## Open Questions (remaining — non-blocking)

- **OQ-A (eng).** Exact mechanism for R5/R9 to resolve a class symbol across modules statically
  (import-following in AST vs a small registry of emitted module→class). Resolve during R5 design;
  does not block planning.
- **OQ-B (eng).** Whether `core/` is rewritten on `--domain all` re-runs (idempotent overwrite) or
  treated as create-once. Lean: idempotent overwrite (deterministic), but never on single-domain runs.

## Timeline / Phasing

- **Phase A** — R1 (`fetch_docs` `--domain` + routing + scaffold) + R8 (author `cashfree.md` §6,
  with the grep-AC) + tests. *(R8 is authoring, not restructuring — budget accordingly.)*
- **Phase B** — R6 (rulebook reshape) + R7 (mandate patterns).
- **Phase C** — R3 (`prompt.py` domain-aware) + R2 (`context.py`/`types.py`) + **R4 (Grace-owned
  compose surface)**.
- **Phase D** — R5 (`quality_rubric.py` rewrite — the largest item) + Grace pytest fixtures (the main
  validation gate).
- **Phase E** — R9 (`docs_build.py`) + R10 (add-connector skill).
- **Deferred Phase F** — live Cashfree regen + un-quarantine + sandbox (separate session).

Phases A/B are independent and can run in parallel; C depends on B (patterns); D depends on A–C
(fixtures mirror the target shape + the compose surface).
