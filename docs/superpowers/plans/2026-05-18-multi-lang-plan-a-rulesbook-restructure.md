# Multi-Lang Connector Generation — Plan A: Rulesbook Restructure

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure `rulesbook/codegen/` into `rulesbook/codegen-rust/` plus extract language-neutral content to `rulesbook/shared/`, without changing what Grace's Rust output looks like. This is Phase 1 of the multi-lang design and unblocks every subsequent plan.

**Architecture:** Pure rename + content extraction + reference updates. No Python source code changes. Each task is one logical move (or one extraction) followed by reference cleanup, verified by `grep` for stale references and committed independently. The plan's acceptance gate is structural: every reference to a moved file resolves correctly.

**Tech Stack:** `git mv`, `sed`, `grep`, markdown editing. No Python or Rust compilation in this plan.

**Source spec:** [docs/superpowers/specs/2026-05-18-multi-lang-connector-generation-design.md](../specs/2026-05-18-multi-lang-connector-generation-design.md) — Sections 4.1, 4.2, 10 Phase 1.

---

## File structure

### Renamed (with `git mv`)
- `rulesbook/codegen/` → `rulesbook/codegen-rust/`
- `rulesbook/codegen-rust/guides/feedback.md` → `rulesbook/shared/feedback.md`
- `rulesbook/codegen-rust/guides/learnings/learnings.md` → `rulesbook/shared/learnings.md`
- `rulesbook/codegen-rust/connector_integration/template/tech_spec.md` → `rulesbook/shared/tech_spec_template.md`

### New files
- `rulesbook/shared/README.md` — explains what `shared/` is for
- `rulesbook/shared/flows.md` — flow definitions + prerequisite DAG (extracted from `codegen-rust/README.md`)
- `rulesbook/shared/payment_methods.md` — payment-method categories + types (extracted)
- `rulesbook/shared/quality_rubric.md` — scoring formula + cross-cutting checks (extracted)

### Modified files (path references only)
- `rulesbook/codegen-rust/.gracerules`
- `rulesbook/codegen-rust/.gracerules_add_flow`
- `rulesbook/codegen-rust/.gracerules_add_payment_method`
- `rulesbook/codegen-rust/README.md` (replace duplicated content with pointers to `shared/`)
- `rulesbook/codegen-rust/add_connector.sh`
- `workflow/1_orchestrator.md`
- `workflow/2_connector.md`
- `workflow/2.1_links.md`
- `workflow/2.2_techspec.md`
- `workflow/2.3_codegen.md`
- `workflow/2.4_pr.md`
- `README.md`
- `setup.md`
- `CLAUDE.md`
- `extract_source_urls_simple.sh`

### Untouched (Plan B handles these)
- All files under `src/`
- `pyproject.toml`, `main.py`, `.env.example`
- `.claude/`

---

## Tasks

### Task 1: Capture baseline reference inventory

**Files:**
- Create: `/tmp/grace-paths-before.txt` (scratch)
- Create: `/tmp/grace-files-before.txt` (scratch)

These are local artifacts for the acceptance gate at Task 14. Not committed.

- [ ] **Step 1: Snapshot every external reference to `rulesbook/codegen/`**

Run:
```bash
grep -rn 'rulesbook/codegen[^-]' \
  workflow/ README.md setup.md CLAUDE.md extract_source_urls_simple.sh \
  2>/dev/null | sort > /tmp/grace-paths-before.txt
wc -l /tmp/grace-paths-before.txt
```
Expected: a non-zero count (typical: 20-40 lines). This is the universe of references that will need to be rewritten. Note the count.

- [ ] **Step 2: Snapshot the file list under `rulesbook/codegen/`**

Run:
```bash
find rulesbook/codegen -type f | sort > /tmp/grace-files-before.txt
wc -l /tmp/grace-files-before.txt
```
Expected: a non-zero count (typical: 50-80 files). After the rename, the same count of files should exist under `rulesbook/codegen-rust/` plus 4 moved into `rulesbook/shared/`.

- [ ] **Step 3: Verify the working tree is clean before starting**

Run: `git status --short`
Expected: No output (clean tree). If anything is uncommitted, stash or commit it first — Plan A's tasks each produce isolated commits.

---

### Task 2: Rename `rulesbook/codegen/` → `rulesbook/codegen-rust/`

**Files:**
- Rename: `rulesbook/codegen/` → `rulesbook/codegen-rust/`

- [ ] **Step 1: Verify the source directory exists**

Run: `ls rulesbook/codegen/.gracerules rulesbook/codegen/.gracerules_add_flow rulesbook/codegen/.gracerules_add_payment_method`
Expected: all three files listed without error.

- [ ] **Step 2: Execute the rename with `git mv`**

Run: `git mv rulesbook/codegen rulesbook/codegen-rust`
Expected: silent success (no output).

- [ ] **Step 3: Confirm the new path**

Run: `ls rulesbook/codegen-rust/.gracerules rulesbook/codegen-rust/.gracerules_add_flow rulesbook/codegen-rust/.gracerules_add_payment_method`
Expected: all three files listed at the new path.

- [ ] **Step 4: Confirm the old path is gone**

Run: `ls rulesbook/codegen 2>&1 || true`
Expected: `ls: cannot access 'rulesbook/codegen': No such file or directory`

- [ ] **Step 5: Confirm git tracked the move as renames (not delete + add)**

Run: `git status --short | head -5`
Expected: lines start with `R` (rename), not paired `D`/`A` lines. If `git mv` was used correctly every file is `R`. If you see `D` + `A` pairs, run `git restore --staged .` and try again with `git mv`.

- [ ] **Step 6: Commit the rename in isolation**

Run:
```bash
git commit -m "refactor(rulesbook): rename codegen/ to codegen-rust/

Part of Phase 1 of multi-lang connector generation. External references
will be updated in subsequent commits."
```
Expected: commit succeeds. Verify with `git log -1 --stat | head -5`.

---

### Task 3: Update external path references (`codegen/` → `codegen-rust/`)

