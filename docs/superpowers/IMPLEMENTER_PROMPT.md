# Implementer Prompt: Grace (codegen)

You are an implementing agent. Your job is to take the locked specs and the implementation plan in this repo and extend **Grace** to emit Python payment connectors that target Orbit's `lens`.

You are **not** a designer. The specs are locked at v0.4. Don't revisit design decisions, don't widen scope, don't add features. If you find yourself wanting to, stop and ask the user.

---

## What Orbit is (the end product)

**Orbit** is Symplora's unified financial-operations product. Consumer apps (Symplora ATS, Hikara, future products) talk to Orbit whenever money needs to move. v1 ships **hosted-checkout payments** integrated to Cashfree, with the architecture in place to add Razorpay, Stripe, and others later.

There are three sub-projects under the Orbit umbrella:

```
        Consumer apps (Symplora ATS, Hikara, …)
                          │
                          ▼ HTTP
        ┌──────────────────────────────────────────┐
        │ Orbit (product)                          │
        │   HTTP API · transaction ledger ·         │
        │   state machines · webhook receiver       │
        └──────────────────┬───────────────────────┘
                           │ imports
                           ▼
        ┌──────────────────────────────────────────┐
        │ Lens                                     │
        │   stateless Python library ·             │
        │   PaymentsFacade · Connector ABC ·       │
        │   per-PSP Connector implementations      │
        └──────────────────┬───────────────────────┘
                           │ httpx
                           ▼
                  PSP APIs (Cashfree, Razorpay, …)

   BUILD-TIME ONLY:
   ┌──────────────────────────────────────────────┐
   │ Grace (codegen tool)     ← YOU               │
   │   reads a PSP's API docs → generates a       │
   │   Python connector that conforms to          │
   │   Lens's `Connector` ABC                     │
   └──────────────────────────────────────────────┘
```

Two first-class entities flow through the runtime system:
- **Order** — the merchant's intent. Created by Orbit; mirrored to the PSP via `create_order`.
- **PaymentAttempt** — one specific attempt by the payer (one Order has 0..N attempts).

Plus **Refund**, hanging off the successful PaymentAttempt of an Order.

v1 is **hosted-checkout only** — the PSP renders its own page; the merchant never holds raw card / UPI / wallet data. Direct-API / server-to-server is parked in `FUTURE_S2S_INTERFACE.md`.

---

## How your sub-project fits in

Grace is **build-time only** — it never runs in production. A developer (or CI) runs:

```
$ grace generate cashfree --from https://docs.cashfree.com/openapi.yaml
```

Grace reads the PSP's API docs + its rulebook, invokes **Claude Code** to write Python code, runs the generated package through quality gates, and (if all gates pass) writes the result to `lens/connectors/<psp>/` in the Lens repo. The generated code is then **committed to git** and reviewed like any other code.

You depend on Lens's `Connector` ABC: Grace must emit Python that subclasses `lens.Connector` with the correct method signatures, status mapping, error handling, and PII discipline.

Lens's **Step 3 (hand-written Cashfree)** is your **Step 5's reference**: you regenerate Cashfree and diff against the hand-written version. If they don't match in shape, your rulebook needs sharpening.

Your sub-project owns **constitution §9 Steps 4 + 5** of the global dependency order.

---

## What you're building, concretely

A CLI tool with a simple, locked interface:

```
$ grace generate <psp> --from <source> [--output <dir>]
$ grace regenerate <psp>
$ grace doctor
$ grace --version
```

The internal pipeline is **three steps**:

1. **Gather context** — read the rulebook + the target PSP's API docs.
2. **Invoke Claude Code** — spawn the local `claude` CLI in headless mode, hand it the context bundle.
3. **Run quality gates** — `mypy --strict` + `pytest --cov` + the 6-dimension rubric (≥ 60 / 100 to pass).

Locked design choices:

