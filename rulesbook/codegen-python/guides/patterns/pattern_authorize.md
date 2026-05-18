# Pattern: Authorize flow (Python)

## 🎯 Quick Start

Implements `{Connector}.authorize(data: PaymentData[AuthorizeRequest, AuthorizeResponse])`.

Placeholders:
- `{Connector}` — class name (e.g., `Razorpay`)
- `{connector}` — lowercase (e.g., `razorpay`)
- `{base_url}` — already on the class; you reference `self.base_url` indirectly via `self.client`
- `{authorize_endpoint}` — PSP authorize path (e.g., `/v1/orders` or `/payments/create`)
- `{Connector}AuthorizeRequest` / `{Connector}AuthorizeResponse` — PSP-specific Pydantic models you define in `transformers.py`

## 📋 Prerequisites

None — Authorize is the entry point for any new connector. All other flows depend on it.

See [`../../../shared/flows.md`](../../../shared/flows.md) for the full prerequisite DAG.

## 🏗️ Template

In `connector_service/connectors/{connector}/connector.py`:

```python
from connector_service.connectors._base import BaseConnector, connector_flow
from connector_service.connectors._registry import register_connector
from connector_service.domain_types import (
    AttemptStatus, AuthorizeRequest, AuthorizeResponse, Flow, PaymentData,
)

from .auth import {Connector}Auth
from .transformers import (
    {Connector}AuthorizeRequest, {Connector}AuthorizeResponse,
    to_authorize_request, from_authorize_response,
)


class {Connector}(BaseConnector):
    name = "{connector}"
    base_url = "{base_url}"
    AuthCls = {Connector}Auth

    @connector_flow(flow=Flow.AUTHORIZE)
    async def authorize(
        self, data: PaymentData[AuthorizeRequest, AuthorizeResponse]
    ) -> PaymentData[AuthorizeRequest, AuthorizeResponse]:
        psp_request: {Connector}AuthorizeRequest = to_authorize_request(data.request)
        http_response = await self.client.post(
            "{authorize_endpoint}",
            json=psp_request.model_dump(by_alias=True, exclude_none=True),
            headers={
                **self._auth_headers(),
                "Idempotency-Key": data.idempotency_key or "",
            },
        )
        http_response.raise_for_status()
        psp_response = {Connector}AuthorizeResponse.model_validate_json(http_response.text)
        mapped = _map_status(psp_response.status)
        data.response = from_authorize_response(psp_response, mapped)
        data.status = mapped
        return data

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.auth.api_key}"}


def _map_status(psp_status: str) -> AttemptStatus:
    # Fill in per the tech spec's "Status Mapping" section.
    # Every documented PSP status must have an entry — unmapped = critical quality issue.
    return {
        "created": AttemptStatus.PENDING,
        "authorized": AttemptStatus.AUTHORIZED,
        "captured": AttemptStatus.CHARGED,
        "failed": AttemptStatus.FAILURE,
        # ... add every status the tech spec lists
    }[psp_status]


register_connector("{connector}", {Connector})
```

In `connector_service/connectors/{connector}/transformers.py`:

```python
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field
from connector_service.domain_types import (
    AttemptStatus, AuthorizeRequest, AuthorizeResponse,
    CardData, PaymentMethodInput, UpiData, WalletData,
)


class {Connector}AuthorizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Fill in PSP-specific fields per the tech spec
    amount: int                          # PSP-side: minor units
    currency: str
    payment_method_type: str
    card: Optional[dict] = None          # nested per the tech spec
    upi: Optional[dict] = None
    # ... etc


class {Connector}AuthorizeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    status: str
    # ... whatever the PSP returns


def to_authorize_request(req: AuthorizeRequest) -> {Connector}AuthorizeRequest:
    # Map the domain request to PSP-specific shape
    pm_block = _payment_method_block(req.payment_method)
    return {Connector}AuthorizeRequest(
        amount=req.amount.minor_units,
        currency=req.amount.currency.value,
        payment_method_type=_pm_type(req.payment_method),
        **pm_block,
    )


def from_authorize_response(
    resp: {Connector}AuthorizeResponse, mapped_status: AttemptStatus
) -> AuthorizeResponse:
    return AuthorizeResponse(
        connector_payment_id=resp.id,
        status=mapped_status,
        raw_response=resp.model_dump(),
    )


def _payment_method_block(pm: PaymentMethodInput) -> dict[str, Any]:
    if isinstance(pm, CardData):
        return {"card": {"number": pm.card_number, "exp_month": pm.card_exp_month}}
    if isinstance(pm, UpiData):
        return {"upi": {"vpa": pm.vpa}} if pm.upi_flow.value == "collect" else {"upi": {}}
    if isinstance(pm, WalletData):
        return {"wallet": {"type": pm.wallet_type.value, "token": pm.token}}
    raise NotImplementedError(f"Payment method {type(pm).__name__} not supported")


def _pm_type(pm: PaymentMethodInput) -> str:
    if isinstance(pm, CardData): return "card"
    if isinstance(pm, UpiData): return "upi"
    if isinstance(pm, WalletData): return "wallet"
    raise NotImplementedError(f"Payment method {type(pm).__name__} not supported")
```

Refer to the per-PM patterns under `authorize/{card,wallet,upi}/` for payment-method-specific transformer logic.

## 🧪 Testing Strategy

Author `connector-service-python/tests/integration/test_{connector}.py`. The
`client` fixture is provided by `tests/conftest.py` — don't redefine it here.

```python
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_authorize_card(client: TestClient):
    response = client.post(
        "/v1/payments/authorize",
        headers={"Authorization": "Bearer test-key"},
        json={
            "connector_name": "{connector}",
            "request_id": "test-123",
            "request": {
                "amount": {"minor_units": 10000, "currency": "INR"},
                "payment_method": {
                    "card_number": "<test card from tech spec>",
                    "card_exp_month": "12",
                    "card_exp_year": "2030",
                    "card_holder_name": "Test Customer",
                    "card_cvc": "123",
                },
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("pending", "authorized", "charged")
    assert body["response"]["connector_payment_id"]
```

Requires valid sandbox `api_key` in `creds.json` under the `{connector}` entry. Tests are marked `@pytest.mark.integration` so they can be skipped in CI: `pytest -m "not integration"`.

## ✅ Validation Checklist

- [ ] `to_authorize_request` handles all 3 payment methods (Card, Wallet, UPI) — even if the connector only supports a subset (raise `NotImplementedError` for unsupported).
- [ ] `from_authorize_response` returns a fully-populated `AuthorizeResponse` (no `None` for fields the PSP returned).
- [ ] `_map_status` has an entry for EVERY status the tech spec documents. Unmapped statuses are a critical issue.
- [ ] Idempotency-Key header is sent (decorator provides the value via `data.idempotency_key`).
- [ ] PSP-specific Pydantic models use `ConfigDict(extra="forbid")`.
- [ ] No floats anywhere on monetary fields.
- [ ] `mypy --strict` clean on this file.
- [ ] Integration test passes (manually, with creds).
