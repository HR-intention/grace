# Pattern: refund

The `refund` flow initiates a reversal against the successful `PaymentAttempt` of an Order. Full or partial refunds are both supported; `amount_to_refund=None` ⇒ full. The PSP returns a refund id and an initial status (typically `PENDING`).

## Domain types involved

- Request: `RefundRequest` (from `lens.domain_types`)
- Response: `RefundResponse` (from `lens.domain_types`)

Highlights:

- `request.psp_payment_id: str` — the successful attempt's PSP id.
- `request.order_id: str` — **use this for order-scoped PSP refund URLs** (see note below).
- `request.refund_id: str` — Orbit's refund id; pass through as the PSP's reference.
- `request.amount_to_refund: int | None` — `None` means full refund.
- `request.idempotency_key: str | None` — pass through as a header when present.
- Response carries `psp_refund_id`, `status: RefundStatus`, optional `refunded_amount: int`.

> **`request.psp_order_id` does NOT exist on `RefundRequest`.**
> PSPs that scope refund endpoints to an order (e.g. `POST /orders/{id}/refunds`) must
> use **`request.order_id`** — the merchant order id Orbit stored at create-order time.
> Only `SyncPaymentRequest` has `psp_order_id`. Accessing `request.psp_order_id` on a
> `RefundRequest` raises `AttributeError` at runtime.

## Method signature (in `connector.py`)

```python
async def refund(self, request: RefundRequest) -> RefundResponse:
    ...
```

## Implementation skeleton

```python
async def refund(self, request: RefundRequest) -> RefundResponse:
    psp_req = <Psp>RefundRequest(
        refund_id=request.refund_id,
        refund_amount=(
            str(Decimal(request.amount_to_refund) / 100)
            if request.amount_to_refund is not None
            else None  # PSP-specific: omit for full refund or pass the payment's full amount
        ),
        refund_note=request.reason,
    )

    headers = build_auth_headers(self._config, psp_req)
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
        # Cashfree-shape: 409 = refund already exists / exceeds limit -> INVALID_ORDER_STATE
        if e.response.status_code in (409, 422):
            raise ConnectorError(reason=ConnectorErrorReason.INVALID_ORDER_STATE) from e
        raise _map_http_error(e) from e
    except httpx.HTTPError as e:
        raise ConnectorError(reason=ConnectorErrorReason.PSP_UNAVAILABLE) from e

    psp_resp = <Psp>RefundResponse.model_validate(resp.json())
    status, _ = map_refund_status(psp_resp.refund_status)  # status_map.py may have a refund table
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
| 4xx "refund already exists" / "amount > remaining" | `ConnectorError(INVALID_ORDER_STATE)` |
| 401 / 403 | `AUTHENTICATION_FAILED` / `AUTHORIZATION_FAILED` |
| 404 on payment | `ConnectorError(PAYMENT_NOT_FOUND)` |
| 5xx / network | `ConnectorError(PSP_UNAVAILABLE)` |
| Wire validation | `ConnectorError(INTERNAL)` |

## Tests

`tests/test_refund.py` (package-local; Grace relocates `tests/` after generation):

- **Happy path (full refund)** — `amount_to_refund=None`; assert `RefundResponse.status` is `PENDING` (or `SUCCESS` if the PSP reports immediately), and `psp_refund_id` populated.
- **Happy path (partial refund)** — assert the partial amount echoes correctly through `refunded_amount`.
- **Already-refunded / over-refund path** — PSP returns 409 or 422; assert `ConnectorError(reason=INVALID_ORDER_STATE)`.
- **5xx path** — PSP returns `502`; assert `ConnectorError(reason=PSP_UNAVAILABLE)`.
- **401 path** — PSP returns `401`; assert `ConnectorError(reason=AUTHENTICATION_FAILED)`.
- **404 path** — PSP returns `404`; assert `ConnectorError(reason=ORDER_NOT_FOUND)` (or `PAYMENT_NOT_FOUND` if the PSP scopes by payment).

## Notes

- Refund amount conversion mirrors `create_order`: Decimal at the wire, integer minor units in the domain types.
- PSP refund status vocabularies differ. If the PSP has a small set (`pending`, `success`, `failed`), inline a tiny mapping. If the vocabulary is rich (Cashfree has multiple intermediate states), put it in `status_map.py` alongside the payment-status table.
- For asynchronous PSPs, the refund will return `PENDING` and a follow-up webhook resolves to `SUCCESS` / `FAILED`. Orbit reconciles via the webhook + the `sync_refund` flow.
