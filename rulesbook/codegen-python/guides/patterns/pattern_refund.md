# Pattern: Refund flow (Python)

## 🎯 Quick Start

Implements `{Connector}.refund(data: PaymentData[RefundRequest, RefundResponse])`.

Refund returns funds to the customer from a previously-captured payment.
It produces a NEW `connector_refund_id` distinct from the `connector_payment_id`.
The request is monetary — `Idempotency-Key` is MANDATORY.

Placeholders:
- `{Connector}` — class name (e.g., `Razorpay`)
- `{connector}` — lowercase (e.g., `razorpay`)
- `{refund_endpoint}` — PSP refund path
  (e.g., `/payments/{connector_payment_id}/refund`, `/refunds`, or `/v1/orders/{connector_payment_id}/refunds`)
- `{Connector}RefundRequest` / `{Connector}RefundResponse` — PSP-specific Pydantic models

## 📋 Prerequisites

Capture — Refund typically requires the payment to be in CHARGED state.

For PSPs that support auth-and-capture-in-one (no separate Capture call), the
prerequisite collapses to Authorize. Note in the connector's tech spec which
mode applies; the generated `_map_status` for Authorize will mark the payment
CHARGED directly in that case.

See [`../../../shared/flows.md`](../../../shared/flows.md) for the full prerequisite DAG.

## 🏗️ Template

In `connector_service/connectors/{connector}/connector.py`:

```python
from connector_service.connectors._base import BaseConnector, connector_flow
from connector_service.connectors._registry import register_connector
from connector_service.domain_types import (
    Amount, Currency, Flow, PaymentData, RefundRequest, RefundResponse, RefundStatus,
)

from .transformers import (
    {Connector}RefundRequest, {Connector}RefundResponse,
    to_refund_request, from_refund_response,
)


class {Connector}(BaseConnector):
    # ... other flows defined elsewhere

    @connector_flow(flow=Flow.REFUND)
    async def refund(
        self, data: PaymentData[RefundRequest, RefundResponse]
    ) -> PaymentData[RefundRequest, RefundResponse]:
        connector_payment_id = data.request.connector_payment_id
        psp_request: {Connector}RefundRequest = to_refund_request(data.request)
        http_response = await self.client.post(
            "{refund_endpoint}".format(connector_payment_id=connector_payment_id),
            json=psp_request.model_dump(by_alias=True, exclude_none=True),
            headers={
                **self._auth_headers(),
                "Idempotency-Key": data.idempotency_key or "",
            },
        )
        http_response.raise_for_status()
        psp_response = {Connector}RefundResponse.model_validate_json(http_response.text)
        mapped = _map_status(psp_response.status)
        data.response = from_refund_response(psp_response, mapped)
        # data.status (envelope) is best-effort cross-flow consistency:
        data.status = None  # refund flows don't populate envelope-level status
        return data


def _map_status(psp_status: str) -> RefundStatus:
    # Fill in per the tech spec's "Refund Status Mapping" section.
    # Every documented refund status must have an entry — unmapped = critical quality issue.
    return {
        "pending": RefundStatus.PENDING,
        "processed": RefundStatus.SUCCESS,
        "succeeded": RefundStatus.SUCCESS,
        "failed": RefundStatus.FAILURE,
        "transaction_failed": RefundStatus.TRANSACTION_FAILURE,
        "manual_review": RefundStatus.MANUAL_REVIEW,
        # ... add every status the tech spec lists
    }[psp_status]
```

In `connector_service/connectors/{connector}/transformers.py`:

```python
from typing import Optional
from pydantic import BaseModel, ConfigDict
from connector_service.domain_types import (
    Amount, Currency, RefundRequest, RefundResponse, RefundStatus,
)


class {Connector}RefundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: int                          # minor units
    currency: str
    reason: Optional[str] = None         # some PSPs require, some accept notes


class {Connector}RefundResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str                              # NEW refund id, distinct from payment id
    status: str
    amount: int                          # minor units actually refunded
    currency: str


def to_refund_request(req: RefundRequest) -> {Connector}RefundRequest:
    return {Connector}RefundRequest(
        amount=req.refund_amount.minor_units,
        currency=req.refund_amount.currency.value,
        reason=req.refund_reason,
    )


def from_refund_response(
    resp: {Connector}RefundResponse, mapped_status: RefundStatus
) -> RefundResponse:
    return RefundResponse(
        connector_refund_id=resp.id,
        status=mapped_status,
        refund_amount=Amount(
            minor_units=resp.amount,
            currency=Currency(resp.currency),
        ),
        raw_response=resp.model_dump(),
    )
```

## 🧪 Testing Strategy

Author `connector-service-python/tests/integration/test_{connector}.py`. The
`client` fixture is provided by `tests/conftest.py` — don't redefine it here.

```python
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_refund(client: TestClient):
    # Pre-condition: a real connector_payment_id from a prior CAPTURED payment.
    response = client.post(
        "/v1/payments/refund",
        headers={"Authorization": "Bearer test-key"},
        json={
            "connector_name": "{connector}",
            "request_id": "test-refund-123",
            "request": {
                "connector_payment_id": "<id from prior capture>",
                "refund_amount": {"minor_units": 5000, "currency": "INR"},
                "refund_reason": "Customer requested",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    # Refund flows leave the envelope status None — read the typed RefundStatus off the response:
    assert body["response"]["status"] in (
        "pending", "success", "failure", "transaction_failure", "manual_review",
    )
    refund_id = body["response"]["connector_refund_id"]
    payment_id = "<id from prior capture>"
    assert refund_id and refund_id != payment_id  # MUST be distinct
    assert body["response"]["refund_amount"]["minor_units"] <= 5000
```

Requires valid sandbox `api_key` in `creds.json` under the `{connector}` entry. Tests are marked `@pytest.mark.integration` so they can be skipped in CI: `pytest -m "not integration"`.

## ✅ Validation Checklist

- [ ] `_map_status` has an entry for EVERY refund status the tech spec documents — including `PENDING`, `SUCCESS`, `FAILURE`, `TRANSACTION_FAILURE`, `MANUAL_REVIEW`. Unmapped statuses are a critical issue.
- [ ] `Idempotency-Key` header IS sent — refund is monetary and replays must be safe.
- [ ] `connector_refund_id` returned is distinct from `connector_payment_id`. If the PSP reuses the payment id as the refund id, document it loudly in the connector README and still surface it via `connector_refund_id`.
- [ ] `refund_amount.minor_units` returned is ≤ the original captured amount. Partial refunds are allowed; over-refunds are a bug.
- [ ] PSP-specific Pydantic models use `ConfigDict(extra="forbid")`.
- [ ] No floats anywhere on monetary fields.
- [ ] `mypy --strict` clean on this file.
- [ ] Integration test passes (manually, with creds).
