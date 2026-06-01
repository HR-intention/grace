# Pattern: build_webhook_handlers (shared webhook router)

In lens 0.2.0, **there is no `handle_webhook` connector method**. Webhooks are dispatched by
the shared `WebhookRouter` using PSP-supplied callables bundled in `WebhookHandlers`. The
connector author's job is to implement `build_webhook_handlers(config) -> WebhookHandlers`
in `webhooks.py` at the package root. Grace registers this builder separately via
`ConnectorFactory.register_webhook`.

See `../python/webhook_handling.md` for the full architecture. This file is the implementation
reference for the webhook module.

## Domain types involved

- `WebhookHandlers` (from `lens.webhook`) — frozen dataclass of four callables.
- `WebhookFamily` (from `lens.webhook`) — `StrEnum`: `PAYMENT` | `MANDATE`.
- `WebhookRouter` (from `lens.webhook`) — instantiated by Orbit; the connector author does not
  instantiate it directly.
- `PaymentWebhookEvent` (from `lens.domain_types`) — returned by `parse_payment`.
- `MandateWebhookEvent` (from `lens.domain_types`) — returned by `parse_mandate`.

## Key principle: verify once, dispatch by family

```
inbound bytes + headers
      │
      ▼
  WebhookRouter.handle()
      │
      ├─ verify(raw, headers)  ──► False → ConnectorError(WEBHOOK_SIGNATURE_FAILED)
      │
      ├─ classify(raw)  ──► WebhookFamily.PAYMENT   ──► parse_payment(raw)  → PaymentWebhookEvent
      │                 └─► WebhookFamily.MANDATE   ──► parse_mandate(raw)  → MandateWebhookEvent
      │
      └─ no parser registered for that family  ──► ConnectorError(NOT_SUPPORTED)
```

The router verifies the signature **exactly once**. Domain parsers (`_parse_payment_webhook`,
`_parse_mandate_webhook`) receive already-verified bytes and must **not** re-verify.

## File layout for webhook code

```
<psp>/
├── webhooks.py                        ← Grace-owned compose surface; exports build_webhook_handlers
├── core/
│   └── auth.py                        ← verify_signature(config, raw, headers) → bool
├── orders/
│   └── webhooks.py                    ← _parse_payment_webhook(raw) → PaymentWebhookEvent
└── subscriptions/
    └── webhooks.py                    ← _parse_mandate_webhook(raw) → MandateWebhookEvent
```

## `build_webhook_handlers` — the root `webhooks.py`

```python
# webhooks.py (package root — Grace-owned compose surface)
from __future__ import annotations

import json
from typing import Callable

from lens.webhook import WebhookFamily, WebhookHandlers
from lens.factory import ConnectorConfig

from <psp>.core.auth import verify_signature as _verify_raw
from <psp>.orders.webhooks import _parse_payment_webhook
from <psp>.subscriptions.webhooks import _parse_mandate_webhook   # omit for payments-only PSP


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

    Uses a lightweight envelope parse (no full Pydantic model) to read the
    discriminator field. The exact field name and prefix are PSP-specific —
    read connector_docs/<psp>.md §classify.
    """
    try:
        envelope = json.loads(raw)
        event_type: str = envelope.get("type", "") or envelope.get("event_type", "")
    except (json.JSONDecodeError, AttributeError):
        return WebhookFamily.PAYMENT   # safe default; parser will raise INVALID_REQUEST

    # PSP-specific discriminator logic — fill prefixes from connector_docs/<psp>.md:
    if event_type.startswith("SUBSCRIPTION_") or event_type.startswith("MANDATE_"):
        return WebhookFamily.MANDATE
    return WebhookFamily.PAYMENT
```

## `verify_signature` — `core/auth.py`

The HMAC verification helper. Its shape depends on what the PSP signs (see PSP docs):

```python
import hmac
import hashlib

from lens.factory import ConnectorConfig


def verify_signature(
    config: ConnectorConfig,
    raw_payload: bytes,
    headers: dict[str, str],
) -> bool:
    """Return True iff the PSP's signature header matches an HMAC over raw_payload.

    Algorithm: <PSP-specific — document here, e.g. HMAC-SHA256(secret, payload)>.
    """
    secret = config.webhook_secret.expose().encode()
    # Build the signed data string (PSP-specific — may be raw_payload, may be timestamp+"."+payload):
    signed_data = raw_payload   # adjust per PSP docs
    expected = hmac.new(secret, signed_data, hashlib.sha256).hexdigest()
    received = headers.get("<psp-signature-header>", "")
    return hmac.compare_digest(expected, received)   # constant-time compare — always
```

