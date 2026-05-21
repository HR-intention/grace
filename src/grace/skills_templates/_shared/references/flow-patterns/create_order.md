# Flow pattern: `create_order`

Tells the PSP to create a hosted-checkout session. Returns a `psp_order_id` and a `payment_link` the merchant hands to the payer.

## Locked signature

```python
async def create_order(self, request: CreateOrderRequest) -> CreateOrderResponse:
```

## Inputs you can read on `request`

- `request.merchant_id: str` — PSP-side merchant identifier (from `ConnectorConfig`).
- `request.order_id: str` — Orbit's UUID. Pass through to the PSP as its reference.
- `request.customer_id: str | None` — Orbit's customer id (optional).
- `request.idempotency_key: str | None` — pass through as an HTTP header if `supports_idempotency_key`.
- `request.amount: Amount` — `minor_units: int` + `currency: Currency`. Convert at the wire only.
- `request.return_url: HttpUrl` — where the PSP redirects the payer after checkout.
- `request.allowed_methods: list[PaymentMethod] | None` — allow-list passed to PSP.
- `request.expires_at: datetime | None` — PSP-side TTL.
- `request.metadata: dict[str, str]` — opaque key-value pairs.

## Outputs you must populate on `CreateOrderResponse`

- `psp_order_id: str`
- `payment_link: HttpUrl`
- `status: OrderStatus` — typically `OrderStatus.CREATED`.
- `expires_at: datetime | None`

## Skeleton

```python
async def create_order(self, request: CreateOrderRequest) -> CreateOrderResponse:
    psp_req = <Psp>CreateOrderBody(
        order_id=request.order_id,
        order_amount=str(Decimal(request.amount.minor_units) / 100),
        order_currency=request.amount.currency.value,
        order_meta=<Psp>OrderMeta(return_url=str(request.return_url)),
        # ... PSP-specific fields per the API docs
    )
    headers = build_auth_headers(self._config)
    if request.idempotency_key and self.supports_idempotency_key:
        headers["x-idempotency-key"] = request.idempotency_key

    try:
        resp = await self._client.post("/orders", json=psp_req.model_dump(), headers=headers)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise _map_http_error(e) from e
    except httpx.HTTPError as e:
        raise ConnectorError(reason=ConnectorErrorReason.PSP_UNAVAILABLE) from e

    psp_resp = <Psp>CreateOrderResponse.model_validate(resp.json())
    return CreateOrderResponse(
        psp_order_id=psp_resp.cf_order_id,
        payment_link=psp_resp.payment_link,
        status=OrderStatus.CREATED,
        expires_at=psp_resp.order_expiry_time,
    )
```

## Errors to surface

| Cause | Raise |
|---|---|
| 4xx, validation error | `_map_http_error(e)` (typically `INVALID_REQUEST`) |
| 401 / 403 | `AUTHENTICATION_FAILED` / `AUTHORIZATION_FAILED` |
| 429 | `RATE_LIMITED` |
| 5xx / network | `PSP_UNAVAILABLE` |
| Wire validation fails | `INTERNAL` with `psp_message=str(e)` |

## Required tests in `tests/test_create_order.py`

1. **Happy path**: `httpx.MockTransport` returns success; assert `CreateOrderResponse` round-trips with expected `psp_order_id`, `payment_link`, `status`.
2. **4xx path**: transport returns 400 with a PSP error body; assert `ConnectorError(reason=INVALID_REQUEST)`.

## Pitfalls (from real generations)

- ❌ `request.amount.value` — there is no `.value` field on `Amount`. It's `minor_units: int`.
- ❌ `float(request.amount.minor_units)` — money never crosses our boundaries as float (ground rule 10). `Decimal` is fine inside the wire builder.
- ❌ `request.customer.id` — `CreateOrderRequest` has only `customer_id: str | None`, no nested `customer` object.
- ❌ Returning `OrderStatus.CREATED.value` (a string) instead of the enum. Use the enum.
