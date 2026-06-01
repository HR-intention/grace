# Flow pattern: webhook handling (shared router)

In lens 0.2.0, **there is no `handle_webhook` connector method**. Webhooks
are dispatched by the shared `WebhookRouter` using PSP-supplied callables
bundled in `WebhookHandlers`. The connector author implements
`build_webhook_handlers(config) -> WebhookHandlers` in `webhooks.py` at
the package root. Grace registers this builder separately via
`ConnectorFactory.register_webhook`.

The old connector-method `handle_webhook` is a lens-0.1 pattern. **It must
not appear in 0.2.0 connectors.** The `PaymentsConnector` and
`MandateConnector` ABCs do not declare it.

---

## Architecture overview

```
inbound bytes + headers
      │
      ▼
  WebhookRouter.handle()        ← instantiated by Orbit; the connector author does NOT call this
      │
      ├─ verify(raw, headers)  ──► False → ConnectorError(WEBHOOK_SIGNATURE_FAILED)
      │
      ├─ classify(raw)  ──► WebhookFamily.PAYMENT   ──► parse_payment(raw)  → PaymentWebhookEvent
      │                 └─► WebhookFamily.MANDATE   ──► parse_mandate(raw)  → MandateWebhookEvent
      │
      └─ no parser registered for that family  ──► ConnectorError(NOT_SUPPORTED)
```

`WebhookRouter` verifies the signature **exactly once**. Domain parsers
(`_parse_payment_webhook`, `_parse_mandate_webhook`) receive already-verified
bytes and must **not** re-verify.

---

## File layout for webhook code

```
<psp>/
├── webhooks.py                       ← Grace-owned compose surface; exports build_webhook_handlers
├── core/
│   └── auth.py                       ← verify_signature(config, raw, headers) → bool
├── orders/
│   └── webhooks.py                   ← _parse_payment_webhook(raw) → PaymentWebhookEvent
└── subscriptions/
    └── webhooks.py                   ← _parse_mandate_webhook(raw) → MandateWebhookEvent
```

---

## Core types (from `lens.webhook`)

```python
from lens.webhook import WebhookFamily, WebhookHandlers, WebhookRouter
```

- **`WebhookFamily`** — `StrEnum`: `PAYMENT` | `MANDATE`.
- **`WebhookHandlers`** — frozen dataclass of four callables:
  - `verify: Callable[[bytes, dict[str, str]], bool]`
  - `classify: Callable[[bytes], WebhookFamily]`
  - `parse_payment: Callable[[bytes], PaymentWebhookEvent] | None`
  - `parse_mandate: Callable[[bytes], MandateWebhookEvent] | None`
- **`WebhookRouter`** — instantiated by Orbit from a `WebhookHandlers`; the connector author never calls it directly.

---

## `build_webhook_handlers` — root `webhooks.py`

```python
# webhooks.py (package root — Grace-owned compose surface)
from __future__ import annotations

import json
from typing import Callable

from lens.webhook import WebhookFamily, WebhookHandlers
from lens.factory import ConnectorConfig

from <psp>.core.auth import verify_signature as _verify_raw
from <psp>.orders.webhooks import _parse_payment_webhook
from <psp>.subscriptions.webhooks import _parse_mandate_webhook   # omit for payments-only


def build_webhook_handlers(config: ConnectorConfig) -> WebhookHandlers:
    return WebhookHandlers(
        verify=_build_verifier(config),
        classify=_classify,
        parse_payment=_parse_payment_webhook,
        parse_mandate=_parse_mandate_webhook,   # set None for a payments-only PSP
    )


def _build_verifier(
    config: ConnectorConfig,
) -> Callable[[bytes, dict[str, str]], bool]:
    """Close over config so the secret is resolved at call time, not at registration time."""
    def _verify(raw: bytes, headers: dict[str, str]) -> bool:
        return _verify_raw(config, raw, headers)
    return _verify


def _classify(raw: bytes) -> WebhookFamily:
    """Determine whether a raw payload belongs to the PAYMENT or MANDATE family.

    Uses a lightweight envelope parse (no full Pydantic model). The exact
    discriminator logic is PSP-specific — read connector_docs/<psp>.md §classify.
    """
    try:
        envelope = json.loads(raw)
        event_type: str = envelope.get("type", "") or envelope.get("event_type", "")
    except (json.JSONDecodeError, AttributeError):
        return WebhookFamily.PAYMENT   # safe default; parser will raise INVALID_REQUEST

    if event_type.startswith("SUBSCRIPTION_") or event_type.startswith("MANDATE_"):
        return WebhookFamily.MANDATE
    return WebhookFamily.PAYMENT
```