**Rules:**
- Use `hmac.compare_digest` — never `==` on strings.
- Resolve `config.webhook_secret.expose()` at call time, never at construction time.
- Do **not** decode `raw_payload` before computing the signature.
- Document the algorithm and the signed-data format in a comment on `verify_signature`.

## Registration (in `__init__.py`)

```python
from lens.factory import ConnectorFactory
from <psp>.connector import <Psp>Connector
from <psp>.webhooks import build_webhook_handlers

ConnectorFactory.register("<psp>", <Psp>Connector)
ConnectorFactory.register_webhook("<psp>", build_webhook_handlers)
```

Both `register` and `register_webhook` are **required**. A package that calls only `register`
will fail the public-surface rubric check.

## Errors to surface

| Condition | Outcome |
|---|---|
| Signature does not verify | `ConnectorError(WEBHOOK_SIGNATURE_FAILED)` — raised by `WebhookRouter.handle` immediately; the domain parsers never see this payload |
| Family parsed but no parser registered (`parse_mandate=None` for a mandate event) | `ConnectorError(NOT_SUPPORTED)` — raised by `WebhookRouter.handle` |
| JSON parse error in `_classify` | safe fallback to `PAYMENT`; let the downstream parser raise `INVALID_REQUEST` |
| Wire-model validation fails inside a domain parser | `ConnectorError(INVALID_REQUEST, psp_message=str(e))` — raised by the domain parser |

## Required tests

`tests/test_webhook_router.py` (package-local; Grace relocates `tests/` after generation):

- **Signed PAYMENT event** — build a signed payload that `_classify` routes to `PAYMENT`;
  call `WebhookRouter.handle`; assert return type is `PaymentWebhookEvent`.
- **Signed MANDATE event** — verify route to `MANDATE`; assert return type is
  `MandateWebhookEvent`.
- **Tampered payload** — flip one byte of a valid signed payload; assert
  `ConnectorError(reason=WEBHOOK_SIGNATURE_FAILED)`. This test must live here
  (cross-domain, tests the router integration), not inside a domain-specific test file.
- **Unknown family (payments-only PSP)** — if the PSP is payments-only, send a payload that
  `_classify` tags as `MANDATE`; assert `ConnectorError(reason=NOT_SUPPORTED)`.
- **Malformed JSON in classifier** — ensure safe fallback or INVALID_REQUEST, not an
  unhandled exception.

## Event field names — never cross them

`PaymentWebhookEvent` and `MandateWebhookEvent` have distinct raw-payload field names and
`occurred_at` presence. Do not mix them:

| | `PaymentWebhookEvent` | `MandateWebhookEvent` |
|---|---|---|
| raw dict | `raw_payload` | `raw` |
| `occurred_at` | **absent** | **present** |

```python
# orders/webhooks.py — CORRECT:
return PaymentWebhookEvent(
    event_type=event_type,
    psp_event_id=psp_event.event_id,
    psp_order_id=psp_event.order_id,
    raw_payload=payload_dict,   # ← raw_payload, never raw
    # DO NOT add occurred_at — field does not exist on PaymentWebhookEvent
)

# subscriptions/webhooks.py — CORRECT:
return MandateWebhookEvent(
    event_type=event_type,
    psp_mandate_ref=psp_event.subscription_id,
    psp_event_id=psp_event.event_id,
    occurred_at=psp_event.event_time,   # ← occurred_at IS present here
    raw=payload_dict,                   # ← raw, never raw_payload
)
```

## Pitfalls

- **Do NOT add a `handle_webhook` method to any connector class.** The `MandateConnector` and
  `PaymentsConnector` ABCs do not declare `handle_webhook`. Adding it as an instance method
  on the connector is a lens-0.1 pattern and must not appear in 0.2.0 connectors.
- **`_classify` must be stateless and cheap.** It is called on every inbound webhook before any
  family-specific work. Avoid full Pydantic model instantiation; a `json.loads` + dict lookup is
  sufficient.
- **Do not expose `webhook_secret` at module import time.** The verifier closes over `config`
  and calls `.expose()` at request time, so the secret is resolved lazily.
- **`parse_mandate=None` for a payments-only PSP**, not `parse_mandate=lambda _: ...`. Passing
  `None` lets the router raise `NOT_SUPPORTED` cleanly.
- **Signature header casing is PSP-defined.** `headers` is `dict[str, str]` with the casing
  the PSP sends. Do not lowercase keys yourself; look up by the documented exact header name.
- **`raw_payload` (payment) vs `raw` (mandate)** — never swap them; pydantic `extra="forbid"`
  will raise a `ValidationError` at construction time.
- **`occurred_at` only on `MandateWebhookEvent`** — do not add it to `PaymentWebhookEvent`.
