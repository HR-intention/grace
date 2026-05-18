# Pattern: Wallet payment method (Authorize, Python)

## 🎯 Quick Start

Extends `to_authorize_request` to handle `WalletData` payment methods.

Wallets include Apple Pay, Google Pay, PayPal, Samsung Pay, Paytm, PhonePe. The PSP-specific request shape varies — most accept an opaque token from the wallet provider.

Placeholders: `{Connector}`, `{connector}`, `{wallet_token_field}` (per tech spec).

## 📋 Prerequisites

Authorize flow.

## 🏗️ Template

```python
from connector_service.domain_types import WalletData, WalletType


def _payment_method_block(pm) -> dict:
    if isinstance(pm, WalletData):
        return {
            "wallet": {
                "type": pm.wallet_type.value,  # "apple_pay", "google_pay", etc.
                "{wallet_token_field}": pm.token,
                **({"email": pm.email} if pm.email else {}),
                **({"phone": pm.phone} if pm.phone else {}),
            }
        }
    # ... fall through ...
```

Some wallets (Apple Pay, Google Pay) require additional cryptogram/network-token fields. Extend `WalletData` via a per-connector model in `transformers.py` if the PSP needs them — do NOT extend the shared `WalletData` in `connector-service-python/connector_service/domain_types/pm_models.py`.

## 🧪 Testing Strategy

```python
@pytest.mark.integration
def test_authorize_wallet_paytm(client):
    response = client.post(
        "/v1/payments/authorize",
        headers={"Authorization": "Bearer test-key"},
        json={
            "connector_name": "{connector}",
            "request_id": "test-wallet",
            "request": {
                "amount": {"minor_units": 1000, "currency": "INR"},
                "payment_method": {
                    "wallet_type": "paytm",
                    "phone": "9876543210",
                },
            },
        },
    )
    assert response.status_code == 200
```

## ✅ Validation Checklist

- [ ] Wallet type maps to the PSP's expected string (per tech spec).
- [ ] Token is required for Apple/Google Pay; phone is typical for Indian wallets (Paytm, PhonePe).
- [ ] Token values are not logged plaintext (the masker doesn't catch `token` by default; use field name `wallet_token` or mask manually).