---

## `verify_signature` — `core/auth.py`

```python
import hmac
import hashlib

from lens.factory import ConnectorConfig


def verify_signature(
    config: ConnectorConfig,
    raw_payload: bytes,
    headers: dict[str, str],
) -> bool:
    """Return True iff the PSP's signature header matches an HMAC over raw_payload."""
    secret = config.webhook_secret.expose().encode()
    signed_data = raw_payload   # adjust per PSP docs (may be timestamp + "." + payload)
    expected = hmac.new(secret, signed_data, hashlib.sha256).hexdigest()
    received = headers.get("<psp-signature-header>", "")
    return hmac.compare_digest(expected, received)   # constant-time — always
```

**Rules:**
- Use `hmac.compare_digest` — never `==` on strings.
- Resolve `config.webhook_secret.expose()` at call time, never at construction time.
- Do not `.decode()` `raw_payload` before computing the signature.

---

## Domain parsers

Each domain folder owns its own parser. These are called by the router after
signature verification, so they only need to parse and normalise:

```python
# orders/webhooks.py
from lens.domain_types import PaymentWebhookEvent

def _parse_payment_webhook(raw: bytes) -> PaymentWebhookEvent:
    """Verify-then-parse is already done by the router. This just normalises."""
    ...
```

```python
# subscriptions/webhooks.py
from lens.domain_types import MandateWebhookEvent

def _parse_mandate_webhook(raw: bytes) -> MandateWebhookEvent:
    """Called by the router after signature verification for MANDATE family events."""
    ...
```

On wire-model validation failure: `raise ConnectorError(reason=ConnectorErrorReason.INVALID_REQUEST, psp_message=str(e))`.

---

## Registration in `__init__.py`

```python
from lens.factory import ConnectorFactory
from <psp>.connector import <Psp>Connector
from <psp>.webhooks import build_webhook_handlers

ConnectorFactory.register("<psp>", <Psp>Connector)
ConnectorFactory.register_webhook("<psp>", build_webhook_handlers)
```

Both calls are required. A package that calls only `register` but not
`register_webhook` will fail the public-surface rubric check.

---

## Error semantics

| Condition | Outcome |
|---|---|
| Signature does not verify | `ConnectorError(WEBHOOK_SIGNATURE_FAILED)` — raised by `WebhookRouter.handle`; domain parsers never see this payload |
| Family parsed but no parser registered (`parse_mandate=None`) | `ConnectorError(NOT_SUPPORTED)` — raised by `WebhookRouter.handle` |
| JSON parse error in `_classify` | safe fallback to `PAYMENT`; let the downstream parser raise `INVALID_REQUEST` |
| Wire-model validation fails inside a domain parser | `ConnectorError(INVALID_REQUEST, psp_message=str(e))` |

---

## Required tests

`tests/integration/connectors/<psp>/test_webhook_router.py`:

1. **Signed PAYMENT event** — build a signed payload that `_classify` routes to `PAYMENT`; call `WebhookRouter.handle`; assert return type is `PaymentWebhookEvent`.
2. **Signed MANDATE event** — verify route to `MANDATE`; assert return type is `MandateWebhookEvent`.
3. **Tampered payload** — flip one byte after signing; assert `ConnectorError(reason=WEBHOOK_SIGNATURE_FAILED)`.
4. **Unknown family (payments-only PSP)** — send a payload `_classify` tags as `MANDATE`; assert `ConnectorError(reason=NOT_SUPPORTED)`.
5. **Malformed JSON in classifier** — ensure safe fallback or `INVALID_REQUEST`, not an unhandled exception.

---

## Pitfalls

- **Do NOT add a `handle_webhook` method to any connector class.** The `PaymentsConnector` and `MandateConnector` ABCs do not declare `handle_webhook`. Adding it is a lens-0.1 pattern and scores 0 in the `error_handling` rubric dimension.
- **`_classify` must be stateless and cheap.** It is called on every inbound webhook before any family-specific work. Avoid full Pydantic model instantiation; a `json.loads` + dict lookup is sufficient.
- **Do not expose `webhook_secret` at module import time.** The verifier closes over `config` and calls `.expose()` at request time.
- **`parse_mandate=None` for a payments-only PSP**, not `parse_mandate=lambda _: ...`. Passing `None` lets the router raise `NOT_SUPPORTED` cleanly.
- **Signature header casing is PSP-defined.** `headers` is `dict[str, str]` with the casing the PSP sends. Look up by the documented exact header name.
- **Domain parsers must not re-verify.** The `WebhookRouter` already called `verify` before dispatching. Re-verifying in the parser is redundant and wasteful.
