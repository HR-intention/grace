# Pattern: Card payment method (Authorize, Python)

## 🎯 Quick Start

Extends `to_authorize_request` to handle `CardData` payment methods.

Placeholders: `{Connector}`, `{connector}`, `{card_field_names}` (per tech spec — common variants: `card.number`, `card_number`, `card.pan`).

## 📋 Prerequisites

Authorize flow.

## 🏗️ Template

```python
from typing import Any
from connector_service.domain_types import CardData, PaymentMethodInput


def _payment_method_block(pm: PaymentMethodInput) -> dict[str, Any]:
    if isinstance(pm, CardData):
        return {
            "card": {
                "number": pm.card_number,
                "exp_month": pm.card_exp_month,
                "exp_year": pm.card_exp_year,
                "name": pm.card_holder_name,
                "cvv": pm.card_cvc,
                # Some PSPs require additional fields per the tech spec:
                # "issuer": pm.card_issuer,
            }
        }
    # ... fall through to other PMs ...
```

## 🧪 Testing Strategy

```python
@pytest.mark.integration
def test_authorize_card(client):
    response = client.post(
        "/v1/payments/authorize",
        headers={"Authorization": "Bearer test-key"},
        json={
            "connector_name": "{connector}",
            "request_id": "test-card",
            "request": {
                "amount": {"minor_units": 10000, "currency": "INR"},
                "payment_method": {
                    "card_number": "<sandbox card from tech spec>",
                    "card_exp_month": "12",
                    "card_exp_year": "2030",
                    "card_holder_name": "Test Customer",
                    "card_cvc": "123",
                },
            },
        },
    )
    assert response.status_code == 200
```

## ✅ Validation Checklist

- [ ] All five required fields (number, exp_month, exp_year, holder_name, cvc) are passed through.
- [ ] Card number is never logged unmasked. The structlog masker handles fields named `card_number`, `pan`, `card_pan`; ensure the connector logs using these key names.
- [ ] CVV is never logged at all (masker redacts to `***` unconditionally).
- [ ] 3DS / SCA flow: if the PSP returns a redirect URL for 3DS, surface it via `RedirectionData(method="POST", url=..., form_fields=...)`.
