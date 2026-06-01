# Webhook handling

Webhooks in lens 0.2.0 are **NOT a connector method**. No connector class owns a webhook
entry-point. Instead, a PSP registers a `WebhookHandlers` dataclass with the factory,
and a shared `WebhookRouter` dispatches inbound payloads using those handlers.

The PSP-side webhook code lives entirely in the Grace-owned compose surface — specifically
`webhooks.py` at the package root — and is registered separately via
`ConnectorFactory.register_webhook("<psp>", build_webhook_handlers)`.

---

## Core types (from `lens.webhook`)

```python
from lens.webhook import WebhookFamily, WebhookHandlers, WebhookRouter
```

- **`WebhookFamily`** — `StrEnum` with two values: `PAYMENT` and `MANDATE`.
- **`WebhookHandlers`** — frozen dataclass; holds four callables:
  - `verify: Callable[[bytes, dict[str, str]], bool]` — signature check (closes over config/secret).
  - `classify: Callable[[bytes], WebhookFamily]` — determines the event family from raw bytes.
  - `parse_payment: Callable[[bytes], PaymentWebhookEvent] | None` — parses a payment event.
  - `parse_mandate: Callable[[bytes], MandateWebhookEvent] | None` — parses a mandate event.
- **`WebhookRouter`** — instantiated with a `WebhookHandlers`; exposes
  `async handle(raw_payload, headers) -> PaymentWebhookEvent | MandateWebhookEvent`. Calls
  `verify` first; raises `ConnectorError(WEBHOOK_SIGNATURE_FAILED)` on failure. Then calls
  `classify`, dispatches to the matching parser; raises `ConnectorError(NOT_SUPPORTED)` if
  no parser handles the family.

---

## The `build_webhook_handlers` function

Every PSP-generated package exposes exactly this public function in `webhooks.py`:

```python
def build_webhook_handlers(config: ConnectorConfig) -> WebhookHandlers:
    ...
```

Grace assembles the `WebhookHandlers` dataclass from three PSP-local helpers.

### Step 1 — `verify` callable (closes over config)

```python
# webhooks.py (root)
from <psp>.core.auth import verify_signature as _verify_raw

def _build_verifier(config: ConnectorConfig) -> Callable[[bytes, dict[str, str]], bool]:
    def _verify(raw: bytes, headers: dict[str, str]) -> bool:
        return _verify_raw(config, raw, headers)
    return _verify
```

`verify_signature` is the PSP-specific HMAC helper in `core/auth.py`. It is called with the
full `ConnectorConfig` so it can access `config.webhook_secret.expose()` at call time (not at
construction time — see pitfall 5b).

### Step 2 — `_classify` function

```python
def _classify(raw: bytes) -> WebhookFamily:
    """Determine whether a raw PSP payload belongs to the PAYMENT or MANDATE family."""
    # Parse the envelope minimally — look at a discriminator field
    # (e.g. the event_type string prefix or a top-level 'type' key).
    import json
    envelope = json.loads(raw)
    event_type: str = envelope.get("type", "")
    if event_type.startswith("SUBSCRIPTION_") or event_type.startswith("MANDATE_"):
        return WebhookFamily.MANDATE
    return WebhookFamily.PAYMENT
```

This is a pure, stateless function. It uses a lightweight parse (no full Pydantic model)
sufficient to discriminate the family. The exact discriminator logic depends on the PSP — read
the per-PSP spec in `connector_docs/<psp>.md`.

### Step 3 — domain parsers

Each domain folder owns its own parser:

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
    ...
```

### Step 4 — assembling `WebhookHandlers`

```python
# webhooks.py (root)
from lens.webhook import WebhookFamily, WebhookHandlers
from lens.factory import ConnectorConfig
from <psp>.orders.webhooks import _parse_payment_webhook
from <psp>.subscriptions.webhooks import _parse_mandate_webhook


def build_webhook_handlers(config: ConnectorConfig) -> WebhookHandlers:
    return WebhookHandlers(
        verify=_build_verifier(config),
        classify=_classify,
        parse_payment=_parse_payment_webhook,
        parse_mandate=_parse_mandate_webhook,
    )
```

For a payments-only PSP, set `parse_mandate=None`. The router raises `NOT_SUPPORTED` for any
inbound `MANDATE` family event.

---

## Error semantics

| Condition | Outcome |
|---|---|
| Signature does not verify | `ConnectorError(reason=WEBHOOK_SIGNATURE_FAILED)` — raised by `WebhookRouter.handle` immediately after the `verify` callable returns `False`. |
| Family parsed but no parser registered | `ConnectorError(reason=NOT_SUPPORTED)` — raised by `WebhookRouter.handle`. |
| JSON decode failure inside a domain parser | `ConnectorError(reason=INVALID_REQUEST)` — raised by the domain parser. |

---

## Registration

The `build_webhook_handlers` builder is registered separately from the connector class:

```python
# __init__.py
from lens.factory import ConnectorFactory
from <psp>.connector import <Psp>Connector
from <psp>.webhooks import build_webhook_handlers

ConnectorFactory.register("<psp>", <Psp>Connector)
ConnectorFactory.register_webhook("<psp>", build_webhook_handlers)
```

Both calls are required; a package that only calls `register` but not `register_webhook` will
fail the public-surface rubric check.

---

## Domain event field names — do NOT cross them

`PaymentWebhookEvent` and `MandateWebhookEvent` have **different** raw-payload field names
and `occurred_at` presence:

| Field | `PaymentWebhookEvent` | `MandateWebhookEvent` |
|---|---|---|
| raw dict field | `raw_payload` | `raw` |
| `occurred_at` | **does NOT exist** | **present** (`datetime`) |

```python
# CORRECT — PaymentWebhookEvent:
PaymentWebhookEvent(
    event_type=…, psp_event_id=…, psp_order_id=…,
    raw_payload={"key": "val"},   # ← raw_payload
)

# CORRECT — MandateWebhookEvent:
MandateWebhookEvent(
    event_type=…, psp_mandate_ref=…, psp_event_id=…,
    occurred_at=datetime(…),      # ← occurred_at IS present here
    raw={"key": "val"},           # ← raw (NOT raw_payload)
)
```

```python
# WRONG — do not mix:
PaymentWebhookEvent(occurred_at=…)    # ← field does not exist
PaymentWebhookEvent(raw=…)            # ← use raw_payload instead
MandateWebhookEvent(raw_payload=…)    # ← use raw instead
```

---

## Rules

- **Signature verification is constant-time.** Use `hmac.compare_digest` in `core/auth.py`.
- **`raw_payload` argument is `bytes`, not `str`.** Do not `.decode()` before verifying —
  signatures cover the byte sequence.
- **Headers come in as `dict[str, str]`** with the casing the PSP sent. Do not assume the
  framework normalized it; look up the signature header by its documented casing.
- **The `verify` callable closes over `config` at registration time.** This means signature
  secrets are resolved from `ConnectorConfig` when the router is first created, not globally.
- **Never log raw payload contents directly.** Use structlog with `Maskable` discipline.
- **Domain parsers receive already-verified bytes.** They do not need to re-verify the
  signature; the `WebhookRouter` already did.
- **`PaymentWebhookEvent.raw_payload` — not `raw`, not `raw_event`.**
- **`MandateWebhookEvent.raw` — not `raw_payload`.**
- **`occurred_at` only on `MandateWebhookEvent`** — do not add it to `PaymentWebhookEvent`.
