# Pattern: _parse_mandate_webhook (mandate webhook parser)

Mandate webhooks land at the shared `WebhookRouter` — they are **not** parsed by a connector
method. The connector owns only the domain parser function
`_parse_mandate_webhook(raw: bytes) -> MandateWebhookEvent`, which receives already-verified
bytes from the router. See `../python/webhook_handling.md` for the full router / registration
architecture.

## Domain types involved

- Output: `MandateWebhookEvent` (from `lens.domain_types`)
- Embedded for debit events: `MandateDebitOutcome` (from `lens.domain_types`)
- Event enum: `WebhookEventType` (from `lens.enums`) — mandate members:
  `MANDATE_AUTHORIZED`, `MANDATE_REJECTED`, `MANDATE_PAUSED`, `MANDATE_RESUMED`,
  `MANDATE_CANCELLED`, `MANDATE_REVOKED`, `MANDATE_SUSPENDED`, `MANDATE_EXPIRED`,
  `MANDATE_COMPLETED`, `MANDATE_DEBIT_SUCCESS`, `MANDATE_DEBIT_FAILED`,
  `MANDATE_DEBIT_NOTIFIED`, `MANDATE_EXPIRING_SOON`.

## Function signature (in `subscriptions/webhooks.py`)

```python
def _parse_mandate_webhook(raw: bytes) -> MandateWebhookEvent:
    ...
```

`raw` is already-verified bytes — do **not** re-verify the signature here.

## Implementation skeleton

```python
import json
from pydantic import ValidationError
from lens.common import ConnectorError
from lens.domain_types import MandateWebhookEvent, MandateDebitOutcome
from lens.enums import ConnectorErrorReason, WebhookEventType, MandateDebitStatus

# Per-PSP event→WebhookEventType map — fill from connector_docs/<psp>.md §event-mapping.
_EVENT_MAP: dict[str, WebhookEventType] = {
    # PSP event string    : WebhookEventType member
    # e.g. "<PSP_EVENT_TYPE>": WebhookEventType.MANDATE_AUTHORIZED,
    # ...
}


def _parse_mandate_webhook(raw: bytes) -> MandateWebhookEvent:
    # 1. Parse the raw bytes into the PSP's wire model.
    try:
        psp_event = <Psp>MandateWebhookEvent.model_validate_json(raw)
    except (ValidationError, ValueError) as e:
        raise ConnectorError(
            reason=ConnectorErrorReason.INVALID_REQUEST,
            psp_message=str(e),
        ) from e

    # 2. Map the PSP event type to a WebhookEventType.
    event_type = _EVENT_MAP.get(psp_event.event_type)
    if event_type is None:
        # Unknown event type — log and fall back to a benign value.
        # The router will still deliver it; Orbit decides whether to act on it.
        import structlog
        structlog.get_logger().warning(
            "unknown_mandate_webhook_event_type",
            psp_event_type=psp_event.event_type,
        )
        event_type = WebhookEventType.MANDATE_AUTHORIZED  # nearest-known fallback

    # 3. Populate the MandateDebitOutcome for debit events.
    debit: MandateDebitOutcome | None = None
    if event_type in (
        WebhookEventType.MANDATE_DEBIT_SUCCESS,
        WebhookEventType.MANDATE_DEBIT_FAILED,
        WebhookEventType.MANDATE_DEBIT_NOTIFIED,
    ):
        debit = _to_debit_outcome(psp_event)

    # 4. Build and return MandateWebhookEvent.
    return MandateWebhookEvent(
        event_type=event_type,
        # psp_mandate_ref MUST equal create_subscription's psp_mandate_ref for the same
        # subscription: use the merchant subscription id (the /subscriptions/{id} path key),
        # NEVER the PSP's internal id (e.g. cf_* / psp_* ids). Apply consistently across
        # ALL branches of this function. See CORE RULE in pattern_create_subscription.md.
        psp_mandate_ref=psp_event.<psp_subscription_id_field>,   # merchant id, same as create
        psp_event_id=psp_event.<psp_event_id_field>,
        occurred_at=psp_event.<event_time_field>,
        mandate_status=_map_mandate_status(psp_event),  # None if absent from this event
        debit=debit,
        raw=psp_event.model_dump(),
    )


def _to_debit_outcome(psp_event: <Psp>MandateWebhookEvent) -> MandateDebitOutcome:
    payment = psp_event.<payment_data_field>
    status, failure_code = map_debit_status(payment.payment_status)  # status_map.py
    return MandateDebitOutcome(
        psp_debit_id=payment.<psp_payment_id_field>,
        # Same merchant subscription id as in _parse_mandate_webhook above — NEVER internal id.
        psp_mandate_ref=psp_event.<psp_subscription_id_field>,   # merchant id, NOT internal id
        status=status,
        amount=Amount(
            minor_units=int(Decimal(payment.payment_amount) * 100),
            currency=Currency(payment.payment_currency),
        ),
        failure_code=failure_code,
        occurred_at=payment.<payment_time_field>,
        psp_attempt=payment.<retry_attempts_field>,   # None if not exposed
    )
```