**Files:**
- Modify: `workflow/1_orchestrator.md`
- Modify: `workflow/2_connector.md`
- Modify: `workflow/2.1_links.md`
- Modify: `workflow/2.2_techspec.md`
- Modify: `workflow/2.3_codegen.md`
- Modify: `workflow/2.4_pr.md`
- Modify: `README.md`
- Modify: `setup.md`
- Modify: `CLAUDE.md`
- Modify: `extract_source_urls_simple.sh`

- [ ] **Step 1: Apply the path rewrite to every external file**

Run:
```bash
sed -i.bak 's|rulesbook/codegen/|rulesbook/codegen-rust/|g' \
  workflow/1_orchestrator.md \
  workflow/2_connector.md \
  workflow/2.1_links.md \
  workflow/2.2_techspec.md \
  workflow/2.3_codegen.md \
  workflow/2.4_pr.md \
  README.md \
  setup.md \
  CLAUDE.md \
  extract_source_urls_simple.sh
rm -f workflow/*.bak README.md.bak setup.md.bak CLAUDE.md.bak extract_source_urls_simple.sh.bak
```
Expected: silent success. Confirms each file's path references now end in `codegen-rust/`.

- [ ] **Step 2: Catch any references that omit the trailing slash (e.g., `rulesbook/codegen.gracerules` is unlikely but `grace/rulesbook/codegen` mid-sentence is possible)**

Run: `grep -rn 'rulesbook/codegen[^-/]' workflow/ README.md setup.md CLAUDE.md extract_source_urls_simple.sh 2>/dev/null || true`
Expected: NO output. If any matches appear, hand-edit each one to use `codegen-rust`.

- [ ] **Step 3: Catch any references that are bare `codegen/` without the `rulesbook/` prefix**

Run: `grep -rn '[^-]codegen/' workflow/ README.md setup.md CLAUDE.md 2>/dev/null | grep -v 'codegen-rust' | grep -v 'codegen-python' | grep -v 'connector_codegen' || true`
Expected: NO output. If matches appear, inspect each (some may be unrelated words like "decoder/" matching the trailing `coder/`). Fix any genuine stale refs.

- [ ] **Step 4: Diff one representative file to confirm the change is sensible**

Run: `git diff workflow/1_orchestrator.md | head -40`
Expected: every changed line shows `-...rulesbook/codegen/...` replaced with `+...rulesbook/codegen-rust/...`. No unintended changes.

- [ ] **Step 5: Commit the reference updates**

Run:
```bash
git add workflow/ README.md setup.md CLAUDE.md extract_source_urls_simple.sh
git commit -m "refactor(rulesbook): update external references to codegen-rust/

Workflow agents, top-level docs, and scripts now point at the renamed
codegen-rust/ directory."
```
Expected: commit succeeds.

---

### Task 4: Create `rulesbook/shared/` skeleton

**Files:**
- Create: `rulesbook/shared/README.md`

- [ ] **Step 1: Create the directory**

Run: `mkdir -p rulesbook/shared`
Expected: silent success. Verify with `ls -d rulesbook/shared`.

- [ ] **Step 2: Write `rulesbook/shared/README.md`**

Create `rulesbook/shared/README.md` with this exact content:

```markdown
# Shared rulesbook content

This directory holds language-neutral content used by every codegen pack
(`codegen-rust/`, `codegen-python/`, future `codegen-typescript/`).

## What lives here

| File | Purpose |
|---|---|
| `flows.md` | Authoritative flow list + prerequisite DAG |
| `payment_methods.md` | Payment-method categories and types |
| `quality_rubric.md` | Scoring formula + cross-cutting quality checks |
| `feedback.md` | Quality-review feedback database. Entries are tagged `[lang:rust]`, `[lang:python]`, or `[lang:*]` (cross-cutting). |
| `learnings.md` | Implementation lessons learned. Same tagging convention as feedback.md. |
| `tech_spec_template.md` | Template for the technical specification document. The spec describes the external PSP API — language-neutral by construction. |

## What does NOT live here

Anything language-specific:
- Pattern templates with concrete code → in `codegen-<lang>/guides/patterns/`
- Type-system references → in `codegen-<lang>/guides/types/types.md`
- Language-specific quality checks → in `codegen-<lang>/guides/quality/`

If a check or concept can be expressed without referring to a specific
language's syntax or types, it belongs in `shared/`. Otherwise it belongs
in the language pack.
```

- [ ] **Step 3: Commit the skeleton**

Run:
```bash
git add rulesbook/shared/README.md
git commit -m "feat(rulesbook): add shared/ skeleton for language-neutral content

Holds flow definitions, quality rubric, feedback, and learnings that
apply to every codegen language pack."
```
Expected: commit succeeds.

---

### Task 5: Move `feedback.md` to `shared/` and tag entries

**Files:**
- Rename: `rulesbook/codegen-rust/guides/feedback.md` → `rulesbook/shared/feedback.md`
- Modify: `rulesbook/shared/feedback.md` (add language tag)
- Modify: `rulesbook/codegen-rust/.gracerules`
- Modify: `rulesbook/codegen-rust/.gracerules_add_flow`
- Modify: `rulesbook/codegen-rust/.gracerules_add_payment_method`
- Modify: `rulesbook/codegen-rust/README.md`

- [ ] **Step 1: Verify the source file exists**

Run: `ls rulesbook/codegen-rust/guides/feedback.md`
Expected: file listed.

- [ ] **Step 2: Move the file**

Run: `git mv rulesbook/codegen-rust/guides/feedback.md rulesbook/shared/feedback.md`
Expected: silent success.

- [ ] **Step 3: Prepend a language-tag preamble to the file**

Add these lines at the very top of `rulesbook/shared/feedback.md` (above all existing content), preserving everything that was already there:

```markdown
> **Language tagging convention**
>
> All entries below this preamble were authored when Grace only generated
> Rust connectors. They are implicitly tagged `[lang:rust]`. New entries
> from any language pack MUST start with one of:
>
> - `[lang:rust]` — Rust-specific (UCS) feedback
> - `[lang:python]` — Python-specific feedback
> - `[lang:*]` — Cross-cutting feedback applicable to all language packs
```

