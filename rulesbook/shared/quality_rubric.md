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
