# Pattern: sync_refund

The `sync_refund` flow polls the PSP for a refund's current state. The flow is symmetric to `sync_payment` but scoped to a single refund — no per-attempt list, just one `RefundStatus` and the actual refunded amount once finalized.

## Domain types involved

- Request: `SyncRefundRequest` (from `lens.domain_types`)
- Response: `SyncRefundResponse` (from `lens.domain_types`)

Highlights:

- `request.psp_refund_id: str` — what `refund` returned.
- `request.order_id: str` — **use this for order-scoped PSP refund-status URLs** (see note below).
- Response carries `psp_refund_id`, `status: RefundStatus`, optional `refunded_amount: int`, optional `failure_reason: str`.

> **`request.psp_order_id` does NOT exist on `SyncRefundRequest`.**
> PSPs that scope refund-status endpoints to an order
> (e.g. `GET /orders/{id}/refunds/{refund_id}`) must use **`request.order_id`** — the
> merchant order id Orbit stored at create-order time.  Only `SyncPaymentRequest` has
> `psp_order_id`. Accessing `request.psp_order_id` on a `SyncRefundRequest` raises
> `AttributeError` at runtime.

## Method signature (in `connector.py`)

```python
async def sync_refund(self, request: SyncRefundRequest) -> SyncRefundResponse:
    ...
```

## Implementation skeleton

```python
async def sync_refund(self, request: SyncRefundRequest) -> SyncRefundResponse:
    try:
        resp = await self._client.get(
            f"/refunds/{request.psp_refund_id}",
            headers=build_auth_headers(self._config, None),
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ConnectorError(reason=ConnectorErrorReason.REFUND_NOT_FOUND) from e
        raise _map_http_error(e) from e
    except httpx.HTTPError as e:
        raise ConnectorError(reason=ConnectorErrorReason.PSP_UNAVAILABLE) from e

    psp_resp = <Psp>RefundResponse.model_validate(resp.json())
    status, _ = map_refund_status(psp_resp.refund_status)
    return SyncRefundResponse(
        psp_refund_id=psp_resp.cf_refund_id,
        status=status,
        refunded_amount=(
            int(Decimal(psp_resp.refund_amount) * 100)
            if psp_resp.refund_amount is not None and status == RefundStatus.SUCCESS
            else None
        ),
        failure_reason=psp_resp.refund_note if status == RefundStatus.FAILED else None,
    )
```

## Errors to surface

| Cause | Raise |
|---|---|
| 404 on refund lookup | `ConnectorError(REFUND_NOT_FOUND)` |
| Other 4xx | `_map_http_error(e)` |
| 5xx / network | `ConnectorError(PSP_UNAVAILABLE)` |
| Wire validation | `ConnectorError(INTERNAL)` |

## Tests

`tests/test_sync_refund.py`:

- **PENDING path** — PSP returns the refund in `pending`; assert `RefundStatus.PENDING` and `refunded_amount is None`.
- **SUCCESS path** — PSP returns `success` + `refund_amount`; assert `RefundStatus.SUCCESS` and `refunded_amount` matches the original request amount (converted from wire major-units back to minor-units).
- (Optional) **FAILED path** — PSP returns `failed` + a reason; assert `RefundStatus.FAILED` and `failure_reason` populated.

## Notes

- `refunded_amount` is only populated when the refund actually settles. While the refund is `PENDING` the PSP may report an intended amount, but our domain type treats it as not-yet-real and returns `None`.
- The refund-status mapping table (in `status_map.py`) is separate from the payment-status table — refunds typically have fewer states (`pending`, `success`, `failed`).
