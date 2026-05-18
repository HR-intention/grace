# Pattern: Capture flow (Python)

## 🎯 Quick Start

Implements `{Connector}.capture(data: PaymentData[CaptureRequest, CaptureResponse])`.

Capture moves an authorized-but-not-yet-charged payment into the CHARGED state.
The request is monetary — `Idempotency-Key` is MANDATORY.

Placeholders:
- `{Connector}` — class name (e.g., `Razorpay`)
- `{connector}` — lowercase (e.g., `razorpay`)
- `{capture_endpoint}` — PSP capture path, parameterized by `connector_payment_id`
  (e.g., `/payments/{connector_payment_id}/capture` or `/v1/orders/{connector_payment_id}/capture`)
- `{Connector}CaptureRequest` / `{Connector}CaptureResponse` — PSP-specific Pydantic models

## 📋 Prerequisites

Authorize — Capture requires a prior authorization (the `connector_payment_id` must already exist).

See [`../../../shared/flows.md`](../../../shared/flows.md) for the full prerequisite DAG.

## 🏗️ Template

In `connector_service/connectors/{connector}/connector.py`:

```python
from connector_service.connectors._base import BaseConnector, connector_flow
from connector_service.connectors._registry import register_connector
from connector_service.domain_types import (
    Amount, AttemptStatus, CaptureRequest, CaptureResponse, Currency, Flow, PaymentData,
)

from .transformers import (
    {Connector}CaptureRequest, {Connector}CaptureResponse,
    to_capture_request, from_capture_response,
)


class {Connector}(BaseConnector):
    # ... other flows defined elsewhere

    @connector_flow(flow=Flow.CAPTURE)
    async def capture(
        self, data: PaymentData[CaptureRequest, CaptureResponse]
    ) -> PaymentData[CaptureRequest, CaptureResponse]:
        connector_payment_id = data.request.connector_payment_id
        psp_request: {Connector}CaptureRequest = to_capture_request(data.request)
        http_response = await self.client.post(
            f"{capture_endpoint}".format(connector_payment_id=connector_payment_id),
            json=psp_request.model_dump(by_alias=True, exclude_none=True),
            headers={
                **self._auth_headers(),
                "Idempotency-Key": data.idempotency_key or "",
            },
        )
        http_response.raise_for_status()
        psp_response = {Connector}CaptureResponse.model_validate_json(http_response.text)
        data.response = from_capture_response(psp_response, data.request)
        data.status = _map_status(psp_response.status)
        return data


def _map_status(psp_status: str) -> AttemptStatus:
    # Fill in per the tech spec's "Status Mapping" section.
    # Capture results are usually CHARGED / PARTIAL_CHARGED / FAILURE, but check the spec.
    return {
        "captured": AttemptStatus.CHARGED,
        "partially_captured": AttemptStatus.PARTIAL_CHARGED,
        "failed": AttemptStatus.FAILURE,
        # ... add every status the tech spec lists
    }[psp_status]
```

In `connector_service/connectors/{connector}/transformers.py`:

```python
from pydantic import BaseModel, ConfigDict
from connector_service.domain_types import (
    Amount, AttemptStatus, CaptureRequest, CaptureResponse, Currency,
)


class {Connector}CaptureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: int                          # minor units
    currency: str


class {Connector}CaptureResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    status: str
    amount_captured: int                 # minor units the PSP confirmed captured
    currency: str


def to_capture_request(req: CaptureRequest) -> {Connector}CaptureRequest:
    return {Connector}CaptureRequest(
        amount=req.amount_to_capture.minor_units,
        currency=req.amount_to_capture.currency.value,
    )


def from_capture_response(
    resp: {Connector}CaptureResponse, req: CaptureRequest
) -> CaptureResponse:
    return CaptureResponse(
        connector_payment_id=resp.id,
        status=AttemptStatus.CHARGED,  # decorator overrides with mapped value
        amount_captured=Amount(
            minor_units=resp.amount_captured,
            currency=Currency(resp.currency),
        ),
        raw_response=resp.model_dump(),
    )
```

## 🧪 Testing Strategy

Author `connector-service-python/tests/integration/test_{connector}.py`:

```python
import pytest
from fastapi.testclient import TestClient

from connector_service.api.server import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.integration
def test_capture(client):
    # Pre-condition: a real connector_payment_id from a prior authorize call
    # that left the payment in AUTHORIZED state.
    response = client.post(
        "/v1/payments/capture",
        headers={"Authorization": "Bearer test-key"},
        json={
            "connector_name": "{connector}",
            "request_id": "test-capture-123",
            "request": {
                "connector_payment_id": "<id from prior authorize>",
                "amount_to_capture": {"minor_units": 10000, "currency": "INR"},
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("charged", "partial_charged", "failure")
    assert body["response"]["connector_payment_id"] == "<id from prior authorize>"
    assert body["response"]["amount_captured"]["minor_units"] <= 10000
```

Requires valid sandbox `api_key` in `creds.json` under the `{connector}` entry. Tests are marked `@pytest.mark.integration` so they can be skipped in CI: `pytest -m "not integration"`.

## ✅ Validation Checklist

- [ ] `_map_status` has an entry for EVERY status the tech spec documents. Unmapped statuses are a critical issue.
- [ ] `Idempotency-Key` header IS sent — capture is monetary and replays must be safe.
- [ ] `amount_captured` in the response equals the requested amount for a full capture, or is strictly less for a partial capture. Never exceeds the original authorization amount.
- [ ] An attempt to capture an already-captured authorization yields a normalized error (mapped to `FAILURE` or surfaced as a typed exception) — do not let the raw PSP error bubble up.
- [ ] PSP-specific Pydantic models use `ConfigDict(extra="forbid")`.
- [ ] No floats anywhere on monetary fields.
- [ ] `mypy --strict` clean on this file.
- [ ] Integration test passes (manually, with creds).