- [ ] **Step 4: Verify the file's other content is still intact**

Run: `wc -l rulesbook/shared/feedback.md`
Expected: line count = (original line count) + 11 (the preamble has 11 lines including blank lines).

- [ ] **Step 5: Find and update every reference to the old path**

Run: `grep -rn 'guides/feedback.md\|guides/feedback\.md' rulesbook/codegen-rust/ 2>/dev/null`
Expected: a non-zero list of matches inside `.gracerules*` files and possibly `README.md`. Note each file and the surrounding context.

For each match, replace `guides/feedback.md` with `../shared/feedback.md` (the `../` is because `.gracerules*` files live at `rulesbook/codegen-rust/`, one level deep from `rulesbook/shared/`).

Bulk sed (verify the matches first via the grep above, then run):
```bash
find rulesbook/codegen-rust -type f \( -name '.gracerules*' -o -name 'README.md' \) \
  -exec sed -i.bak 's|guides/feedback\.md|../shared/feedback.md|g' {} \;
find rulesbook/codegen-rust -name '*.bak' -delete
```
Expected: silent success.

- [ ] **Step 6: Verify no stale references remain**

Run: `grep -rn 'guides/feedback\.md' rulesbook/codegen-rust/ 2>/dev/null || true`
Expected: NO output. If any matches appear, hand-edit them.

- [ ] **Step 7: Verify the new reference path resolves**

Run: `ls rulesbook/codegen-rust/../shared/feedback.md`
Expected: file listed. (`..` from `codegen-rust/` goes back to `rulesbook/`, then `shared/feedback.md`.)

- [ ] **Step 8: Commit**

Run:
```bash
git add rulesbook/shared/feedback.md rulesbook/codegen-rust/
git commit -m "refactor(rulesbook): move feedback.md to shared/, tag entries [lang:rust]

Cross-cutting feedback now lives in rulesbook/shared/feedback.md.
Existing entries are implicitly Rust-tagged via a preamble; future
entries from any language pack must include their lang tag."
```
Expected: commit succeeds.

---

### Task 6: Move `learnings.md` to `shared/`

**Files:**
- Rename: `rulesbook/codegen-rust/guides/learnings/learnings.md` → `rulesbook/shared/learnings.md`
- Delete: `rulesbook/codegen-rust/guides/learnings/` (empty directory after move)
- Modify: `rulesbook/codegen-rust/.gracerules*` (path refs)
- Modify: `rulesbook/codegen-rust/README.md` (path refs)

- [ ] **Step 1: Verify the source file exists**

Run: `ls rulesbook/codegen-rust/guides/learnings/learnings.md`
Expected: file listed.

- [ ] **Step 2: Move the file**

Run: `git mv rulesbook/codegen-rust/guides/learnings/learnings.md rulesbook/shared/learnings.md`
Expected: silent success.

- [ ] **Step 3: Add the same language-tag preamble**

Add at the top of `rulesbook/shared/learnings.md`:

```markdown
> **Language tagging convention**
>
> All entries below this preamble were authored when Grace only generated
> Rust connectors. They are implicitly tagged `[lang:rust]`. New entries
> from any language pack MUST start with one of `[lang:rust]`,
> `[lang:python]`, or `[lang:*]`.
```

- [ ] **Step 4: Remove the now-empty `learnings/` directory**

Run:
```bash
rmdir rulesbook/codegen-rust/guides/learnings
```
Expected: silent success. If `rmdir` fails with "directory not empty", run `ls rulesbook/codegen-rust/guides/learnings/` to see what's still there and decide what to do (move or commit separately).

- [ ] **Step 5: Find every reference to the old path**

Run: `grep -rn 'guides/learnings/learnings\.md\|guides/learnings\.md' rulesbook/codegen-rust/ 2>/dev/null || true`
Expected: a list of matches. Note them.

- [ ] **Step 6: Bulk-rewrite the references**

Run:
```bash
find rulesbook/codegen-rust -type f \( -name '.gracerules*' -o -name 'README.md' \) \
  -exec sed -i.bak 's|guides/learnings/learnings\.md|../shared/learnings.md|g' {} \;
find rulesbook/codegen-rust -name '*.bak' -delete
```
Expected: silent success.

- [ ] **Step 7: Verify clean**

Run: `grep -rn 'guides/learnings' rulesbook/codegen-rust/ 2>/dev/null || true`
Expected: NO output.

- [ ] **Step 8: Commit**

Run:
```bash
git add rulesbook/shared/learnings.md rulesbook/codegen-rust/
git commit -m "refactor(rulesbook): move learnings.md to shared/

Removed the empty guides/learnings/ directory. References updated."
```
Expected: commit succeeds.

---

### Task 7: Move tech-spec template to `shared/`

**Files:**
- Rename: `rulesbook/codegen-rust/connector_integration/template/tech_spec.md` → `rulesbook/shared/tech_spec_template.md`
- Modify: any file referencing the old path

- [ ] **Step 1: Verify the source file exists**

Run: `ls rulesbook/codegen-rust/connector_integration/template/tech_spec.md`
Expected: file listed.

- [ ] **Step 2: Move the file with rename**

Run: `git mv rulesbook/codegen-rust/connector_integration/template/tech_spec.md rulesbook/shared/tech_spec_template.md`
Expected: silent success.

- [ ] **Step 3: Find references to the old path**

Run:
```bash
grep -rn 'connector_integration/template/tech_spec\.md\|template/tech_spec\.md' \
  rulesbook/ workflow/ README.md setup.md CLAUDE.md src/ 2>/dev/null || true
```
Expected: a list of matches (likely in `.gracerules*` and possibly `src/ai/prompts/`).

- [ ] **Step 4: Update references**

