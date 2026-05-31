# Status mapping

Every PSP has its own vocabulary. The `status_map.py` files translate each PSP-specific term
into locked lens types. There are **three mapping surfaces** in a domain-modular connector:

| File | Maps | Destination |
|---|---|---|
| `orders/status_map.py` | PSP payment-attempt status | `(PaymentAttemptStatus, PaymentFailureCode \| None)` |
| `subscriptions/status_map.py` | PSP subscription status | `MandateStatus` |
| `subscriptions/status_map.py` | PSP event-type string | `WebhookEventType` |
| `core/status.py` | failure free-text → `(PaymentFailureCode, FailureClass)` | shared by both domains |

---

## 1. Payment-attempt status (`orders/status_map.py`)

Same pattern as lens 0.1. Translate PSP-specific payment status terms into the locked
`(PaymentAttemptStatus, PaymentFailureCode | None)` pair.

```python
# orders/status_map.py
from lens.enums import PaymentAttemptStatus, PaymentFailureCode
import structlog

_log = structlog.get_logger(__name__)

STATUS_MAP: dict[str, tuple[PaymentAttemptStatus, PaymentFailureCode | None]] = {
    "SUCCESS":      (PaymentAttemptStatus.SUCCESS, None),
    "FAILED":       (PaymentAttemptStatus.FAILED,  PaymentFailureCode.CARD_DECLINED),
    "USER_DROPPED": (PaymentAttemptStatus.FAILED,  PaymentFailureCode.USER_DROPPED),
    "CANCELLED":    (PaymentAttemptStatus.FAILED,  PaymentFailureCode.USER_CANCELLED),
    "FLAGGED":      (PaymentAttemptStatus.PENDING, PaymentFailureCode.FRAUD_REVIEW_PENDING),
    "PENDING":      (PaymentAttemptStatus.PENDING, None),
    # ... complete from PSP docs
}


def map_payment_status(
    psp_term: str,
) -> tuple[PaymentAttemptStatus, PaymentFailureCode | None]:
    mapped = STATUS_MAP.get(psp_term)
    if mapped is not None:
        return mapped
    _log.warning("unknown_psp_payment_status", value=psp_term)
    return (PaymentAttemptStatus.FAILED, PaymentFailureCode.UNKNOWN)
```

**Every status term the PSP documents must appear in `STATUS_MAP`.** Unknown terms fall back
to `(FAILED, UNKNOWN)` with a warning — never silently default.

---

## 2. Subscription status (`subscriptions/status_map.py`)

Translate PSP-specific subscription/mandate status strings into `MandateStatus`.

```python
# subscriptions/status_map.py
from lens.enums import MandateStatus, WebhookEventType
import structlog

_log = structlog.get_logger(__name__)

SUBSCRIPTION_STATUS_MAP: dict[str, MandateStatus] = {
    # PSP term → MandateStatus — fill from PSP docs + connector_docs/<psp>.md §6
    "ACTIVE":   MandateStatus.ACTIVE,
    "PAUSED":   MandateStatus.PAUSED,
    # ... complete from per-PSP spec
}


def map_subscription_status(psp_term: str) -> MandateStatus:
    mapped = SUBSCRIPTION_STATUS_MAP.get(psp_term)
    if mapped is not None:
        return mapped
    _log.warning("unknown_psp_subscription_status", value=psp_term)
    return MandateStatus.FAILED   # closest "unknown" fallback
```

---

## 3. Webhook event type (`subscriptions/status_map.py`, continued)

Translate PSP-specific event-type strings into `WebhookEventType`.

```python
EVENT_TYPE_MAP: dict[str, WebhookEventType] = {
    # PSP event string → WebhookEventType — fill from PSP docs
    "SUBSCRIPTION_AUTH_STATUS":               WebhookEventType.MANDATE_AUTHORIZED,
    "SUBSCRIPTION_PAYMENT_SUCCESS":           WebhookEventType.MANDATE_DEBIT_SUCCESS,
    "SUBSCRIPTION_PAYMENT_FAILED":            WebhookEventType.MANDATE_DEBIT_FAILED,
    "SUBSCRIPTION_PAYMENT_NOTIFICATION_INITIATED": WebhookEventType.MANDATE_DEBIT_NOTIFIED,
    # ... complete from per-PSP spec
}


def map_event_type(psp_event: str) -> WebhookEventType:
    mapped = EVENT_TYPE_MAP.get(psp_event)
    if mapped is not None:
        return mapped
    _log.warning("unknown_psp_event_type", value=psp_event)
    return WebhookEventType.MANDATE_DEBIT_FAILED   # closest fallback
```

