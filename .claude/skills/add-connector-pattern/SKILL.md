---
name: add-connector-pattern
description: Use when the user wants to add a new flow pattern (e.g., pattern_<flow>.md) or payment-method pattern under `rulesbook/codegen/guides/patterns/`. Walks through the required section shape, prerequisite chain, macro template usage, and wiring into the right `.gracerules*` entrypoint so the new pattern is actually applied by codegen.
---

# Add a connector pattern to the rulesbook

Patterns under `rulesbook/codegen/guides/patterns/` are templates the external AI coding agent applies when implementing Rust connectors. A pattern that's structurally off — or not wired into `.gracerules*` — will silently never be used.

## When to use

User asks to:
- "Add a pattern for `<FlowName>`"
- "Add a payment-method pattern for `<Category>:<Method>`"
- "Document how `<Flow>` should be implemented"

## Decide what kind of pattern

| Pattern type | Location | Wired from |
|---|---|---|
| **Core flow** (Authorize/Capture/Refund/Void/PSync/RSync) | `rulesbook/codegen/guides/patterns/pattern_<flow>.md` | `.gracerules` (always) |
| **Advanced flow** (SetupMandate, RepeatPayment, IncomingWebhook, DefendDispute, etc.) | `rulesbook/codegen/guides/patterns/pattern_<flow>.md` | `.gracerules_add_flow` (and `.gracerules` if listed in core 6) |
| **Payment method (under Authorize)** | `rulesbook/codegen/guides/patterns/authorize/<category>/pattern_authorize_<pm>.md` | `.gracerules_add_payment_method` |

Categories: `card`, `wallet`, `bank_transfer`, `bank_debit`, `bank_redirect`, `upi`, `bnpl`, `crypto`, `gift_card`, `mobile_payment`, `reward`.

## Required structure

Use an existing peer as a template. Good references:

- Flow pattern: [pattern_authorize.md](rulesbook/codegen/guides/patterns/pattern_authorize.md), [pattern_refund.md](rulesbook/codegen/guides/patterns/pattern_refund.md)
- Payment-method pattern: [authorize/upi/pattern_authorize_upi.md](rulesbook/codegen/guides/patterns/authorize/upi/pattern_authorize_upi.md), [authorize/crypto/pattern_authorize_crypto.md](rulesbook/codegen/guides/patterns/authorize/crypto/pattern_authorize_crypto.md)

Every pattern file MUST contain these sections (in this order):

1. **🎯 Quick Start** — one-liner of what the pattern produces, plus placeholder list (`{ConnectorName}`, `{connector}`, `{base_url}`, etc.).
2. **📋 Prerequisites** — which flows must already exist. See the dependency DAG in [CLAUDE.md](CLAUDE.md) (e.g., Refund needs Capture; RepeatPayment needs SetupMandate).
3. **🏗️ Modern Macro-Based Template** — Rust code block using `macro_connector_implementation!` with the right arguments. Cross-check the macro signature against [macro_patterns_reference.md](rulesbook/codegen/guides/patterns/macro_patterns_reference.md).
4. **🔧 Legacy Manual Pattern** *(optional, only if the macro doesn't cover the case)* — the manual trait-based implementation, with a note on why the macro isn't sufficient.
5. **🧪 Testing Strategy** — grpcurl invocation example. **Never recommend `cargo test`** — UCS doesn't test connectors that way.
6. **✅ Validation Checklist** — what the implementer/quality reviewer should verify.

## Type-system rules (non-negotiable)

The pattern's Rust snippets must use:
- `RouterDataV2` (not `RouterData`)
- `ConnectorIntegrationV2` (not `ConnectorIntegration`)
- Imports from `domain_types::*` (not `hyperswitch_*`)
- Generic struct: `pub struct ConnectorName<T> { phantom: PhantomData<T> }`
- Macro-based impls (prefer over manual)

These come from the UCS architecture decision in [rulesbook/codegen/README.md](rulesbook/codegen/README.md). Any pattern violating them produces broken connectors.

## Wiring the pattern (the easy step to forget)

A new pattern file does nothing unless the relevant `.gracerules*` references it.

```bash
# For a flow pattern, append a reference in both:
grep -n "pattern_" rulesbook/codegen/.gracerules | head -20
grep -n "pattern_" rulesbook/codegen/.gracerules_add_flow | head -20
```

Add an entry in the format the existing list uses (each `.gracerules*` has a "Pattern References" or flow-mapping section — match it).

For payment-method patterns, the category routing happens in `.gracerules_add_payment_method`; the new pattern file's path must match the category prefix expected there.

## Final check — quality & feedback alignment

Before considering the pattern done:
1. Skim [guides/feedback.md](rulesbook/codegen/guides/feedback.md) for past issues with this flow type — the new pattern should pre-emptively address them.
2. Skim [guides/learnings/learnings.md](rulesbook/codegen/guides/learnings/learnings.md) for relevant historical lessons.
3. Run the `rulesbook-pattern-auditor` subagent on the new file:
   ```
   Audit the new pattern at rulesbook/codegen/guides/patterns/pattern_<flow>.md
   ```

## Step-by-step

1. Confirm which kind of pattern (flow / payment-method) and where it goes.
2. Read 2–3 peer patterns to internalize the shape.
3. Read the matching `pattern_macro_guide.md` and `macro_patterns_reference.md` for macro arguments.
4. Write the new pattern with all six required sections.
5. Wire it into the appropriate `.gracerules*` file(s).
6. Run `rulesbook-pattern-auditor` on it.
7. Address the audit's critical issues. Warnings are judgment calls.

## Hard rules

- Do NOT recommend `cargo test` anywhere.
- Do NOT introduce new placeholder syntax — use `{Like}` / `{like_this}` consistent with other patterns.
- Do NOT skip the Prerequisites section, even if it's "none".
- Do NOT write Rust that imports from `hyperswitch_*` — UCS uses `domain_types::*`.
- A pattern that doesn't appear in any `.gracerules*` is dead code. Wire it or delete it.
