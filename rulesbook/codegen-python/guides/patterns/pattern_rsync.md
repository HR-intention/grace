# Pattern: RSync flow (Python)

## 🎯 Quick Start

Implements `{Connector}.rsync(data: PaymentData[RSyncRequest, RSyncResponse])`.

RSync (Refund Status Sync) polls the PSP to refresh the status of a previously-issued refund.
It is read-only and MUST be idempotent — the gateway / merchant may invoke it any number of times.

Placeholders:
- `{Connector}` — class name (e.g., `Razorpay`)
- `{connector}` — lowercase (e.g., `razorpay`)
- `{rsync_endpoint}` — PSP refund-status path, parameterized by `connector_refund_id`
  (e.g., `/refunds/{connector_refund_id}` or `/v1/payments/{connector_payment_id}/refunds/{connector_refund_id}`)
- `{Connector}RSyncResponse` — PSP-specific Pydantic model

## 📋 Prerequisites

Refund — RSync cannot run before a refund exists on the PSP side.

See [`../../../shared/flows.md`](../../../shared/flows.md) for the full prerequisite DAG.

## 🏗️ Template

In `connector_service/connectors/{connector}/connector.py`:

```python
from connector_service.connectors._base import BaseConnector, connector_flow
from connector_service.connectors._registry import register_connector
from connector_service.domain_types import (
    Flow, PaymentData, RefundStatus, RSyncRequest, RSyncResponse,
)

from .transformers import (
    {Connector}RSyncResponse, from_rsync_response,
)


class {Connector}(BaseConnector):
    # ... other flows defined elsewhere

    @connector_flow(flow=Flow.RSYNC)
    async def rsync(
        self, data: PaymentData[RSyncRequest, RSyncResponse]
    ) -> PaymentData[RSyncRequest, RSyncResponse]:
        connector_refund_id = data.request.connector_refund_id
        http_response = await self.client.get(
            f"{rsync_endpoint}".format(connector_refund_id=connector_refund_id),
            headers=self._auth_headers(),
        )
        http_response.raise_for_status()
        psp_response = {Connector}RSyncResponse.model_validate_json(http_response.text)
        data.response = from_rsync_response(psp_response)
        data.refund_status = _map_status(psp_response.status)
        return data


def _map_status(psp_status: str) -> RefundStatus:
    # Fill in per the tech spec's "Refund Status Mapping" section.
    # RSync must handle every transient/terminal status the PSP may return —
    # "still processing" is normal and must NOT raise.
    return {
        "pending": RefundStatus.PENDING,
        "processing": RefundStatus.PENDING,
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
from pydantic import BaseModel, ConfigDict
from connector_service.domain_types import (
    RefundStatus, RSyncResponse,
)


class {Connector}RSyncResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    status: str
    # ... whatever the PSP returns


def from_rsync_response(resp: {Connector}RSyncResponse) -> RSyncResponse:
    return RSyncResponse(
        connector_refund_id=resp.id,
        status=RefundStatus.PENDING,  # decorator overrides with mapped value
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
def test_rsync(client):
    # Pre-condition: a real connector_refund_id from a prior refund call.
    response = client.post(
        "/v1/payments/rsync",
        headers={"Authorization": "Bearer test-key"},
        json={
            "connector_name": "{connector}",
            "request_id": "test-rsync-123",
            "request": {
                "connector_refund_id": "<id from prior refund>",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in (
        "pending", "success", "failure", "transaction_failure", "manual_review",
    )
    assert body["response"]["connector_refund_id"] == "<id from prior refund>"
```

Requires valid sandbox `api_key` in `creds.json` under the `{connector}` entry. Tests are marked `@pytest.mark.integration` so they can be skipped in CI: `pytest -m "not integration"`.

## ✅ Validation Checklist

- [ ] `_map_status` has an entry for EVERY refund status the tech spec documents — including transient ones like `pending`, `processing`. Unmapped statuses are a critical issue.
- [ ] RSync handles "still processing" statuses by returning `PENDING` — it MUST NOT raise on a not-yet-terminal status.
- [ ] RSync is idempotent: calling it twice back-to-back yields the same `RSyncResponse`. No side-effects on the PSP.
- [ ] No `Idempotency-Key` is required (the call is a safe GET), but `Authorization` is.
- [ ] PSP-specific Pydantic models use `ConfigDict(extra="forbid")`.
- [ ] No floats anywhere on monetary fields.
- [ ] `mypy --strict` clean on this file.
- [ ] Integration test passes (manually, with creds).
