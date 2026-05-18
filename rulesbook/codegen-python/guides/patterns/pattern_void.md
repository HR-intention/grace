# Pattern: Void flow (Python)

## 🎯 Quick Start

Implements `{Connector}.void(data: PaymentData[VoidRequest, VoidResponse])`.

Void cancels an authorized-but-not-yet-captured payment so that no funds are moved.
The request is monetary (it releases a hold) — `Idempotency-Key` is MANDATORY.

HTTP method varies by PSP: most use `POST` (e.g., to a `.../cancel` or `.../void` sub-resource);
a few use `DELETE` against the payment resource itself. The default template below uses `POST`;
flip to `DELETE` if the tech spec explicitly says so.

Placeholders:
- `{Connector}` — class name (e.g., `Razorpay`)
- `{connector}` — lowercase (e.g., `razorpay`)
- `{void_endpoint}` — PSP void path, parameterized by `connector_payment_id`
  (e.g., `/payments/{connector_payment_id}/cancel` or `/payments/{connector_payment_id}/void`)
- `{Connector}VoidRequest` / `{Connector}VoidResponse` — PSP-specific Pydantic models

## 📋 Prerequisites

Authorize — Void requires a prior authorization that is NOT yet captured.

See [`../../../shared/flows.md`](../../../shared/flows.md) for the full prerequisite DAG.
(For voiding an already-captured payment, see VoidPC; some PSPs auto-route void-after-capture
to a refund, others reject — encode the PSP's behavior in `_map_status` / error normalization.)

## 🏗️ Template

In `connector_service/connectors/{connector}/connector.py`:

```python
from connector_service.connectors._base import BaseConnector, connector_flow
from connector_service.connectors._registry import register_connector
from connector_service.domain_types import (
    AttemptStatus, Flow, PaymentData, VoidRequest, VoidResponse,
)

from .transformers import (
    {Connector}VoidRequest, {Connector}VoidResponse,
    to_void_request, from_void_response,
)


class {Connector}(BaseConnector):
    # ... other flows defined elsewhere

    @connector_flow(flow=Flow.VOID)
    async def void(
        self, data: PaymentData[VoidRequest, VoidResponse]
    ) -> PaymentData[VoidRequest, VoidResponse]:
        connector_payment_id = data.request.connector_payment_id
        psp_request: {Connector}VoidRequest = to_void_request(data.request)
        # Most PSPs: POST. A few: DELETE — adapt per the tech spec.
        http_response = await self.client.post(
            f"{void_endpoint}".format(connector_payment_id=connector_payment_id),
            json=psp_request.model_dump(by_alias=True, exclude_none=True),
            headers={
                **self._auth_headers(),
                "Idempotency-Key": data.idempotency_key or "",
            },
        )
        http_response.raise_for_status()
        psp_response = {Connector}VoidResponse.model_validate_json(http_response.text)
        data.response = from_void_response(psp_response)
        data.status = _map_status(psp_response.status)
        return data


def _map_status(psp_status: str) -> AttemptStatus:
    # Fill in per the tech spec's "Status Mapping" section.
    # Void terminal statuses are usually VOIDED / FAILURE, but PSP may also
    # report VOID_INITIATED → ongoing — map accordingly.
    return {
        "voided": AttemptStatus.VOIDED,
        "cancelled": AttemptStatus.VOIDED,
        "void_initiated": AttemptStatus.PENDING,
        "failed": AttemptStatus.FAILURE,
        # ... add every status the tech spec lists
    }[psp_status]
```

In `connector_service/connectors/{connector}/transformers.py`:

```python
from typing import Optional
from pydantic import BaseModel, ConfigDict
from connector_service.domain_types import (
    AttemptStatus, VoidRequest, VoidResponse,
)


class {Connector}VoidRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Many PSPs accept no body; some accept a reason or notes.
    reason: Optional[str] = None


class {Connector}VoidResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    status: str


def to_void_request(req: VoidRequest) -> {Connector}VoidRequest:
    return {Connector}VoidRequest(
        reason=req.cancellation_reason,
    )


def from_void_response(resp: {Connector}VoidResponse) -> VoidResponse:
    return VoidResponse(
        connector_payment_id=resp.id,
        status=AttemptStatus.VOIDED,  # decorator overrides with mapped value
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
def test_void(client):
    # Pre-condition: a real connector_payment_id from a prior authorize call
    # that left the payment in AUTHORIZED state (NOT yet captured).
    response = client.post(
        "/v1/payments/void",
        headers={"Authorization": "Bearer test-key"},
        json={
            "connector_name": "{connector}",
            "request_id": "test-void-123",
            "request": {
                "connector_payment_id": "<id from prior authorize>",
                "cancellation_reason": "Duplicate transaction",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("voided", "pending", "failure")
    assert body["response"]["connector_payment_id"] == "<id from prior authorize>"
```

Requires valid sandbox `api_key` in `creds.json` under the `{connector}` entry. Tests are marked `@pytest.mark.integration` so they can be skipped in CI: `pytest -m "not integration"`.

## ✅ Validation Checklist

- [ ] `_map_status` has an entry for EVERY status the tech spec documents. Unmapped statuses are a critical issue.
- [ ] `Idempotency-Key` header IS sent — void releases a hold, replays must be safe.
- [ ] HTTP method matches the tech spec: `POST` for `.../cancel` style endpoints; `DELETE` only if explicitly documented.
- [ ] An attempt to void an already-CAPTURED payment yields a normalized error. Document whether the PSP rejects it or auto-routes to refund; if it auto-routes, this connector's Void method MUST still return a typed failure rather than silently producing a refund.
- [ ] PSP-specific Pydantic models use `ConfigDict(extra="forbid")`.
- [ ] No floats anywhere on monetary fields.
- [ ] `mypy --strict` clean on this file.
- [ ] Integration test passes (manually, with creds).
