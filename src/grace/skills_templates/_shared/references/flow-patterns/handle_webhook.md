# Flow pattern: `handle_webhook`

Verifies the PSP's signature on a raw payload and parses it into a `WebhookEvent`. Dedup is Orbit's job — Lens just verifies and parses.

## Locked signature

```python
async def handle_webhook(
    self, raw_payload: bytes, headers: dict[str, str]
) -> WebhookEvent:
```

## Step list

1. **Verify signature** via `auth.verify_signature(config, raw_payload, headers)`. Use `hmac.compare_digest` for constant-time comparison.
2. **On signature failure**: `raise ConnectorError(reason=ConnectorErrorReason.WEBHOOK_SIGNATURE_FAILED)`. Never `ValueError`. Never a benign return.
3. **Parse body** as JSON via `<Psp>WebhookEvent.model_validate_json(raw_payload)`. On parse failure: `raise ConnectorError(reason=INVALID_REQUEST, psp_message=str(e))`.
4. **Branch on event type**:
   - `PAYMENT_*` → populate `WebhookEvent.attempt: PaymentAttempt`.
   - `REFUND_*` → populate `WebhookEvent.refund: RefundEvent`.
   - `ORDER_EXPIRED` → neither.
   - Unknown → log warning, return `WebhookEvent` with closest-known `event_type` (fallback `PAYMENT_INITIATED`). Don't raise.

## Skeleton

```python
async def handle_webhook(self, raw_payload: bytes, headers: dict[str, str]) -> WebhookEvent:
    if not verify_signature(self._config, raw_payload, headers):
        raise ConnectorError(reason=ConnectorErrorReason.WEBHOOK_SIGNATURE_FAILED)

    try:
        psp_event = <Psp>WebhookEvent.model_validate_json(raw_payload)
    except ValidationError as e:
        raise ConnectorError(
            reason=ConnectorErrorReason.INVALID_REQUEST,
            psp_message=str(e),
        ) from e

    if psp_event.type.startswith("PAYMENT_"):
        return WebhookEvent(
            event_type=_map_event_type(psp_event.type),
            psp_event_id=psp_event.event_id,
            psp_order_id=psp_event.data.order.cf_order_id,
            attempt=_payment_to_attempt(psp_event.data.payment),
            raw_payload=psp_event.model_dump(),
        )
    if psp_event.type.startswith("REFUND_"):
        return WebhookEvent(
            event_type=_map_event_type(psp_event.type),
            psp_event_id=psp_event.event_id,
            psp_order_id=psp_event.data.order.cf_order_id if psp_event.data.order else None,
            refund=_to_refund_event(psp_event.data.refund),
            raw_payload=psp_event.model_dump(),
        )
    if psp_event.type == "ORDER_EXPIRED":
        return WebhookEvent(
            event_type=WebhookEventType.ORDER_EXPIRED,
            psp_event_id=psp_event.event_id,
            psp_order_id=psp_event.data.order.cf_order_id,
            raw_payload=psp_event.model_dump(),
        )

    _log.warning("unknown_webhook_event_type", value=psp_event.type)
    return WebhookEvent(
        event_type=WebhookEventType.PAYMENT_INITIATED,
        psp_event_id=psp_event.event_id,
        psp_order_id=None,
        raw_payload=psp_event.model_dump(),
    )
```

## Required tests in `tests/test_webhook.py`

1. **Signed PAYMENT_SUCCESS**: build a valid signed payload; assert `event_type == PAYMENT_SUCCESS`, `attempt.status == SUCCESS`.
2. **Signed PAYMENT_FAILED**: assert `attempt.status == FAILED` and `attempt.failure_code` populated (e.g. `CARD_DECLINED` or `USER_DROPPED`).
3. **Signed REFUND_SUCCESS**: assert `event_type == REFUND_SUCCESS`, `refund.status == SUCCESS`.
4. **Tampered payload**: flip one byte after signing; assert `ConnectorError(reason=WEBHOOK_SIGNATURE_FAILED)`.

## Pitfalls

- ❌ `raise ValueError("bad signature")` — rubric checks for the literal `WEBHOOK_SIGNATURE_FAILED`. Bare exceptions score 0.
- ❌ `.decode()` on `raw_payload` before verifying. Signatures cover the bytes as received.
- ❌ Storing the raw bytes in `WebhookEvent.raw_payload`. That field is the *parsed* dict (`psp_event.model_dump()`).
- ❌ Raising on unknown event types. Return a benign event with the closest-known `event_type`; Orbit decides.
- ❌ Hardcoding the signature header name as `X-Webhook-Signature`. Look up case-insensitively — frameworks normalize differently. (Cashfree: `x-webhook-signature` + `x-webhook-timestamp`. Razorpay: `x-razorpay-signature`. Each PSP has its own.)
