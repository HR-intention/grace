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
