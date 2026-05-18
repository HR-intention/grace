# Pattern: UPI payment method (Authorize, Python)

UPI is the primary payment rail in India. Every Indian connector MUST support it.

## 🎯 Quick Start

Extends `to_authorize_request` (in `transformers.py`) to handle `UpiData` payment methods.

Two sub-flows:
- **UPI Collect** — customer's VPA is provided; PSP pushes a payment request to their UPI app; status arrives via webhook
- **UPI Intent** — PSP returns a deep link (`upi://pay?...`); customer's UPI app opens; status arrives via webhook

Placeholders: `{Connector}`, `{connector}`, `{upi_endpoint_field}` (PSP-specific JSON field name for VPA).

## 📋 Prerequisites

Authorize flow (per `../../../../shared/flows.md`). UPI is a payment-method variant of Authorize.

## 🏗️ Template

Extend the connector's `_payment_method_block` and `_pm_type` helpers:

```python
from connector_service.domain_types import RedirectionData, UpiData, UpiFlowType


def _payment_method_block(pm) -> dict:
    if isinstance(pm, UpiData):
        if pm.upi_flow == UpiFlowType.COLLECT:
            if not pm.vpa:
                raise ValueError("VPA required for UPI Collect")
            return {"upi": {"{upi_endpoint_field}": pm.vpa, "flow": "collect"}}
        elif pm.upi_flow == UpiFlowType.INTENT:
            return {"upi": {"flow": "intent"}}
        else:
            raise NotImplementedError(f"UPI flow {pm.upi_flow} not supported")
    # ... fall through to other PMs ...
```

And in `from_authorize_response`, populate `redirection_data` for UPI Intent:

```python
def from_authorize_response(resp: {Connector}AuthorizeResponse) -> AuthorizeResponse:
    redirection = None
    if resp.upi_intent_url:  # PSP-specific field name from tech spec
        redirection = RedirectionData(
            method="INTENT",
            url=resp.upi_intent_url,  # deep link like upi://pay?pa=...
        )
    return AuthorizeResponse(
        connector_payment_id=resp.id,
        status=_map_status(resp.status),
        redirection_data=redirection,
        raw_response=resp.model_dump(),
    )
```

For UPI Collect, no `redirection_data` is set; the customer's UPI app receives a push notification from the PSP. The connector returns `AttemptStatus.PENDING`; the eventual `CHARGED` or `FAILURE` status arrives via `incoming_webhook` (see [`../../../pattern_IncomingWebhook_flow.md`](../../../pattern_IncomingWebhook_flow.md)).

## 🧪 Testing Strategy

```python
@pytest.mark.integration
def test_authorize_upi_collect(client):
    response = client.post(
        "/v1/payments/authorize",
        headers={"Authorization": "Bearer test-key"},
        json={
            "connector_name": "{connector}",
            "request_id": "test-upi-collect",
            "request": {
                "amount": {"minor_units": 100, "currency": "INR"},
                "payment_method": {
                    "upi_flow": "collect",
                    "vpa": "test@upi",
                },
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"


@pytest.mark.integration
def test_authorize_upi_intent(client):
    response = client.post(
        "/v1/payments/authorize",
        headers={"Authorization": "Bearer test-key"},
        json={
            "connector_name": "{connector}",
            "request_id": "test-upi-intent",
            "request": {
                "amount": {"minor_units": 100, "currency": "INR"},
                "payment_method": {"upi_flow": "intent"},
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["response"]["redirection_data"]["method"] == "INTENT"
    assert body["response"]["redirection_data"]["url"].startswith("upi://")
```

## ✅ Validation Checklist

- [ ] Both `UpiFlowType.COLLECT` and `UpiFlowType.INTENT` are handled.
- [ ] Collect without `vpa` raises a clear error.
- [ ] Intent returns `RedirectionData(method="INTENT", url=upi://...)`.
- [ ] Status for both starts at `PENDING` — final status arrives via webhook.
- [ ] VPA values are not logged in plaintext (mask via `mask_vpa` or use field-name `vpa` in structlog kwargs so the masking processor catches it).