---

## 4. Failure free-text → `(PaymentFailureCode, FailureClass)` (`core/status.py`)

Mandate debit failures are often described by the PSP with a free-text reason string rather
than a typed code. The `core/status.py` module provides a **shared**, ordered substring-match
lookup used by both domains:

```python
# core/status.py
from lens.enums import FAILURE_CLASS, FailureClass, PaymentFailureCode
from typing import Mapping

# Ordered — first match wins. Entries with overlapping substrings must be
# listed most-specific first.
_FAILURE_SUBSTRINGS: list[tuple[str, PaymentFailureCode]] = [
    ("revoke", PaymentFailureCode.MANDATE_REVOKED),
    ("pause",  PaymentFailureCode.MANDATE_PAUSED),
    ("expir",  PaymentFailureCode.MANDATE_EXPIRED),
    ("not found", PaymentFailureCode.MANDATE_NOT_FOUND),
    ("limit exceed", PaymentFailureCode.DEBIT_LIMIT_EXCEEDED),
    ("insufficient", PaymentFailureCode.INSUFFICIENT_FUNDS),
    ("declined",     PaymentFailureCode.CARD_DECLINED),
    ("invalid",      PaymentFailureCode.INVALID_INSTRUMENT),
    ("network",      PaymentFailureCode.NETWORK_ERROR),
    # ... extend from per-PSP spec (connector_docs/<psp>.md §6)
]


def map_failure_reason(
    free_text: str | None,
) -> tuple[PaymentFailureCode, FailureClass | None]:
    """Ordered substring match; defaults to (UNKNOWN, None) on no match.

    The connector sets ``MandateDebitOutcome.failure_code`` from this
    function's first return value. The caller (Orbit) looks up
    ``FAILURE_CLASS[code]`` itself — lens never branches on FailureClass.
    """
    if not free_text:
        return (PaymentFailureCode.UNKNOWN, None)
    lower = free_text.lower()
    for substring, code in _FAILURE_SUBSTRINGS:
        if substring in lower:
            return (code, FAILURE_CLASS.get(code))
    return (PaymentFailureCode.UNKNOWN, None)
```

`FAILURE_CLASS` is imported from `lens.enums` — **never redeclare it**. It maps
`PaymentFailureCode → FailureClass` (RETRIABLE or TERMINAL). The connector only sets
`failure_code`; Orbit reads `FAILURE_CLASS[code]` to decide charge-failed vs
charge-failed-final. Lens **never branches on FailureClass** — it has no retry logic.

---

## 5. Periodic-mode finality rule

In periodic (PSP-driven) mode there is **no `*_FAILED_FINAL` event**. Finality is signalled
by a combination of:

- The mandate status reaching `MANDATE_SUSPENDED` (the `WebhookEventType`), AND
- `MandateDebitOutcome.psp_attempt` reflecting the PSP's retry-attempt count.

Orbit uses these two signals to decide whether to call the subscription permanently failed.
The connector sets both fields faithfully from the PSP payload; it does **not** synthesise
a `*_FAILED_FINAL` variant.

---

## Rules

- **Read the PSP's docs for the full status list.** Don't guess. Every status and event type
  the PSP documents must appear in the relevant map.
- **Don't promote PSP-specific terms to first-class lens types.** They are keys in the map;
  the lens enum values are the map's values.
- **Unknown terms must fall back with a `structlog.warning`** and the documented default.
  Never silently default.
- **Mapping is one-way: PSP → lens.** Never translate lens values back to PSP terms.
- **`FAILURE_CLASS` is published data, not logic.** Import it from `lens.enums`; never
  redeclare it; never branch on it inside the connector. The connector only sets
  `failure_code`; Orbit reads the class map.
- **The shared failure-substring map lives in `core/status.py`** and is consumed by both
  `orders/` and `subscriptions/` domain code. Don't duplicate it.
