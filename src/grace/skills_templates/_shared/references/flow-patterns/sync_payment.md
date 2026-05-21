# Flow pattern: `sync_payment`

Polls the PSP for an order's overall state plus the list of `PaymentAttempt`s observed against it.

## Locked signature

```python
async def sync_payment(self, request: SyncPaymentRequest) -> SyncPaymentResponse:
```

## Inputs

- `request.psp_order_id: str` — the id returned by `create_order`.
- Plus the `RequestCommon` fields (`merchant_id`, `order_id`, `customer_id`, `idempotency_key`).

## Outputs

- `psp_order_id: str`
- `status: OrderStatus` — the order's overall status (`CREATED` | `PAID` | `PARTIALLY_REFUNDED` | `REFUNDED` | `EXPIRED` | `FAILED`).
- `paid_amount: int | None` — minor units; populated once at least one attempt is `SUCCESS`.
- `attempts: list[PaymentAttempt]` — every attempt the PSP has on file, in observation order.

## Skeleton

Most PSPs need two GETs: one for the order envelope, one for the payments list.

```python
async def sync_payment(self, request: SyncPaymentRequest) -> SyncPaymentResponse:
    try:
        order_raw = await self._client.get(f"/orders/{request.psp_order_id}")
        order_raw.raise_for_status()
        payments_raw = await self._client.get(f"/orders/{request.psp_order_id}/payments")
        payments_raw.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ConnectorError(reason=ConnectorErrorReason.ORDER_NOT_FOUND) from e
        raise _map_http_error(e) from e
    except httpx.HTTPError as e:
        raise ConnectorError(reason=ConnectorErrorReason.PSP_UNAVAILABLE) from e

    order_psp = <Psp>OrderResponse.model_validate(order_raw.json())
    payments_psp = [<Psp>Payment.model_validate(p) for p in payments_raw.json()]
    attempts = [_payment_to_attempt(p) for p in payments_psp]

    return SyncPaymentResponse(
        psp_order_id=request.psp_order_id,
        status=_map_order_status(order_psp.order_status),
        paid_amount=_paid_amount(attempts),
        attempts=attempts,
    )


def _payment_to_attempt(p: <Psp>Payment) -> PaymentAttempt:
    status, failure_code = map_status(p.payment_status)  # status_map.py
    amount = (
        Amount(
            minor_units=int(Decimal(p.payment_amount) * 100),
            currency=Currency(p.payment_currency),
        )
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


def _paid_amount(attempts: list[PaymentAttempt]) -> int | None:
    for a in attempts:
        if a.status == PaymentAttemptStatus.SUCCESS and a.amount is not None:
            return a.amount.minor_units
    return None
```

## Errors to surface

| Cause | Raise |
|---|---|
| 404 on order | `ORDER_NOT_FOUND` |
| Other 4xx | `_map_http_error(e)` |
| 5xx / network | `PSP_UNAVAILABLE` |
| Wire validation | `INTERNAL` |
| Unknown status term | `status_map.map_status` handles it — falls back to `(FAILED, UNKNOWN)` with a `structlog.warning`. |

## Required tests in `tests/test_sync_payment.py`

1. **Single-attempt happy path**: PSP returns one `SUCCESS` attempt; assert `len(response.attempts) == 1`, `response.status == OrderStatus.PAID`, `paid_amount` correct.
2. **Multi-attempt path**: PSP returns two attempts (first `FAILED`, second `SUCCESS`); assert list order, both statuses, `paid_amount` reflects the success.
3. **No-attempts path**: order in `CREATED` with empty payments; assert `attempts == []` and `status == CREATED`.

## Pitfalls

- ❌ Filtering `attempts` to only successes. Return all of them — Orbit needs the full history.
- ❌ Using PSP-specific status strings on `PaymentAttempt.status`. Every value must come from `status_map.map_status`.
- ❌ Inventing enum values like `PaymentAttemptStatus.CAPTURED` or `AUTHORIZED`. The locked set is `PENDING | SUCCESS | FAILED`.
