# Pattern: handle_webhook (incoming webhook)

`handle_webhook` is the verify-and-parse path for PSP webhooks. It runs on raw bytes (the payload as received) + the request headers (for the signature). It returns a `WebhookEvent` normalized to our domain shape. **Dedup is Orbit's job.** **Ledger updates are Orbit's job.** Lens just verifies and parses.

See `../python/webhook_handling.md` for the canonical step list; this file describes the per-PSP shape.

## Domain types involved

- Output: `WebhookEvent` (from `lens.domain_types`).
- Embedded per-event-type: `PaymentAttempt` (for `PAYMENT_*` events) or `RefundEvent` (for `REFUND_*` events).
- Event-type enum: `WebhookEventType` (locked).

## Method signature (in `connector.py`)

```python
async def handle_webhook(
    self, raw_payload: bytes, headers: dict[str, str]
) -> WebhookEvent:
    ...
```

## Implementation skeleton

```python
async def handle_webhook(self, raw_payload: bytes, headers: dict[str, str]) -> WebhookEvent:
    # 1. Verify signature. Constant-time compare via hmac.compare_digest in auth.py.
    if not verify_signature(self._config, raw_payload, headers):
        raise ConnectorError(reason=ConnectorErrorReason.WEBHOOK_SIGNATURE_FAILED)

    # 2. Parse the body.
    try:
        psp_event = <Psp>WebhookEvent.model_validate_json(raw_payload)
    except ValidationError as e:
        raise ConnectorError(
            reason=ConnectorErrorReason.INVALID_REQUEST,
            psp_message=str(e),
        ) from e

    # 3. Branch on event type.
    if psp_event.type.startswith("PAYMENT_"):
        attempt = _payment_to_attempt(psp_event.data.payment)  # status_map-aware
        return WebhookEvent(
            event_type=_map_event_type(psp_event.type),
            psp_event_id=psp_event.event_id,
            psp_order_id=psp_event.data.order.cf_order_id,
            attempt=attempt,
            raw_payload=psp_event.model_dump(),
        )
    if psp_event.type.startswith("REFUND_"):
        refund = _to_refund_event(psp_event.data.refund)
        return WebhookEvent(
            event_type=_map_event_type(psp_event.type),
            psp_event_id=psp_event.event_id,
            psp_order_id=psp_event.data.order.cf_order_id if psp_event.data.order else None,
            refund=refund,
            raw_payload=psp_event.model_dump(),
        )
    if psp_event.type == "ORDER_EXPIRED":
        return WebhookEvent(
            event_type=WebhookEventType.ORDER_EXPIRED,
            psp_event_id=psp_event.event_id,
            psp_order_id=psp_event.data.order.cf_order_id,
            raw_payload=psp_event.model_dump(),
        )

    # 4. Unknown event type — log + return a benign event Orbit can ignore.
    _log.warning("unknown_webhook_event_type", value=psp_event.type)
    return WebhookEvent(
        event_type=WebhookEventType.PAYMENT_INITIATED,   # closest-known fallback
        psp_event_id=psp_event.event_id,
        psp_order_id=None,
        raw_payload=psp_event.model_dump(),
    )
```

## Errors to surface

| Cause | Raise |
|---|---|
| Signature verification fails | `ConnectorError(WEBHOOK_SIGNATURE_FAILED)` — **always**, never silently |
| Payload not valid JSON / wrong shape | `ConnectorError(INVALID_REQUEST, psp_message=str(e))` |
| Anything else unexpected | `ConnectorError(INTERNAL)` |

## Tests

`tests/test_webhook.py`:

- **Signed PAYMENT_SUCCESS** — build a signed payload (use the auth helper to sign a known-good fixture); call `handle_webhook`; assert `event_type == PAYMENT_SUCCESS`, `attempt.status == SUCCESS`, `attempt.amount` populated.
- **Signed PAYMENT_FAILED** — same idea but failed; assert `attempt.status == FAILED` and `attempt.failure_code` populated (per the PSP's failure signal — `CARD_DECLINED`, `USER_DROPPED`, etc.).
- **Signed REFUND_SUCCESS** — assert `event_type == REFUND_SUCCESS`, `refund.status == SUCCESS`, `refund.refunded_amount` populated.
- **Tampered payload** — flip one byte after signing; assert `ConnectorError(reason=WEBHOOK_SIGNATURE_FAILED)`.
- (Optional) **Signed `USER_DROPPED`** — verifies the `status_map.py` mapping flows through into `attempt.failure_code == USER_DROPPED`.

## Notes

- The PSP signature header name varies (`x-webhook-signature`, `x-cashfree-signature`, `x-razorpay-signature`, etc.). The webhook header lookup is case-aware; respect what the PSP actually sends.
- Some PSPs sign `payload` directly; others sign `timestamp + "." + payload`; some sign with HMAC-SHA256, others SHA512. The `verify_signature` helper in `auth.py` knows the right scheme for *this* PSP. Document the algorithm in a comment on the helper.
- **Don't decode `raw_payload` before verifying.** Signatures cover the bytes as received.
- The `raw_payload` field of `WebhookEvent` holds the parsed dict (`psp_event.model_dump()`), not the raw bytes. Bytes can carry secrets; the parsed dict is safer for downstream debug.
- Unknown event types must not raise. Orbit needs to log/persist them; raising would drop the message.