## Realized rail (auth-success only)

On the PSP's mandate-authorized event, **when the authorization succeeded**, populate the three
optional realized-rail fields on `MandateWebhookEvent`:

- `realized_rail: MandateRail | None` — the rail that the customer actually completed
  authorization on (mapped from the PSP's payment-group via `map_payment_group_to_rail`; see
  `status_mapping.md` §many→few + `connector_docs/<psp>.md` §realized-rail).
- `authorization_reference: str | None` — the PSP's authorization identifier from its
  authorization block (wire key in `connector_docs/<psp>.md`).
- `payment_group: str | None` — the raw PSP payment-group string, preserved alongside the
  normalized `realized_rail` (the enum is coarser than the raw value).

**Gate strictly on the PSP's auth-success signal** (e.g. the event's `payment_type == "AUTH"`
and `payment_status == "SUCCESS"` combination — exact field names and values in
`connector_docs/<psp>.md`). **Null all three fields on failure even if the authorization block
is present in the payload.** Never infer a rail from a card-expiry / debit-notified / reminder
event — those have no authorization_details block.

Implementation note: read the PSP's authorization block from the event payload. Coerce all dict
reads with `isinstance` checks (no `Any` leaks). The wire key name for the authorization block
may differ between the webhook and the sync response (see `pattern_sync_subscription.md` and
`connector_docs/<psp>.md` for each path's own key).

```python
# Pseudocode — gate on auth-success before populating:
if psp_event.payment_type == "AUTH" and psp_event.payment_status == "SUCCESS":
    auth_block = psp_event.<authorization_block_field>    # wire key from connector_docs
    if auth_block is not None and isinstance(auth_block, dict):
        raw_group = auth_block.get("<payment_group_field>")  # wire key from connector_docs
        payment_group: str | None = raw_group if isinstance(raw_group, str) else None
        realized_rail = map_payment_group_to_rail(payment_group)
        authorization_reference = ...  # auth id wire key from connector_docs
    else:
        payment_group = None
        realized_rail = None
        authorization_reference = None
else:
    # Auth failed, or non-auth event: null all three unconditionally.
    payment_group = None
    realized_rail = None
    authorization_reference = None
```

### Required tests (realized rail)

- **AUTH-SUCCESS + known group** → `realized_rail` populated, `authorization_reference`
  populated, `payment_group` equals the raw string.
- **AUTH-FAILED with `payment_group` present in body** → all three fields are `None`
  (the gotcha: the group may be present even on failure; only SUCCESS sets the fields).
- **Non-auth event (e.g. expiry-reminder)** → all three fields are `None` (no auth block
  present; never synthesize a rail from a reminder event).
- **AUTH-SUCCESS with no authorization block** → all three fields are `None` (absent block
  treated the same as failure).

## Per-PSP event → WebhookEventType table

The `_EVENT_MAP` dict is the sole place where PSP event strings are mapped. Fill it
entirely from `connector_docs/<psp>.md` §event-mapping. Do **not** inline partial mappings
elsewhere. Every event row in that spec must appear in this dict (use `connector_docs/<psp>.md`
as the source of truth for the complete list).

Example shape (fill with actual values from the PSP doc):

```python
_EVENT_MAP = {
    "<SUBSCRIPTION_ACTIVATED>":   WebhookEventType.MANDATE_AUTHORIZED,
    "<SUBSCRIPTION_AUTH_FAILED>": WebhookEventType.MANDATE_REJECTED,
    "<SUBSCRIPTION_PAUSED>":      WebhookEventType.MANDATE_PAUSED,
    "<SUBSCRIPTION_CANCELLED>":   WebhookEventType.MANDATE_CANCELLED,
    "<SUBSCRIPTION_COMPLETED>":   WebhookEventType.MANDATE_COMPLETED,
    "<SUBSCRIPTION_PAYMENT_SUCCESS>": WebhookEventType.MANDATE_DEBIT_SUCCESS,
    "<SUBSCRIPTION_PAYMENT_FAILED>":  WebhookEventType.MANDATE_DEBIT_FAILED,
    "<SUBSCRIPTION_PAYMENT_NOTIFICATION_INITIATED>": WebhookEventType.MANDATE_DEBIT_NOTIFIED,
    "<SUBSCRIPTION_CARD_EXPIRY_REMINDER>": WebhookEventType.MANDATE_EXPIRING_SOON,
    # ... add all rows from connector_docs/<psp>.md
}
```

## Periodic-mode finality rule

Periodic mode has **no `*_FAILED_FINAL` event**. There is no `MANDATE_DEBIT_FAILED_FINAL` in
`WebhookEventType`. Finality for periodic mode is determined by Orbit when the mandate enters
`MANDATE_SUSPENDED` **and** the debit outcome carries a non-zero `psp_attempt` counter —
not by a separate final-failure event. Do **not** invent a custom status or add an extra
`*_FINAL` variant.

## Errors to surface

| Cause | Raise |
|---|---|
| Payload not valid JSON / fails wire-model validation | `ConnectorError(INVALID_REQUEST, psp_message=str(e))` |
| Unknown event type | Log a warning; return with a benign fallback `event_type` — do **not** raise |

## Required tests

`tests/test_mandate_webhook.py` (package-local; Grace relocates `tests/` after generation):

- **MANDATE_AUTHORIZED event** — build a valid signed fixture; call through
  `WebhookRouter.handle`; assert `event_type == MANDATE_AUTHORIZED` and
  `psp_mandate_ref` populated.
- **MANDATE_DEBIT_SUCCESS event** — assert `debit.status == MandateDebitStatus.SUCCESS`,
  `debit.amount` matches, `debit.failure_code is None`.
- **MANDATE_DEBIT_FAILED event** — assert `debit.status == MandateDebitStatus.FAILED` and
  `debit.failure_code` is a non-None `PaymentFailureCode` from `status_map.py`.
- **MANDATE_DEBIT_NOTIFIED event** — assert `event_type == MANDATE_DEBIT_NOTIFIED` and
  `debit.status == MandateDebitStatus.PENDING`.
- **MANDATE_EXPIRING_SOON event** — assert `event_type == MANDATE_EXPIRING_SOON`, `debit is None`.
- **Unknown event type** — payload carries an unrecognised event string; assert **no exception**
  is raised and a non-None `event_type` is returned.
- **Malformed JSON** — pass bytes that are not valid JSON; assert
  `ConnectorError(reason=INVALID_REQUEST)`.

## Pitfalls

- **Do not re-verify the signature here.** `raw` has already been verified by the
  `WebhookRouter`. Calling `verify_signature` again is wasteful and semantically wrong.
- **Unknown event types must not raise.** The router has already committed the request; raising
  here would drop the message. Log and return a fallback event type.
- **The `_EVENT_MAP` must be complete.** If a PSP event is absent from the map, Orbit silently
  receives the fallback type. Audit the map against `connector_docs/<psp>.md` regularly.
- **Periodic finality is `MANDATE_SUSPENDED` + `psp_attempt`, not a `*_FAILED_FINAL` event.**
  Do not fabricate a custom terminal event.
- **`psp_attempt` comes from the PSP's retry counter field** (not Orbit's). If the PSP exposes
  it on the payment data, map it; otherwise pass `None`.
- **`mandate_status` may not be present** on every event — some PSPs include it only on
  lifecycle events (AUTHORIZED, PAUSED, CANCELLED) but not on debit events. Always handle
  `None` for `mandate_status`.
- **`raw` (not `raw_payload`) — `MandateWebhookEvent` uses `raw: dict[str, Any]`.** The
  payment counterpart (`PaymentWebhookEvent`) uses `raw_payload`. Never swap them; pydantic
  `extra="forbid"` will raise a `ValidationError` at construction time.
- **`occurred_at` is present on `MandateWebhookEvent`** (it is a required field). The payment
  counterpart (`PaymentWebhookEvent`) does NOT have `occurred_at`. Do not omit it here.
