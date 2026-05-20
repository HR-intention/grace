# Webhook handling

`handle_webhook` verifies the PSP's signature on a raw payload and parses it into a `WebhookEvent`. Dedup is **Orbit's** job — Lens just verifies + parses.

## Step list

1. **Verify the signature** using a helper from `auth.py` (e.g., `verify_signature(config, raw_payload, headers)`). On failure, raise `ConnectorError(reason=ConnectorErrorReason.WEBHOOK_SIGNATURE_FAILED)`. No exceptions.

2. **Parse the raw payload as JSON** into a Pydantic model from `models.py` (e.g., `<Psp>WebhookEvent.model_validate_json(raw_payload)`). If parsing fails, raise `ConnectorError(reason=ConnectorErrorReason.INVALID_REQUEST, psp_message=str(e))`.

3. **Branch on event type:**
   - `PAYMENT_*` events: populate `WebhookEvent.attempt: PaymentAttempt` from the payment data (use `status_map.py` for the status translation).
   - `REFUND_*` events: populate `WebhookEvent.refund: RefundEvent`.
   - `ORDER_EXPIRED`: neither attempt nor refund populated.

4. **Return** `WebhookEvent(event_type=..., psp_event_id=<PSP event id>, psp_order_id=<if available>, attempt=..., refund=..., raw_payload=psp_event.model_dump())`.

5. **Unknown event types:** log a warning (`structlog.warning("unknown_webhook_event_type", value=...)`) and return a `WebhookEvent` with the closest known `event_type` value, or — if nothing close exists — let it fall through to the caller (`event_type` set to the most generic value; Orbit decides what to do). Don't raise on unknown types.

## Reference pattern (Cashfree-shaped)

```python
async def handle_webhook(self, raw_payload: bytes, headers: dict[str, str]) -> WebhookEvent:
    if not verify_signature(self._config, raw_payload, headers):
        raise ConnectorError(reason=ConnectorErrorReason.WEBHOOK_SIGNATURE_FAILED)

    try:
        psp_event = CashfreeWebhookEvent.model_validate_json(raw_payload)
    except ValidationError as e:
        raise ConnectorError(
            reason=ConnectorErrorReason.INVALID_REQUEST,
            psp_message=str(e),
        ) from e

    if psp_event.type.startswith("PAYMENT_"):
        attempt = _payment_to_attempt(psp_event.data.payment)
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
    _log.warning("unknown_webhook_event_type", value=psp_event.type)
    return WebhookEvent(
        event_type=WebhookEventType.PAYMENT_INITIATED,   # closest-known fallback
        psp_event_id=psp_event.event_id,
        psp_order_id=None,
        raw_payload=psp_event.model_dump(),
    )
```

## Rules

- **Signature verification is constant-time.** Use `hmac.compare_digest`.
- **`raw_payload` argument is `bytes`, not `str`.** Don't `.decode()` before verifying — signatures cover the byte sequence.
- **Headers come in as `dict[str, str]`** with the casing the PSP sent. Look up the signature header (`x-cashfree-signature`, `x-razorpay-signature`, etc.) without assuming the framework normalized it.
- **`raw_payload` in `WebhookEvent` is the parsed dict.** Use `psp_event.model_dump()`. Do not stash the raw bytes there.
- **Never log raw payload contents directly.** Logging is via structlog with `Maskable` discipline; the `raw` dict is debug-only.
