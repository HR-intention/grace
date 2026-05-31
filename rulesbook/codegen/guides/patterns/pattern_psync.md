# Pattern: sync_payment

The `sync_payment` flow polls the PSP for the order's current state, returning the overall `OrderStatus` and the list of `PaymentAttempt`s the PSP has observed under the order. An order with no attempts yet returns `attempts=[]`; an order with multiple attempts (some `FAILED`, one `SUCCESS`) returns all of them in observation order.

## Domain types involved

- Request: `SyncPaymentRequest` (from `lens.domain_types`)
- Response: `SyncPaymentResponse` (from `lens.domain_types`)
- Per-attempt model: `PaymentAttempt` (from `lens.domain_types`)

Highlights:

- `request.psp_order_id: str` — the PSP-side order id from `create_order`'s response.
- Response carries `psp_order_id`, `status: OrderStatus`, `paid_amount: int | None`, and `attempts: list[PaymentAttempt]`.
- Each `PaymentAttempt` carries `psp_payment_id`, `status: PaymentAttemptStatus`, optional `failure_code`, `failure_reason`, `method_used`, `amount`, and `attempted_at`. The `raw` dict captures PSP-specific extras for debug only.

## Method signature (in `connector.py`)

```python
async def sync_payment(self, request: SyncPaymentRequest) -> SyncPaymentResponse:
    ...
```

## Implementation skeleton

Most PSPs need two GETs: one for the order metadata (overall status), one for the list of attempts. Cashfree is the canonical case.

```python
async def sync_payment(self, request: SyncPaymentRequest) -> SyncPaymentResponse:
    try:
        order_resp_raw = await self._client.get(
            f"/orders/{request.psp_order_id}",
            headers=build_auth_headers(self._config, None),
        )
        order_resp_raw.raise_for_status()
        payments_resp_raw = await self._client.get(
            f"/orders/{request.psp_order_id}/payments",
            headers=build_auth_headers(self._config, None),
        )
        payments_resp_raw.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ConnectorError(reason=ConnectorErrorReason.ORDER_NOT_FOUND) from e
        raise _map_http_error(e) from e
    except httpx.HTTPError as e:
        raise ConnectorError(reason=ConnectorErrorReason.PSP_UNAVAILABLE) from e

    order_psp = <Psp>OrderResponse.model_validate(order_resp_raw.json())
    payments_psp = [<Psp>Payment.model_validate(p) for p in payments_resp_raw.json()]

    attempts = [_payment_to_attempt(p) for p in payments_psp]  # uses status_map.map_status

    return SyncPaymentResponse(
        psp_order_id=request.psp_order_id,
        status=_map_order_status(order_psp.order_status),
        paid_amount=_compute_paid_amount(attempts),
        attempts=attempts,
    )


def _payment_to_attempt(p: <Psp>Payment) -> PaymentAttempt:
    status, failure_code = map_status(p.payment_status)
    amount = (
        Amount(minor_units=int(Decimal(p.payment_amount) * 100), currency=Currency(p.payment_currency))
        if status == PaymentAttemptStatus.SUCCESS and p.payment_amount is not None
        else None
    )
    return PaymentAttempt(
        psp_payment_id=p.cf_payment_id,
        status=status,
        method_used=_map_method(p.payment_method),
        amount=amount,
        failure_code=failure_code,
        failure_reason=p.payment_message if status == PaymentAttemptStatus.FAILED else None,
        attempted_at=p.payment_time,
        raw=p.model_dump(),
    )


def _compute_paid_amount(attempts: list[PaymentAttempt]) -> int | None:
    for a in attempts:
        if a.status == PaymentAttemptStatus.SUCCESS and a.amount is not None:
            return a.amount.minor_units
    return None
```

## Errors to surface

| Cause | Raise |
|---|---|
| 404 on order lookup | `ConnectorError(ORDER_NOT_FOUND)` |
| Other 4xx | `_map_http_error(e)` |
| 5xx / network | `ConnectorError(PSP_UNAVAILABLE)` |
| Wire validation | `ConnectorError(INTERNAL, psp_message=str(e))` |
| Unknown status term | (handled by `status_map.map_status` — falls back to `(FAILED, UNKNOWN)` with a `structlog.warning`) |

## Tests

`tests/integration/connectors/<psp>/orders/test_sync_payment.py`:

- **Single-attempt happy path** — PSP returns one `SUCCESS` attempt; assert `len(response.attempts) == 1`, `response.status == OrderStatus.PAID`, `response.paid_amount` matches.
- **Multi-attempt path** — PSP returns two attempts (first `FAILED`, then `SUCCESS`); assert the list contains both in PSP-observation order, both statuses correct, `paid_amount` reflects the success amount.
- **No-attempts path** — PSP returns the order in `CREATED` state with empty payments; assert `response.attempts == []` and `response.status == OrderStatus.CREATED`.
- **5xx path** — endpoint returns `503`; assert `ConnectorError(reason=PSP_UNAVAILABLE)`.
- **Unknown order-status path** — order body contains an unmapped `order_status` string; assert does NOT raise and `response.status` is the documented fallback (exercises `map_order_status` warning branch).
- **404 path** — endpoint returns 404; assert `ConnectorError(reason=ORDER_NOT_FOUND)`.
- (Optional) **`FLAGGED` → `PENDING`+`FRAUD_REVIEW_PENDING`** — assert the status-map mapping flows through.

## Notes

- The order-status mapping (`_map_order_status`) is per-PSP. Most PSPs have a separate order-status vocabulary from the payment-status one. Translate to the `OrderStatus` enum (`CREATED`, `PAID`, `PARTIALLY_REFUNDED`, `REFUNDED`, `EXPIRED`, `FAILED`).
- `paid_amount` is `int | None` — `None` until at least one attempt is `SUCCESS`. Sum of refunded amounts is **not** netted off here; the order may still be `PAID` even after partial refunds (the order status itself moves to `PARTIALLY_REFUNDED`).
- Don't filter the attempts list. The caller (Orbit) wants the full history including failures.