- **One AI backend**: Claude Code via the local CLI session. No `AIProvider` ABC, no OpenAI, no Anthropic SDK, no fallback chain. If you find yourself adding pluggability, stop and re-read constitution OQ-7.
- **The `python-support` branch** lands as v1 acceptance: it merges back into `main` and is then deleted.
- **Generated files carry a marker** (constitution §4). Hand-edits to those files are forbidden.
- **`status_map.py`** is a required emitted file: it maps PSP-specific status terms to `(PaymentAttemptStatus, PaymentFailureCode)`.

Existing Grace fork code lives at `src/grace/` and `rulesbook/codegen/`. Your work is part **rulebook restructure** (replace Rust patterns with Python patterns), part **pipeline implementation** (`ClaudeCodeRunner`, gates, rubric), and part **end-to-end validation** (regenerate Cashfree, generate Razorpay from scratch).

---

## Working directory

`/Users/sarthak/PycharmProjects/references/grace/` — the team's fork of `juspay-prism/grace/` at `github.com/HR-intention/grace`.

Branch the work off `main`. The `python-support` branch already exists; the plan tells you whether to extend it or start fresh.

---

## Required reading (in this order)

1. **`docs/superpowers/specs/ORBIT_CONSTITUTION.md`** — the system constitution. Read in full. Pay attention to §4 (marker format), §5 (`Connector` ABC), §9 (dependency order), §10 OQ-3 (upstream sync policy).
2. **`docs/superpowers/specs/SUBPROJECT_GRACE_CODEGEN.md`** — your sub-project's locked spec. Read in full.
3. **`docs/superpowers/specs/SUBPROJECT_LENS.md`** — what you generate **against**. Read §2 (glossary), §4 (interfaces), §5.1 (file layout), §5.2 (status mapping). Skim the rest.
4. **`docs/superpowers/plans/PLAN_GRACE_CODEGEN.md`** — your implementation plan. Read in full; this is what you **execute**.
5. **Glance only**:
   - `docs/superpowers/specs/SUBPROJECT_ORBIT_PRODUCT.md` — to understand who eventually consumes the connectors you generate.
   - `docs/superpowers/specs/FUTURE_S2S_INTERFACE.md` — what's deliberately NOT in v1 (so you don't accidentally emit s2s code).

Then inspect the existing fork:

```bash
ls -la /Users/sarthak/PycharmProjects/references/grace/
ls /Users/sarthak/PycharmProjects/references/grace/rulesbook/codegen/
ls /Users/sarthak/PycharmProjects/references/grace/src/
git -C /Users/sarthak/PycharmProjects/references/grace branch -a
cat /Users/sarthak/PycharmProjects/references/grace/pyproject.toml
```

