# Pattern: PSync flow (Python)

## 🎯 Quick Start

Implements `{Connector}.psync(data: PaymentData[PSyncRequest, PSyncResponse])`.

PSync (Payment Status Sync) polls the PSP to refresh the status of a previously-authorized payment.
It is read-only and MUST be idempotent — the gateway / merchant may invoke it any number of times.

Placeholders:
- `{Connector}` — class name (e.g., `Razorpay`)
- `{connector}` — lowercase (e.g., `razorpay`)
- `{psync_endpoint}` — PSP status path, parameterized by `connector_payment_id`
  (e.g., `/payments/{connector_payment_id}` or `/v1/orders/{connector_payment_id}/status`)
- `{Connector}PSyncResponse` — PSP-specific Pydantic model

## 📋 Prerequisites

Authorize — PSync cannot run before a payment exists on the PSP side.

See [`../../../shared/flows.md`](../../../shared/flows.md) for the full prerequisite DAG.

## 🏗️ Template

In `connector_service/connectors/{connector}/connector.py`:

```python
from connector_service.connectors._base import BaseConnector, connector_flow
from connector_service.connectors._registry import register_connector
from connector_service.domain_types import (
    AttemptStatus, Amount, Flow, PaymentData, PSyncRequest, PSyncResponse,
)

from .transformers import (
    {Connector}PSyncResponse, from_psync_response,
)


class {Connector}(BaseConnector):
    # ... other flows defined elsewhere

    @connector_flow(flow=Flow.PSYNC)
    async def psync(
        self, data: PaymentData[PSyncRequest, PSyncResponse]
    ) -> PaymentData[PSyncRequest, PSyncResponse]:
        connector_payment_id = data.request.connector_payment_id
        http_response = await self.client.get(
            f"{psync_endpoint}".format(connector_payment_id=connector_payment_id),
            headers=self._auth_headers(),
        )
        http_response.raise_for_status()
        psp_response = {Connector}PSyncResponse.model_validate_json(http_response.text)
        data.response = from_psync_response(psp_response)
        data.status = _map_status(psp_response.status)
        return data


def _map_status(psp_status: str) -> AttemptStatus:
    # Fill in per the tech spec's "Status Mapping" section.
    # PSync must handle every transient/terminal status the PSP may return —
    # "still processing" is normal and must NOT raise.
    return {
        "created": AttemptStatus.PENDING,
        "pending": AttemptStatus.PENDING,
        "authorized": AttemptStatus.AUTHORIZED,
        "captured": AttemptStatus.CHARGED,
        "failed": AttemptStatus.FAILURE,
        "voided": AttemptStatus.VOIDED,
        # ... add every status the tech spec lists
    }[psp_status]
```

In `connector_service/connectors/{connector}/transformers.py`:

```python
from typing import Optional
from pydantic import BaseModel, ConfigDict
from connector_service.domain_types import (
    Amount, AttemptStatus, Currency, PSyncResponse,
)


class {Connector}PSyncResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    status: str
    amount: Optional[int] = None        # minor units, if PSP returns
    currency: Optional[str] = None
    # ... whatever the PSP returns


def from_psync_response(resp: {Connector}PSyncResponse) -> PSyncResponse:
    amount_received: Optional[Amount] = None
    if resp.amount is not None and resp.currency is not None:
        amount_received = Amount(
            minor_units=resp.amount, currency=Currency(resp.currency)
        )
    return PSyncResponse(
        connector_payment_id=resp.id,
        status=AttemptStatus.PENDING,  # decorator overrides with mapped value
        amount_received=amount_received,
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
def test_psync(client):
    # Pre-condition: a real connector_payment_id from a prior authorize call.
    # Either chain from test_authorize_card or seed it from creds/fixtures.
    response = client.post(
        "/v1/payments/psync",
        headers={"Authorization": "Bearer test-key"},
        json={
            "connector_name": "{connector}",
            "request_id": "test-psync-123",
            "request": {
                "connector_payment_id": "<id from prior authorize>",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in (
        "pending", "authorized", "charged", "voided", "failure",
    )
    assert body["response"]["connector_payment_id"] == "<id from prior authorize>"
```

Requires valid sandbox `api_key` in `creds.json` under the `{connector}` entry. Tests are marked `@pytest.mark.integration` so they can be skipped in CI: `pytest -m "not integration"`.

## ✅ Validation Checklist

- [ ] `_map_status` has an entry for EVERY status the tech spec documents — including transient ones like `pending`, `processing`, `requires_action`. Unmapped statuses are a critical issue.
- [ ] PSync handles "still processing" statuses by returning `PENDING` — it MUST NOT raise on a not-yet-terminal status.
- [ ] PSync is idempotent: calling it twice back-to-back yields the same `PSyncResponse`. No side-effects on the PSP.
- [ ] No `Idempotency-Key` is required (the call is a safe GET), but `Authorization` is.
- [ ] `from_psync_response` populates `amount_received` only when the PSP returns an amount — `None` is acceptable for early-stage statuses.
- [ ] PSP-specific Pydantic models use `ConfigDict(extra="forbid")`.
- [ ] No floats anywhere on monetary fields.
- [ ] `mypy --strict` clean on this file.
- [ ] Integration test passes (manually, with creds).
