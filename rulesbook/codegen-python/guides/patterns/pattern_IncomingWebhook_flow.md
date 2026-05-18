# Pattern: IncomingWebhook flow (Python)

## 🎯 Quick Start

Implements `{Connector}.incoming_webhook(raw_payload: bytes, headers: dict[str, str]) -> WebhookEvent`.

Webhooks are how UPI payment status reaches us — PSync polling is too slow for production UPI. Every Indian PSP webhook is at-least-once, so deduplication is required.

Placeholders: `{Connector}`, `{connector}`, `{signature_header_name}` (e.g., `x-razorpay-signature`), `{event_id_field}` (e.g., `event.id` or `data.id` per the tech spec).

## 📋 Prerequisites

PSync (per `../../../shared/flows.md`). Conceptually the webhook delivers the same status PSync would fetch, just push-style.

## 🏗️ Template

In `connector_service/connectors/{connector}/connector.py`, add the webhook handler:

```python
import hmac
import hashlib
import json

from connector_service.domain_types import ConnectorError, WebhookEvent


class {Connector}(BaseConnector):
    # ... other methods ...

    async def incoming_webhook(
        self, raw_payload: bytes, headers: dict[str, str]
    ) -> WebhookEvent:
        # Step 1: Signature verification
        received_sig = headers.get("{signature_header_name}", "")
        expected_sig = hmac.new(
            self.auth.webhook_secret.encode(),
            raw_payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(received_sig, expected_sig):
            raise ConnectorError("webhook signature mismatch", retryable=False)

        # Step 2: Parse + extract event_id
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as e:
            raise ConnectorError(f"webhook payload not JSON: {e}", retryable=False)

        event_id = payload.get("{event_id_field}")
        if not event_id:
            raise ConnectorError("webhook missing event_id", retryable=False)

        # Step 3: Dedup
        # Note: dedup_store is available via FastAPI app.state but the connector body
        # doesn't have direct access to it. The router passes the dedup_store reference
        # via a contextvar set by the lifespan. Plan E's Razorpay implementation
        # wires this through.
        # For now, the connector returns WebhookEvent.duplicate(...) ONLY if it has
        # internal knowledge of duplicates (rare). The dedup check is handled by
        # the router layer.

        # Step 4: Normalize to WebhookEvent
        event_type = payload.get("event", "unknown")
        return WebhookEvent(
            connector_name="{connector}",
            event_id=event_id,
            event_type=event_type,
            payload=payload,
        )
```

The router (`api/routers/webhooks.py`) is responsible for invoking the dedup store before returning the result. Generated connectors should focus on signature + parse + normalize.

## 🧪 Testing Strategy

```python
import hmac
import hashlib
import json
import pytest


@pytest.mark.integration
def test_incoming_webhook_valid_signature(client):
    payload = {"event": "payment.captured", "{event_id_field}": "evt_test_123"}
    raw = json.dumps(payload).encode()
    sig = hmac.new(b"<webhook_secret_from_creds>", raw, hashlib.sha256).hexdigest()

    response = client.post(
        "/v1/webhooks/{connector}",
        headers={
            "Authorization": "Bearer test",
            "{signature_header_name}": sig,
            "Content-Type": "application/json",
        },
        content=raw,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["event_id"] == "evt_test_123"
    assert body["duplicate"] is False


@pytest.mark.integration
def test_incoming_webhook_invalid_signature_rejected(client):
    payload = {"event": "payment.captured", "id": "evt_test_456"}
    raw = json.dumps(payload).encode()

    response = client.post(
        "/v1/webhooks/{connector}",
        headers={
            "Authorization": "Bearer test",
            "{signature_header_name}": "wrong_signature",
            "Content-Type": "application/json",
        },
        content=raw,
    )
    assert response.status_code == 400
```

## ✅ Validation Checklist

- [ ] Signature verification uses `hmac.compare_digest` (constant-time) — NOT `==`.
- [ ] Missing or empty signature header → `ConnectorError`, NOT silent acceptance.
- [ ] JSON parse failure → `ConnectorError` with retryable=False (replaying won't help).
- [ ] Missing event_id → `ConnectorError`. Without an event_id we can't dedup, which means duplicate events cause double-processing.
- [ ] `mypy --strict` clean.
