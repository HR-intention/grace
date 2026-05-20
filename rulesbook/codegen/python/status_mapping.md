# Status mapping

Every PSP has its own vocabulary. The `status_map.py` you emit translates each PSP-specific term into the **locked** `(PaymentAttemptStatus, PaymentFailureCode | None)` pair.

## Worked example — Cashfree (from `SUBPROJECT_LENS.md` §5.2)

| Cashfree term | `PaymentAttemptStatus` | `PaymentFailureCode` | Notes |
|---|---|---|---|
| `SUCCESS` | `SUCCESS` | — | Happy path. |
| `FAILED` | `FAILED` | `CARD_DECLINED` (or per `error_code` mapping) | Look at Cashfree's `payment_message` for nuance. |
| `USER_DROPPED` | `FAILED` | `USER_DROPPED` | Cashfree-specific signal. |
| `CANCELLED` | `FAILED` | `USER_CANCELLED` | Rare; explicit cancel. |
| `FLAGGED` | `PENDING` | `FRAUD_REVIEW_PENDING` | Non-terminal; resolved by follow-up webhook. |
| `PENDING` | `PENDING` | — | Async method awaiting outcome (UPI etc.). |
| `NOT_ATTEMPTED` | (no PaymentAttempt is created) | — | We don't create an attempt for this. |

## Required shape

```python
# status_map.py
from lens.enums import PaymentAttemptStatus, PaymentFailureCode
import structlog

_log = structlog.get_logger(__name__)

# Module-scope dict — the source of truth.
STATUS_MAP: dict[str, tuple[PaymentAttemptStatus, PaymentFailureCode | None]] = {
    "SUCCESS": (PaymentAttemptStatus.SUCCESS, None),
    "FAILED":  (PaymentAttemptStatus.FAILED,  PaymentFailureCode.CARD_DECLINED),
    "USER_DROPPED": (PaymentAttemptStatus.FAILED, PaymentFailureCode.USER_DROPPED),
    "CANCELLED": (PaymentAttemptStatus.FAILED, PaymentFailureCode.USER_CANCELLED),
    "FLAGGED": (PaymentAttemptStatus.PENDING, PaymentFailureCode.FRAUD_REVIEW_PENDING),
    "PENDING": (PaymentAttemptStatus.PENDING, None),
}


def map_status(psp_term: str) -> tuple[PaymentAttemptStatus, PaymentFailureCode | None]:
    """Translate a PSP-specific status term into our domain pair.

    Unknown terms fall back to (FAILED, UNKNOWN) and log a warning so they get
    triaged into the table later.
    """
    mapped = STATUS_MAP.get(psp_term)
    if mapped is not None:
        return mapped
    _log.warning("unknown_psp_status", value=psp_term)
    return (PaymentAttemptStatus.FAILED, PaymentFailureCode.UNKNOWN)
```

## Rules

- **Read the PSP's docs for the full status list.** Don't guess. Every status the PSP documents must appear in `STATUS_MAP`.
- **Don't promote PSP-specific terms to first-class statuses.** `USER_DROPPED`, `CANCELLED`, `FLAGGED` are *failure codes*, not statuses.
- **Unknown terms must fall back to `(FAILED, UNKNOWN)`** with a `structlog.warning("unknown_psp_status", value=<raw>)`. Never silently default.
- **Don't translate failure codes back to PSP terms.** Mapping is one-way: PSP → ours.
- **Refund statuses** can use the same pattern if the PSP has its own vocabulary for refunds; map to `RefundStatus` instead of `PaymentAttemptStatus`. Most PSPs use simple `pending/success/failed` for refunds, in which case a tiny helper or a second dict is enough.