For each match identified in Step 3, update by hand or via sed. The replacement path differs by source file location:
- From `rulesbook/codegen-rust/.gracerules*` → use `../shared/tech_spec_template.md`
- From `rulesbook/codegen-rust/README.md` → use `../shared/tech_spec_template.md`
- From `workflow/*.md` → use `grace/rulesbook/shared/tech_spec_template.md`
- From `src/` → use the repo-root-relative path `rulesbook/shared/tech_spec_template.md`

Generic sed (use this only if all matches are in `.gracerules*`; otherwise do per-file):
```bash
find rulesbook/codegen-rust -type f \( -name '.gracerules*' -o -name 'README.md' \) \
  -exec sed -i.bak 's|connector_integration/template/tech_spec\.md|../shared/tech_spec_template.md|g' {} \;
find rulesbook/codegen-rust -name '*.bak' -delete
```

- [ ] **Step 5: Verify clean**

Run: `grep -rn 'connector_integration/template/tech_spec\.md\|template/tech_spec\.md' rulesbook/ workflow/ README.md setup.md CLAUDE.md src/ 2>/dev/null || true`
Expected: NO output.

- [ ] **Step 6: Commit**

Run:
```bash
git add rulesbook/shared/tech_spec_template.md rulesbook/codegen-rust/
git commit -m "refactor(rulesbook): move tech_spec.md template to shared/

The tech-spec template is language-neutral by construction (it describes
the external PSP API, not the connector code). Now lives in shared/."
```
Expected: commit succeeds.

---

### Task 8: Author `shared/flows.md` (extract flow definitions + DAG)

**Files:**
- Create: `rulesbook/shared/flows.md`
- Modify: `rulesbook/codegen-rust/README.md` (replace duplicated section with pointer)

- [ ] **Step 1: Read the source content**

Open `rulesbook/codegen-rust/README.md` and locate two sections:
- "📋 Comprehensive Flow Support" (the section with Core Payment Flows + Advanced Flows tables)
- The prerequisite dependency information in those tables

These two sections together are the language-neutral flow knowledge.

- [ ] **Step 2: Write `rulesbook/shared/flows.md`**

Create the file with this exact content:

```markdown
# Flow definitions and prerequisite DAG

Authoritative source of truth for every payment flow Grace's rulesbook
supports, including the prerequisite dependency graph. Language-neutral —
all packs reference this file rather than duplicating the list.

## Core Payment Flows (6 essential flows)

| Flow | Pattern File (per lang pack) | Prerequisites | Description |
|------|------------------------------|---------------|-------------|
| **Authorize** | `pattern_authorize.md` | None | Initial payment authorization |
| **PSync** | `pattern_psync.md` | Authorize | Payment status synchronization |
| **Capture** | `pattern_capture.md` | Authorize | Capture authorized payments |
| **Void** | `pattern_void.md` | Authorize | Cancel authorized payments |
| **Refund** | `pattern_refund.md` | Capture (or Authorize for auth-and-capture-in-one connectors) | Full and partial refunds |
| **RSync** | `pattern_rsync.md` | Refund | Refund status synchronization |

## Advanced Flows

| Flow | Pattern File | Prerequisites | Description |
|------|--------------|---------------|-------------|
| **SetupMandate** | `pattern_setup_mandate.md` | Authorize | Set up recurring payments (UPI Autopay / eMandate) |
| **RepeatPayment** | `pattern_repeat_payment_flow.md` | SetupMandate | Process recurring payments |
| **IncomingWebhook** | `pattern_IncomingWebhook_flow.md` | PSync | Real-time event handling (UPI status, dispute updates, etc.) |
| **CreateOrder** | `pattern_createorder.md` | — | Multi-step payment initiation |
| **SessionToken** | `pattern_session_token.md` | — | Secure session management |
| **PaymentMethodToken** | `pattern_payment_method_token.md` | — | Tokenize payment methods |
| **DefendDispute** | `pattern_defend_dispute.md` | — | Defend chargebacks |
| **AcceptDispute** | `pattern_accept_dispute.md` | — | Accept chargebacks |
| **DSync** | `pattern_dsync.md` | — | Dispute status synchronization |
| **MandateRevoke** | `pattern_mandate_revoke.md` | SetupMandate | Cancel stored mandates |
| **IncrementalAuthorization** | `pattern_IncrementalAuthorization_flow.md` | Authorize | Incremental auth flow |
| **VoidPC** | `pattern_void_pc.md` | Capture | Void post-capture |
| **CreateAccessToken** | `pattern_CreateAccessToken_flow.md` | — | OAuth-style token acquisition |
| **SubmitEvidence** | `pattern_submit_evidence.md` | DefendDispute | Submit dispute evidence |

## Prerequisite DAG (textual form)

```
Authorize ──┬─► PSync
            ├─► Capture ──► Refund ──► RSync
            │              │
            │              └─► VoidPC
            ├─► Void
            ├─► SetupMandate ──┬─► RepeatPayment
            │                  └─► MandateRevoke
            └─► IncrementalAuthorization

PSync ──► IncomingWebhook

DefendDispute ──► SubmitEvidence
DefendDispute / AcceptDispute ──► DSync
```

## Validity rules

When a new pattern is added to any language pack:

1. Its prerequisites must form a valid DAG (no cycles) against the table above.
2. Its prerequisites must be a subset of what's listed above for that flow.
3. New flows not listed here must be added to this file first, then implemented in each language pack that supports them.

The [rulesbook-pattern-auditor](../../.claude/agents/rulesbook-pattern-auditor.md) agent enforces these rules.
```

- [ ] **Step 3: Replace the duplicated content in `codegen-rust/README.md`**

In `rulesbook/codegen-rust/README.md`, locate the "## 📋 Comprehensive Flow Support" section. Replace it with:

```markdown
## 📋 Comprehensive Flow Support

The authoritative list of flows and their prerequisite DAG lives in
[`../shared/flows.md`](../shared/flows.md). It applies to every language
pack equally.

Each entry in `flows.md` references a `pattern_<flow>.md` file located in
this pack's `guides/patterns/` directory.
```

