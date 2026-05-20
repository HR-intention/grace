# Testing

The emitted package must have working pytest tests. Aim for ≥ 80% line coverage on the package; the rubric awards 0–25 points linearly.

## Framework

- `pytest >= 8.0`, `pytest-asyncio` (configured `asyncio_mode = "auto"` in the consumer's pyproject — your tests just declare `async def test_...`).
- `httpx.MockTransport` for **all** HTTP-touching tests. **Never** hit a live PSP from a unit test.

## Required test files

Per `file_layout.md`, five test files are mandatory:

```
tests/test_create_order.py
tests/test_sync_payment.py
tests/test_refund.py
tests/test_sync_refund.py
tests/test_webhook.py
```

## Required cases per file

### `test_create_order.py`
- **Happy path**: PSP returns 200 with `psp_order_id` + `payment_link`; assert `CreateOrderResponse` round-trips.
- **4xx path**: PSP returns 400 with an error body; assert `ConnectorError` raised with the right `reason`.

### `test_sync_payment.py`
- **Single-attempt path**: order has one `SUCCESS` attempt; assert `attempts` has one entry, `paid_amount` populated.
- **Multi-attempt path**: order has two attempts, first `FAILED` then `SUCCESS`; assert `attempts` list contains both in observation order with the correct statuses, and `paid_amount` reflects the success.

### `test_refund.py`
- **Happy path**: PSP returns a `psp_refund_id` + `PENDING` (or `SUCCESS`) status.
- **Already-refunded path**: PSP returns 4xx-equivalent ("refund already exists" / "amount exceeds remaining"); assert `ConnectorError(reason=INVALID_ORDER_STATE)` or the relevant typed error.

### `test_sync_refund.py`
- **PENDING path**: PSP returns `pending`; assert `RefundStatus.PENDING`.
- **SUCCESS path**: PSP returns `success` + `refunded_amount`; assert `RefundStatus.SUCCESS` and the amount echoes.

### `test_webhook.py`
- **Signed PAYMENT_SUCCESS**: build a valid signed payload; assert `WebhookEvent.attempt.status == PaymentAttemptStatus.SUCCESS`.
- **Signed PAYMENT_FAILED**: assert `attempt.status == FAILED` and `failure_code` populated (e.g., `CARD_DECLINED` or `USER_DROPPED` depending on PSP signal).
- **Signed REFUND_SUCCESS**: assert `refund.status == SUCCESS`.
- **Tampered payload**: change one byte after signing; assert `ConnectorError(reason=WEBHOOK_SIGNATURE_FAILED)`.

## Test fixture pattern

```python
import httpx
import pytest
from lens.connectors.cashfree.connector import Cashfree
from lens.factory import ConnectorConfig
from lens.common import Maskable


def _config() -> ConnectorConfig:
    return ConnectorConfig(
        name="cashfree",
        api_key=Maskable("test_key"),
        secret_key=Maskable("test_secret"),
        webhook_secret=Maskable("test_webhook"),
    )


def _build_connector(handler) -> Cashfree:
    transport = httpx.MockTransport(handler)
    cfg = _config()
    c = Cashfree(cfg)
    # Replace the connector's client with one using the mock transport.
    c._client = httpx.AsyncClient(transport=transport, base_url=c.base_url)
    return c
```

(Yes — touching `_client` from the outside is intentional for tests. Production code uses the real httpx client. A cleaner injection seam is fine if the connector exposes one.)

## Coverage discipline

- Every branch in `connector.py` should be exercised by at least one test (happy + error path for each flow; signature-fail + at least two event types for the webhook).
- `status_map.py` should have at least one test exercising `map_status` for each entry, plus the `UNKNOWN` fallback.
- `auth.py` signing/verification helpers each get a direct unit test.
