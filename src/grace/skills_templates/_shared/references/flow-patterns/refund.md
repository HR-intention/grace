# Flow pattern: `refund`

Initiates a refund against the successful `PaymentAttempt` of an order. Full or partial.

## Locked signature

```python
async def refund(self, request: RefundRequest) -> RefundResponse:
```

## Inputs

- `request.psp_payment_id: str` — the successful attempt's PSP id.
- `request.refund_id: str` — Orbit's refund id; pass through as the PSP's reference.
- `request.amount_to_refund: int | None` — minor units; `None` means full refund.
- `request.reason: str | None` — human-readable reason.
- `request.idempotency_key: str | None` — pass through as a header.

## Outputs

- `psp_refund_id: str`
- `status: RefundStatus` — `PENDING` | `SUCCESS` | `FAILED`.
- `refunded_amount: int | None` — populated once the refund settles.

## Skeleton

```python
async def refund(self, request: RefundRequest) -> RefundResponse:
    psp_req = <Psp>RefundBody(
        refund_id=request.refund_id,
        refund_amount=(
            str(Decimal(request.amount_to_refund) / 100)
            if request.amount_to_refund is not None
            else None
        ),
        refund_note=request.reason,
    )
    headers = build_auth_headers(self._config)
    if request.idempotency_key and self.supports_idempotency_key:
        headers["x-idempotency-key"] = request.idempotency_key

    try:
        resp = await self._client.post(
            f"/payments/{request.psp_payment_id}/refunds",
            json=psp_req.model_dump(exclude_none=True),
            headers=headers,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (409, 422):
            raise ConnectorError(reason=ConnectorErrorReason.INVALID_ORDER_STATE) from e
        raise _map_http_error(e) from e
    except httpx.HTTPError as e:
        raise ConnectorError(reason=ConnectorErrorReason.PSP_UNAVAILABLE) from e

    psp_resp = <Psp>RefundResponse.model_validate(resp.json())
    status, _ = map_refund_status(psp_resp.refund_status)
    return RefundResponse(
        psp_refund_id=psp_resp.cf_refund_id,
        status=status,
        refunded_amount=(
            int(Decimal(psp_resp.refund_amount) * 100)
            if psp_resp.refund_amount is not None
            else None
        ),
    )
```

## Errors to surface

| Cause | Raise |
|---|---|
| 4xx "already refunded" / "amount > remaining" | `INVALID_ORDER_STATE` |
| 401 / 403 | `AUTHENTICATION_FAILED` / `AUTHORIZATION_FAILED` |
| 404 on payment | `PAYMENT_NOT_FOUND` |
| 5xx / network | `PSP_UNAVAILABLE` |

## Required tests in `tests/test_refund.py`

1. **Full refund happy path**: `amount_to_refund=None`; assert `status` ∈ {`PENDING`, `SUCCESS`}, `psp_refund_id` populated.
2. **Partial refund**: pass a specific amount; assert it echoes back through `refunded_amount`.
3. **Already-refunded / over-refund**: PSP returns 409 or 422; assert `ConnectorError(INVALID_ORDER_STATE)`.

## Pitfalls

- ❌ Returning `RefundStatus.SUCCESS` immediately for PSPs that settle async. Most PSPs return `PENDING` and a follow-up webhook resolves it.
- ❌ Setting `refunded_amount` for a PENDING refund. Leave it `None` until the PSP confirms the settled value.