(Preserve the rest of `codegen-rust/README.md` exactly as-is. Only the "Comprehensive Flow Support" section moves.)

- [ ] **Step 4: Verify the file referenced from the README resolves**

Run: `ls rulesbook/codegen-rust/../shared/flows.md`
Expected: file listed.

- [ ] **Step 5: Commit**

Run:
```bash
git add rulesbook/shared/flows.md rulesbook/codegen-rust/README.md
git commit -m "feat(rulesbook): extract flow definitions to shared/flows.md

Flow names and prerequisite DAG are language-neutral. The codegen-rust
README now points at the shared file instead of duplicating it."
```
Expected: commit succeeds.

---

### Task 9: Author `shared/payment_methods.md` (extract PM categories)

**Files:**
- Create: `rulesbook/shared/payment_methods.md`
- Modify: `rulesbook/codegen-rust/README.md` (replace section with pointer)

- [ ] **Step 1: Locate the source content**

Open `rulesbook/codegen-rust/README.md` and find the "Payment Method Patterns (for Authorize Flow)" section and its companion list of supported categories.

- [ ] **Step 2: Write `rulesbook/shared/payment_methods.md`**

Create the file with this exact content:

```markdown
# Payment-method categories and types

Authoritative source of truth for the payment-method taxonomy. Each
language pack defines language-specific pattern files under
`guides/patterns/authorize/<category>/` matching the categories below.

## Categories

| Category | Code (Category:Type) | Per-pack pattern dir | Supported Flows |
|----------|----------------------|----------------------|-----------------|
| **Card** | `Card:Credit`, `Card:Debit` | `authorize/card/` | All flows |
| **Wallet** | `Wallet:Apple Pay`, `Wallet:Google Pay`, `Wallet:PayPal`, etc. | `authorize/wallet/` | Authorize, Refund |
| **Bank Transfer** | `BankTransfer:SEPA`, `BankTransfer:ACH`, etc. | `authorize/bank_transfer/` | Authorize, Refund |
| **Bank Debit** | `BankDebit:SEPA`, `BankDebit:ACH`, etc. | `authorize/bank_debit/` | Authorize, Refund |
| **Bank Redirect** | `BankRedirect:Sofort`, `BankRedirect:iDEAL`, etc. | `authorize/bank_redirect/` | Authorize |
| **UPI** | `UPI:Collect`, `UPI:Intent` | `authorize/upi/` | Authorize, Refund |
| **BNPL** | `BNPL:Klarna`, `BNPL:Afterpay`, etc. | `authorize/bnpl/` | Authorize, Refund |
| **Crypto** | `Crypto:Bitcoin`, etc. | `authorize/crypto/` | Authorize |
| **Gift Card** | `GiftCard:Generic` | `authorize/gift_card/` | Authorize |
| **Mobile Payment** | `MobilePayment:<network>` | `authorize/mobile_payment/` | Authorize, Refund |
| **Reward** | `Reward:<program>` | `authorize/reward/` | Authorize |

## Command syntax

When adding payment methods to a connector, the command form is:

```
add <Category>:<Type1>,<Type2> [and <Category2>:<Type3>] to <Connector> using grace/rulesbook/codegen-<lang>/.gracerules_add_payment_method
```

Examples:
- `add Wallet:Apple Pay,Google Pay to Stripe using grace/rulesbook/codegen-rust/.gracerules_add_payment_method`
- `add UPI:Collect,Intent to Razorpay using grace/rulesbook/codegen-python/.gracerules_add_payment_method`

## Validity rules

When adding a payment method to any language pack:

1. The category must exist in the table above.
2. The pattern file path matches `guides/patterns/authorize/<category>/pattern_authorize_<type_or_category>.md`.
3. The Authorize flow must already exist for the target connector (prerequisite).

The [rulesbook-pattern-auditor](../../.claude/agents/rulesbook-pattern-auditor.md) agent enforces these rules.
```

- [ ] **Step 3: Replace the duplicated content in `codegen-rust/README.md`**

Locate the "Payment Method Patterns (for Authorize Flow)" table in `rulesbook/codegen-rust/README.md`. Replace it with:

```markdown
### Payment Method Patterns (for Authorize Flow)

The authoritative list of payment-method categories and types lives in
[`../shared/payment_methods.md`](../shared/payment_methods.md). Pattern
files for this language pack live under `guides/patterns/authorize/<category>/`.
```

- [ ] **Step 4: Commit**

Run:
```bash
git add rulesbook/shared/payment_methods.md rulesbook/codegen-rust/README.md
git commit -m "feat(rulesbook): extract payment-method taxonomy to shared/

Categories and command syntax are language-neutral. Codegen-rust README
references the shared file."
```
Expected: commit succeeds.

---

### Task 10: Author `shared/quality_rubric.md` (extract formula + cross-cutting checks)

**Files:**
- Create: `rulesbook/shared/quality_rubric.md`
- Modify: `rulesbook/codegen-rust/README.md` (replace section)
- Modify: `rulesbook/codegen-rust/.gracerules` (update Quality Review section pointer)
- Modify: `rulesbook/codegen-rust/.gracerules_add_flow` (same)
- Modify: `rulesbook/codegen-rust/.gracerules_add_payment_method` (same)

- [ ] **Step 1: Locate the source content**

In `rulesbook/codegen-rust/README.md`, find the "🛡️ Quality Enforcement System" section. It contains the scoring formula, thresholds, and a list of what gets reviewed.

- [ ] **Step 2: Write `rulesbook/shared/quality_rubric.md`**

Create the file with this exact content:

