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
