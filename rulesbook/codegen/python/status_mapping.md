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

**Test requirement:** assert this finality mapping directly — the PSP's hold/suspend term must
map to `MandateStatus.SUSPENDED` (subscription status) **and** to
`WebhookEventType.MANDATE_SUSPENDED` (status-changed event). See `testing.md` → "Finality /
suspend mapping". Do not rely on a happy-path sync test to cover it.

---

## 6. PSP method-group → `PaymentMethod` mapping

`supported_methods` (the `@property` on `<Psp>Orders`) must return a `set[PaymentMethod]`
containing only **locked** `PaymentMethod` members. Use this table to map PSP group names:

| PSP group | Use |
|---|---|
| `card`, `credit_card`, `debit_card` | `PaymentMethod.CARD` |
| `upi` | `PaymentMethod.UPI` |
| `wallet` | `PaymentMethod.WALLET` |
| `bank_transfer`, `neft`, `rtgs`, `imps` | `PaymentMethod.BANK_TRANSFER` |
| `net_banking`, `netbanking` | `PaymentMethod.BANK_REDIRECT` |
| `emi`, `paylater`, `buy_now_pay_later` | pick the closest locked member or omit |

**Locked members (exact set):** `CARD`, `UPI`, `WALLET`, `BANK_TRANSFER`, `BANK_REDIRECT`.

`NET_BANKING`, `EMI`, `PAY_LATER` do **NOT** exist as `PaymentMethod` members. `mypy --strict`
will fail (`error: "type[PaymentMethod]" has no attribute "NET_BANKING"`) on any unknown member
access. Never invent a `PaymentMethod` member.

---

## 7. Raw-preserving many→few mapping (`payment_group → MandateRail`)

Some PSP fields are **coarser than the lens enum** — many raw values collapse to fewer enum
members. When this happens, preserve the raw source string alongside the normalized enum so
that callers retain the finer-grained information.

**Example: `payment_group → MandateRail`**

The PSP may return a `payment_group` string in its authorization block (e.g. `"upi"`,
`"enach"`, `"pnach"`, `"card"`, `"debit_card"`). The lens `MandateRail` enum has only two
members (`UPI_AUTOPAY`, `CARD_EMANDATE`), so multiple PSP groups collapse to the same enum
value. The raw `payment_group` must be kept on the event/response separately.

```python
# subscriptions/status_map.py
from lens.enums import MandateRail
import structlog

_log = structlog.get_logger(__name__)

# Many→few: multiple PSP groups collapse to two MandateRail members.
# Case-insensitive matching; unknown non-empty → None + warning; raw string preserved separately.
_PAYMENT_GROUP_MAP: dict[str, MandateRail] = {
    "upi":        MandateRail.UPI_AUTOPAY,
    "enach":      MandateRail.CARD_EMANDATE,
    "pnach":      MandateRail.CARD_EMANDATE,
    "card":       MandateRail.CARD_EMANDATE,
    "debit_card": MandateRail.CARD_EMANDATE,
}


def map_payment_group_to_rail(payment_group: str | None) -> MandateRail | None:
    """Map a PSP payment-group string to a MandateRail enum value.

    Returns None for absent/empty/unknown groups. Warns on unknown non-empty values.
    The caller is responsible for preserving the raw payment_group string alongside
    the returned enum — the enum is coarser and the raw value carries finer detail.
    """
    if not payment_group:
        return None
    mapped = _PAYMENT_GROUP_MAP.get(payment_group.lower())
    if mapped is not None:
        return mapped
    _log.warning("unknown_payment_group", value=payment_group)
    return None
```

**Calling pattern** (in `_parse_mandate_webhook` or `sync_subscription`):

```python
# Do NOT discard the raw payment_group — preserve it on the event:
raw_group: str | None = ...   # from the PSP auth block
realized_rail = map_payment_group_to_rail(raw_group)
event = MandateWebhookEvent(
    ...
    realized_rail=realized_rail,          # normalized (may be None for unknown)
    payment_group=raw_group,              # raw string preserved (keeps enach/pnach/card distinction)
    authorization_reference=...,
)
```

**Why preserve the raw value?** `MandateRail.CARD_EMANDATE` collapses `enach`, `pnach`,
`card`, and `debit_card`. The raw `payment_group` string retains the distinction — Orbit
may need it for analytics or routing. Always set `payment_group` from the raw PSP value,
regardless of whether `map_payment_group_to_rail` succeeded.

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
- **`net_banking` / `netbanking` → `BANK_REDIRECT`.** Never use a non-existent
  `PaymentMethod.NET_BANKING` member.
- **`supported_methods` returns only locked members.** Filter out any PSP group that has no
  close locked equivalent rather than inventing a new member.