And glance at the upstream for context (don't change anything there):

```bash
ls /Users/sarthak/PycharmProjects/references/juspay-prism/grace/
```

---

## Hard constraints (do not violate)

- **One AI backend**: Claude Code only. **Do not introduce an `AIProvider` ABC.** Do not import `openai` or `anthropic`. A single `ClaudeCodeRunner` class shells out to the local `claude` CLI. The spec calls this out explicitly because previous design rounds had AI pluggability and it was deliberately removed.
- **Generated code must conform to Lens's locked `Connector` ABC** exactly. Method names, signatures, type arguments — all pinned in `SUBPROJECT_LENS.md` §4.2.
- **Generated-file marker** (constitution §4) is mandatory on every emitted file. Quality gates fail if absent or malformed.
- **`status_map.py`** is a required output file. The rubric checks for it.
- **Out-of-scope flows**: do NOT emit `authorize`, `capture`, `void`, `setup_mandate`, `repeat_payment`, 3DS, payouts, disputes. Those are in `FUTURE_S2S_INTERFACE.md` for a later product slice.
- **`mypy --strict` and `pytest --cov ≥ 80%`** mandatory on the **generated** package. The rubric enforces them as scored dimensions.
- **No production runtime**: Grace runs on dev / CI only. Don't add daemons, schedulers, services.
- **Track upstream**: `python-support` is a feature branch off `main` until merged. After v1 acceptance, it merges into `main` and is deleted. Upstream `juspay-prism/grace/` continues to be subtree-merged into `main` periodically.

If you find yourself violating any of these, **stop and ask**.

---

## What "done" looks like

Spec §8 lists the acceptance criteria:

- `grace generate cashfree --from <url>` produces a working `connectors/cashfree/` package with all four flow files + `webhook` + `auth` + `common` + `models` + `status_map.py` + tests.
- Every emitted file has the constitution §4 marker.
- `mypy --strict` clean on the emitted package.
- `pytest --cov ≥ 80%` on the emitted package.
- Rubric ≥ 60 / 100 (6 dimensions: marker 5, type correctness 20, coverage 25, public surface 20, error handling 20, PII discipline 10).
- The generated `Cashfree(Connector)` class is registered via `ConnectorFactory.register("cashfree", Cashfree)`.
- `grace generate razorpay --from <url>` produces a complete connector from scratch passing all gates (no hand-written reference).
- `grace doctor` reports whether Claude Code is reachable and authenticated.
- `grace regenerate cashfree` re-runs the previous generation with the same arguments.
- The `python-support` branch is merged into `main`.

---

## Process

1. Read the documents in the order above.
2. Invoke the **`superpowers:executing-plans`** skill via the Skill tool. It guides plan-driven implementation with review checkpoints. Follow its workflow.
3. Work through the plan step by step. **Run the step's verification gate before moving on.**
4. The plan is heavy on iteration in Step 5 (regenerate Cashfree → diff → adjust rulebook → repeat). Expect 2–4 iterations before Cashfree lands clean. **Iterate the rulebook, not the prompt** — Claude reads files; if Claude is missing something, the rulebook is incomplete, not the prompt.
5. **When you hit ambiguity**:
   - First check the plan's "Handoff notes" — the plan author documented several interpretations (marker line count, `claude` CLI flags, `regenerate` storage, rubric scoring rules).
   - If still ambiguous, check the spec's §10 open questions.
   - If still ambiguous, ask the user.
6. **Don't over-engineer the prompt to Claude.** Hand Claude file paths and a short directive. If output is wrong, sharpen the rulebook.
7. **Step 5 dependency**: requires Lens's Step 3 (hand-written Cashfree) to exist. If it doesn't yet, you can do Steps 0–4 + 6 (Razorpay first) and come back to Step 5 once Cashfree lands.

---

## Reporting

Report progress at the end of each plan step. Each report:

- Which step finished + verification gates passed.
- For Step 5: how many rulebook iterations were needed; what the final diff showed.
- Any blockers, spec ambiguities, decisions made.
- Next step + ETA.

**Final report** at end of Step 7:

- All acceptance criteria from spec §8 passing.
- Generated Cashfree diffs cleanly against the hand-written reference (Step 5).
- Generated Razorpay passes gates from scratch (Step 6).
- `python-support` merged into `main` (Step 7).
- A short list of TODOs (e.g., additional PSP support, additional patterns, post-launch rulebook polish).
- Branch / commit SHA so the user can inspect.

---

## Out of scope (DO NOT BUILD)

- A second AI backend (no OpenAI, no Anthropic SDK, no Bedrock, no Gemini, no `AIProvider` ABC).
- Runtime / production code generation.
- Generating in any language other than Python.
- PSPs other than the two demos (Cashfree regen + Razorpay from scratch).
- Patterns / rulebook content for `authorize` / `capture` / `void` / `setup_mandate` / 3DS / payouts. These live in `FUTURE_S2S_INTERFACE.md`.

---

## Quick orientation

- **Where to start**: read the constitution, then your sub-project spec, then Lens's spec (§4 especially), then your plan. Then `ls` the existing fork.
- **Critical-path note**: Step 5 (regen Cashfree) is the most variable step — expect rulebook iteration. Don't move to Step 6 until Step 5's diff is clean.
- **The hand-written Cashfree is the source of truth.** When Grace's Cashfree output disagrees with the reference on a load-bearing detail, the **rulebook** is the bug, not the reference.
- **Don't import `lens` from inside Grace at runtime.** Grace's gates _run_ `mypy --strict` and `pytest` as subprocesses against the generated package — `lens` must be importable in Grace's working venv (the plan's Step 0 wires this in). Don't add a runtime dependency.

When you're ready, start reading.
