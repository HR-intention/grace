# Flow pattern: `sync_refund`

Polls the PSP for a refund's current state. Symmetric to `sync_payment` but scoped to one refund.

## Locked signature

```python
async def sync_refund(self, request: SyncRefundRequest) -> SyncRefundResponse:
```

## Inputs

- `request.psp_refund_id: str` — id returned by `refund`.

## Outputs

- `psp_refund_id: str`
- `status: RefundStatus`
- `refunded_amount: int | None` — only when `status == SUCCESS`.
- `failure_reason: str | None` — only when `status == FAILED`.

## Skeleton

```python
async def sync_refund(self, request: SyncRefundRequest) -> SyncRefundResponse:
    try:
        resp = await self._client.get(f"/refunds/{request.psp_refund_id}")
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
| 404 | `REFUND_NOT_FOUND` |
| Other 4xx | `_map_http_error(e)` |
| 5xx / network | `PSP_UNAVAILABLE` |

## Required tests in `tests/test_sync_refund.py`

1. **PENDING**: PSP returns `pending`; assert `RefundStatus.PENDING` and `refunded_amount is None`.
2. **SUCCESS**: PSP returns `success` + amount; assert `RefundStatus.SUCCESS` and `refunded_amount` matches.
3. *(optional)* **FAILED**: PSP returns `failed` + reason; assert `status == FAILED` and `failure_reason` populated.