```markdown
# Quality Guardian — scoring formula and cross-cutting checks

Authoritative source of truth for the Quality Guardian's scoring formula
and the cross-cutting (language-neutral) checks it applies to every
generated connector. Language-specific checks live in each pack's
`guides/quality/` directory.

## Scoring formula

```
Quality Score = 100 - (Critical Issues × 20) - (Warnings × 5) - (Suggestions × 1)
```

## Thresholds

| Range | Tier | Action |
|-------|------|--------|
| 95-100 | Excellent ✨ | Auto-approve, document success patterns in `feedback.md` |
| 80-94  | Good ✅ | Approve with minor notes |
| 60-79  | Fair ⚠️ | **Approve** with warnings, recommend fixes (this is the gate) |
| 40-59  | Poor ❌ | Block until critical issues fixed |
| 0-39   | Critical 🚨 | Block immediately, requires rework |

**Gate:** A connector must score ≥ 60 to proceed past Quality Guardian.

## Cross-cutting checks (apply to ALL languages, same semantics, same severity)

| Check | Severity |
|-------|----------|
| Idempotency key sent on Authorize/Capture/Refund | Critical |
| Every documented PSP status mapped to a UCS status (no silent fallthrough to Failure) | Critical |
| No hardcoded secrets (auth only from Auth class/struct) | Critical |
| Coverage: every flow requested has a real implementation (no `todo!()` / `NotImplementedError`) | Critical |
| Webhook signature verification present (if IncomingWebhook implemented) | Critical |
| Webhook dedup present (if IncomingWebhook implemented) | Critical |
| Currency/amount handling uses minor-unit-aware helpers; no float arithmetic on money | Critical |
| PCI/PII masking applied to any log line touching PAN/CVV/VPA | Critical |
| Errors include connector-provided message + code | Warning |
| No fields hardcoded to None/null | Warning |
| No code duplication across flows | Suggestion |

## Language-specific checks

Each language pack adds its own checks on top of the cross-cutting list:
- Rust-specific: see [`../codegen-rust/guides/quality/`](../codegen-rust/guides/quality/)
- Python-specific: see [`../codegen-python/guides/quality/`](../codegen-python/guides/quality/) (when present)

## How Quality Guardian uses this file

Every `.gracerules*` ends with a "Quality Review" section that:
1. References this file for the formula, thresholds, and cross-cutting checks.
2. References the language pack's local `guides/quality/` for language-specific checks.
3. Sums the checks, applies the formula, and gates at score ≥ 60.

## Feedback database

Findings during Quality Review are logged to [`feedback.md`](feedback.md)
with appropriate language tags.
```

- [ ] **Step 3: Replace the duplicated content in `codegen-rust/README.md`**

Locate the "🛡️ Quality Enforcement System" section in `rulesbook/codegen-rust/README.md`. Replace its entire content (formula, thresholds, scoring, "What Gets Reviewed", "Feedback Database" subsection) with:

```markdown
## 🛡️ Quality Enforcement System

The scoring formula, thresholds, and cross-cutting (language-neutral)
quality checks live in [`../shared/quality_rubric.md`](../shared/quality_rubric.md).

This pack's Rust-specific quality checks live in
[`guides/quality/`](guides/quality/).
```

- [ ] **Step 4: Update Quality Review references inside each `.gracerules*` file**

In each of these files, find the "Quality Review" section and update any reference that mentions the in-README quality content. Replace with a reference to `../shared/quality_rubric.md`.

Files:
- `rulesbook/codegen-rust/.gracerules`
- `rulesbook/codegen-rust/.gracerules_add_flow`
- `rulesbook/codegen-rust/.gracerules_add_payment_method`

Search per file:
```bash
grep -n -i 'quality.*review\|quality.*score\|quality.*formula\|quality.*threshold' rulesbook/codegen-rust/.gracerules | head -20
```

Identify each spot referring to the scoring/formula/thresholds content. Either:
- (a) Add a line near the Quality Review section: `See \`../shared/quality_rubric.md\` for the scoring formula and cross-cutting checks.`
- (b) Replace any literal duplication of the formula/thresholds with a reference to that file.

The `.gracerules*` files are AI-agent prompts; preserve their existing structure and language. Only add or replace the formula-reference snippets.

- [ ] **Step 5: Verify the new file resolves from each reference point**

Run:
```bash
ls rulesbook/codegen-rust/../shared/quality_rubric.md
ls rulesbook/codegen-rust/../shared/feedback.md
ls rulesbook/codegen-rust/../shared/learnings.md
ls rulesbook/codegen-rust/../shared/flows.md
ls rulesbook/codegen-rust/../shared/payment_methods.md
ls rulesbook/codegen-rust/../shared/tech_spec_template.md
```
Expected: all six files listed without error.

- [ ] **Step 6: Commit**

Run:
```bash
git add rulesbook/shared/quality_rubric.md rulesbook/codegen-rust/
git commit -m "feat(rulesbook): extract Quality Guardian formula to shared/

Scoring formula, thresholds, and cross-cutting checks now live in
shared/quality_rubric.md. Each .gracerules* and the codegen-rust
README reference the shared file."
```
Expected: commit succeeds.

---

### Task 11: Verify all `.gracerules*` internal paths resolve

**Files:**
- Read-only verification across `rulesbook/codegen-rust/.gracerules*`.

- [ ] **Step 1: List every relative path reference inside the three `.gracerules*` files**

Run:
```bash
grep -hn 'guides/\|references/\|connector_integration/\|shared/\|../shared/' \
  rulesbook/codegen-rust/.gracerules \
  rulesbook/codegen-rust/.gracerules_add_flow \
  rulesbook/codegen-rust/.gracerules_add_payment_method \
  | grep -v '^[0-9]*:[[:space:]]*#' \
  | head -60
```
Expected: a list of relative paths used inside the files. Each one should now point at a place that exists.

- [ ] **Step 2: For each unique relative path in the output, verify it resolves**

For each unique path found (sorting and dedup helps):
```bash
grep -hoE '(\.\./)?[a-zA-Z_/-]+\.md' rulesbook/codegen-rust/.gracerules* \
  | sort -u
```
Expected: a list of `.md` files referenced. Spot-check each via `ls rulesbook/codegen-rust/<path>` (or `ls rulesbook/codegen-rust/../shared/<file>` for `../shared/...` refs).

- [ ] **Step 3: Hand-fix any broken reference**

For any path that does NOT resolve:
- If it's a `guides/feedback.md` / `guides/learnings/learnings.md` / `connector_integration/template/tech_spec.md` left over from earlier tasks, replace with the corresponding `../shared/<file>` path.
- If it's a different broken path, investigate — it may be a pre-existing issue unrelated to this plan. If so, document it and skip; do not silently fix unrelated issues in this plan.

- [ ] **Step 4: Commit any fixes**

Run:
```bash
git status --short
# Review changes
git diff rulesbook/codegen-rust/
git add rulesbook/codegen-rust/
git commit -m "fix(rulesbook): repair stale path references in .gracerules*

Found during Task 11 audit." \
  || echo "Nothing to commit (no stale refs found)"
```
Expected: either a commit or "Nothing to commit" — either is acceptable.

---

### Task 12: Update `add_connector.sh` if it references old paths

**Files:**
- Modify: `rulesbook/codegen-rust/add_connector.sh`

- [ ] **Step 1: Inspect the script for path references**

Run: `grep -n 'rulesbook/\|codegen/\|guides/\|connector_integration/' rulesbook/codegen-rust/add_connector.sh`
Expected: a list of lines that reference paths.

- [ ] **Step 2: Identify any that point at the old (pre-rename) layout**

For each match, decide:
- If it points at `rulesbook/codegen/` (no `-rust`), it needs to become `rulesbook/codegen-rust/`.
- If it points at `guides/feedback.md` or similar moved files, it needs to point at `../shared/<file>` (since the script lives at `rulesbook/codegen-rust/`).

- [ ] **Step 3: Apply the fixes (hand-edit if more than one)**

If a single safe sed works:
```bash
sed -i.bak \
  -e 's|rulesbook/codegen/|rulesbook/codegen-rust/|g' \
  -e 's|guides/feedback\.md|../shared/feedback.md|g' \
  -e 's|guides/learnings/learnings\.md|../shared/learnings.md|g' \
  -e 's|connector_integration/template/tech_spec\.md|../shared/tech_spec_template.md|g' \
  rulesbook/codegen-rust/add_connector.sh
rm -f rulesbook/codegen-rust/add_connector.sh.bak
```

- [ ] **Step 4: Run a syntax sanity check**

Run: `bash -n rulesbook/codegen-rust/add_connector.sh && echo "syntax OK"`
Expected: `syntax OK`. If errors, hand-fix.

- [ ] **Step 5: Commit (if anything changed)**

Run:
```bash
git diff rulesbook/codegen-rust/add_connector.sh
git add rulesbook/codegen-rust/add_connector.sh
git commit -m "fix(rulesbook): update add_connector.sh path references" \
  || echo "Nothing to commit"
```
Expected: commit succeeds or "Nothing to commit".

---

### Task 13: Update `CLAUDE.md` and top-level docs for the new structure

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `setup.md`

These were already updated for the bare path rename in Task 3 (`codegen/` → `codegen-rust/`). This task adds explicit documentation of the new `shared/` directory.

- [ ] **Step 1: Locate the "Repository layout" or "rulesbook" section in `CLAUDE.md`**

Open `CLAUDE.md` and find the existing repo layout block (it shows the `rulesbook/` tree).

- [ ] **Step 2: Update the layout to reflect `shared/` + `codegen-rust/`**

Find the existing `rulesbook/codegen/` block. Replace it with:

```
├── rulesbook/
│   ├── shared/                       # Language-neutral content
│   │   ├── flows.md                  # Authoritative flow list + prerequisite DAG
│   │   ├── payment_methods.md        # Payment-method categories + types
│   │   ├── quality_rubric.md         # Scoring formula + cross-cutting checks
│   │   ├── feedback.md               # Quality-review feedback (tagged by lang)
│   │   ├── learnings.md              # Implementation lessons (tagged by lang)
│   │   └── tech_spec_template.md     # Tech-spec template (lang-neutral)
│   ├── codegen-rust/                 # Rust language pack (rulebook that AI agents read)
│   │   ├── .gracerules               # NEW connector from scratch (6 core flows)
│   │   ├── .gracerules_add_flow      # Add one flow to existing connector
│   │   ├── .gracerules_add_payment_method  # Add payment methods
│   │   ├── README.md                 # GRACE-UCS user guide
│   │   ├── guides/
│   │   │   ├── patterns/             # Rust pattern templates
│   │   │   ├── types/types.md        # UCS Rust type system
│   │   │   └── quality/              # Rust-only quality checks
│   │   └── connector_integration/
│   └── references/                   # Per-connector tech specs (gitignored)
```

(Replace the previous layout block exactly. Preserve everything else in `CLAUDE.md`.)

- [ ] **Step 3: Add a one-paragraph explanation near the layout**

Right below the layout block, ensure there's a paragraph explaining:

```markdown
The `rulesbook/` directory has three top-level children:

- `shared/` — language-neutral content used by every codegen pack (flow
  definitions, quality rubric, feedback/learnings)
- `codegen-<lang>/` — one directory per supported target language; each
  holds the `.gracerules*` triad, pattern templates, and language-specific
  type and quality references
- `references/` — per-connector tech specs generated by `grace techspec`
  (gitignored)
```

If a similar paragraph already exists from earlier, leave it; otherwise add this.

- [ ] **Step 4: Apply equivalent updates to `README.md`**

Locate any layout or "What's in this repo" section in `README.md`. If it mentions `rulesbook/codegen/`, update it to describe the `shared/` + `codegen-rust/` split. If `README.md` has no such section, skip — only the path strings updated in Task 3 are required there.

- [ ] **Step 5: Apply equivalent updates to `setup.md`**

Same as `README.md` — only update if a layout description is present. Path strings were already fixed in Task 3.

- [ ] **Step 6: Commit**

Run:
```bash
git add CLAUDE.md README.md setup.md
git commit -m "docs: describe new rulesbook/shared + codegen-rust layout

CLAUDE.md (and README/setup where applicable) now show the language-
neutral shared/ directory alongside language-specific codegen-rust/."
```
Expected: commit succeeds.

---

### Task 14: Acceptance gate — verify no stale references remain

**Files:**
- Read-only audit across the repo.

- [ ] **Step 1: Audit all external references for the old codegen path**

Run:
```bash
grep -rn 'rulesbook/codegen[^-]' \
  workflow/ README.md setup.md CLAUDE.md *.sh rulesbook/ docs/ src/ .claude/ \
  2>/dev/null | grep -v '\.bak:' || true
```
Expected: NO output. If anything appears, it's a missed reference — hand-fix and commit before proceeding.

- [ ] **Step 2: Audit all references for the old `guides/feedback.md` / `guides/learnings/learnings.md` / `connector_integration/template/tech_spec.md`**

Run:
```bash
grep -rn 'guides/feedback\.md\|guides/learnings/learnings\.md\|connector_integration/template/tech_spec\.md' \
  workflow/ README.md setup.md CLAUDE.md *.sh rulesbook/ docs/ src/ .claude/ \
  2>/dev/null || true
```
Expected: NO output. The exception is `rulesbook/shared/` itself or the spec/plan docs in `docs/superpowers/` which may legitimately mention these for historical reasons — exclude those manually.

- [ ] **Step 3: Verify the new structural shape**

Run:
```bash
ls rulesbook/
ls rulesbook/shared/
ls rulesbook/codegen-rust/
```
Expected:
- `rulesbook/` lists at least `shared/`, `codegen-rust/`, `references/` (no `codegen/` without suffix)
- `rulesbook/shared/` lists `README.md`, `feedback.md`, `flows.md`, `learnings.md`, `payment_methods.md`, `quality_rubric.md`, `tech_spec_template.md`
- `rulesbook/codegen-rust/` lists `.gracerules`, `.gracerules_add_flow`, `.gracerules_add_payment_method`, `README.md`, `add_connector.sh`, `guides/`, plus any other files that were originally there

- [ ] **Step 4: Compare baseline vs current file count**

Run:
```bash
find rulesbook/codegen-rust rulesbook/shared -type f | sort | wc -l
wc -l /tmp/grace-files-before.txt
```
Expected: equal counts (or `codegen-rust + shared` total = `codegen` baseline + 4 new files (`shared/README.md` + 3 authored shared docs: `flows.md`, `payment_methods.md`, `quality_rubric.md`)). Do the arithmetic:

- Baseline file count = X (from `/tmp/grace-files-before.txt`)
- Current count should be = X + 4 (the new shared/ docs minus zero removed)

If they don't match, something was lost. Track down the missing file via `git log --diff-filter=D --name-only` since the start of this plan's commits.

- [ ] **Step 5: Read each `.gracerules*` quickly and confirm it scans clean**

Run:
```bash
wc -l rulesbook/codegen-rust/.gracerules*
head -50 rulesbook/codegen-rust/.gracerules
head -50 rulesbook/codegen-rust/.gracerules_add_flow
head -50 rulesbook/codegen-rust/.gracerules_add_payment_method
```
Expected: file sizes match the baseline (or are slightly different from added "see ../shared/..." references), and the opening of each file reads coherently — no obvious paste damage from the sed operations.

- [ ] **Step 6: Document the acceptance result**

In the plan's worktree root, run:
```bash
git log --oneline | head -20
```
Expected: a clean linear sequence of commits from this plan, all on the current branch. Capture this list; it's the "what Plan A did" summary for the PR description.

- [ ] **Step 7: (Optional) Full end-to-end gate**

The spec's full acceptance gate is "generate a sample Rust connector before AND after Phase 1, then `diff -r` the output." This is a heavyweight test requiring `connector-service/` to be present and a sample tech spec on hand.

If running this end-to-end test:

1. Before this plan started, you should have generated a connector with the pre-rename rulesbook. If you didn't, this gate is moot for this run — the structural audit above is sufficient.
2. Run `grace techspec <sample> -f <docs-dir>` (with whatever target-lang default was, since Plan B hasn't shipped). Note that Plan A has NOT changed any Python code yet — `grace techspec` behaves exactly as before.
3. Compare the tech spec output to a saved baseline. They should be byte-identical.
4. Optionally invoke the AI agent on `connector-service/` with `.gracerules` and confirm the generated Rust connector matches a pre-plan baseline.

If you skip this gate, document the skip:

```
Plan A acceptance gate: structural audit PASSED (Steps 1-6).
Full end-to-end gate (generate connector before/after) SKIPPED — relied
on structural audit because no pre-plan connector baseline was captured.
```

This documentation goes in the Plan A completion summary (final response).

---

## Plan A acceptance summary

The plan is complete when every box above is checked AND the Step 1/Step 2 audits in Task 14 produce no output. The structural changes — rename, content extraction, reference rewrites — are atomic, individually committed, and individually revertable.

After Plan A lands:
- Existing Rust workflows continue to work (no Python code changed)
- The shape is ready for Plan B (CLI `--target-lang` flag) and Plan D (Python pattern pack)
- Anyone who hardcoded `grace/rulesbook/codegen/` paths externally will see those break — confirmed acceptable per design spec Section 5.1 ("no external consumers atm, breaking changes are fine")

---

## Self-review notes (for the plan-writer's records)

Spec coverage:
- ✓ Section 4.1 layout — Tasks 2, 4, 5, 6, 7, 8, 9, 10
- ✓ Section 4.2 shared/ contents — Tasks 5, 6, 7, 8, 9, 10
- ✓ Section 10 Phase 1 task list — Tasks 1-14
- ✓ Phase 1 acceptance gate (`diff -r`) — Task 14 Step 7 (optional; structural audit is the default)

Placeholders: none — every step has concrete commands or content.

Type consistency: N/A for Plan A (no code types). All file paths used are consistent across tasks.

Out-of-scope items deferred to other plans:
- CLI changes (`--target-lang` flag) → Plan B
- Workflow agent `{LANG}` parameter → Plan B
- Python language pack → Plan D
- `lens` bootstrap → Plan C
- Razorpay end-to-end validation → Plan E
