# Pattern: create_order

The `create_order` flow tells the PSP to create a hosted-checkout session for a given `Amount` and `allowed_methods`. The PSP returns a session/order id and a payment link the merchant can hand to the payer.

## Domain types involved

- Request: `CreateOrderRequest` (from `lens.domain_types`)
- Response: `CreateOrderResponse` (from `lens.domain_types`)

See `../python/domain_types.md` for the locked shape. Highlights:

- `request.amount: Amount` — `minor_units: int` + `currency: Currency`. Convert at the wire only.
- `request.return_url: HttpUrl` — where the PSP redirects the payer after checkout.
- `request.allowed_methods: list[PaymentMethod] | None` — translates to the PSP's allow-list payload.
- `request.idempotency_key: str | None` — if set and `supports_idempotency_key`, pass through as a header.
- Response carries `psp_order_id`, `payment_link`, `status` (typically `OrderStatus.CREATED`), and optional `expires_at`.

## Method signature (in `connector.py`)

```python
async def create_order(self, request: CreateOrderRequest) -> CreateOrderResponse:
    ...
```

## Implementation skeleton

```python
from decimal import Decimal

async def create_order(self, request: CreateOrderRequest) -> CreateOrderResponse:
    # 1. Build the PSP wire-level request from the domain request.
    psp_req = <Psp>CreateOrderRequest(
        order_id=request.order_id,                            # Orbit's UUID as the PSP's reference
        order_amount=str(Decimal(request.amount.minor_units) / 100),  # if the PSP wants major-units
        order_currency=request.amount.currency.value,
        customer_details=_build_customer(request.customer_id),
        order_meta=<Psp>OrderMeta(
            return_url=str(request.return_url),
            payment_methods=_format_methods(request.allowed_methods),
        ),
        # ... other PSP-specific fields per its API docs
    )

    # 2. Sign / build auth headers.
    headers = build_auth_headers(self._config, psp_req)
    if request.idempotency_key and self.supports_idempotency_key:
        headers["x-idempotency-key"] = request.idempotency_key

    # 3. Call the PSP. Wrap httpx errors into ConnectorError.
    try:
        resp = await self._client.post("/orders", json=psp_req.model_dump(), headers=headers)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise _map_http_error(e) from e
    except httpx.HTTPError as e:
        raise ConnectorError(reason=ConnectorErrorReason.PSP_UNAVAILABLE) from e

    # 4. Parse the response into the wire-level model, then build the domain response.
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
| `httpx.HTTPStatusError` 4xx, validation error | `_map_http_error(e)` (typically `ConnectorError(INVALID_REQUEST)`) |
| `httpx.HTTPStatusError` 401/403 | `ConnectorError(AUTHENTICATION_FAILED)` or `AUTHORIZATION_FAILED` |
| `httpx.HTTPStatusError` 429 | `ConnectorError(RATE_LIMITED)` |
| `httpx.HTTPStatusError` 5xx | `ConnectorError(PSP_UNAVAILABLE)` |
| `httpx.HTTPError` (network) | `ConnectorError(PSP_UNAVAILABLE)` |
| Response shape validation fails | `ConnectorError(INTERNAL, psp_message=str(e))` |

## Tests

`tests/integration/connectors/<psp>/orders/test_create_order.py`:

- **Happy path** — `httpx.MockTransport` returns the PSP's success payload; assert the returned `CreateOrderResponse` has the right `psp_order_id`, `payment_link`, and `status == OrderStatus.CREATED`.
- **4xx path** — transport returns `400` with a PSP error body; assert `ConnectorError(reason=INVALID_REQUEST)` (or the more specific reason).
- **5xx path** — transport returns `503`; assert `ConnectorError(reason=PSP_UNAVAILABLE)`.
- **Network-error path** — `MockTransport` raises `httpx.ConnectError`; assert `ConnectorError(reason=PSP_UNAVAILABLE)`.
- **`_map_http_error` branch coverage** — parametrized test over the key branches (at minimum: 400, 401, 403, 404, 409, 429, one 5xx); assert the expected `ConnectorErrorReason` for each.
- **`payment_link` absent** — transport returns 200 but the link field is missing/null; assert `ConnectorError(reason=INTERNAL)`.
- (Optional) **Idempotency-key path** — assert the `x-idempotency-key` header is forwarded when the request carries one.

## `payment_link` is REQUIRED (non-None)

`CreateOrderResponse.payment_link` is typed `HttpUrl` — it is **not** `str | None`. If the PSP
response omits the link or the session URL field, do not return `None`; raise instead:

```python
from pydantic import HttpUrl

payment_link_str = psp_resp.payment_sessions_url or psp_resp.payment_link
if not payment_link_str:
    raise ConnectorError(reason=ConnectorErrorReason.INTERNAL)

return CreateOrderResponse(
    psp_order_id=psp_resp.cf_order_id,
    payment_link=HttpUrl(payment_link_str),   # ← coerce str→HttpUrl; required, non-optional
    status=OrderStatus.CREATED,
    expires_at=psp_resp.order_expiry_time,
)
```

**mypy `--strict` requires `HttpUrl(url)` coercion.** Passing a bare `str` variable:

```python
# WRONG — mypy strict error: "str" incompatible with "HttpUrl"
return CreateOrderResponse(payment_link=payment_link_str, …)
```

```python
# WRONG — pydantic validation fails on None:
return CreateOrderResponse(
    psp_order_id=…,
    payment_link=None,   # ← ValidationError at runtime
    …
)
```

Add a `payment_link absent` test case: transport returns a body where the link field is missing
or null; assert `ConnectorError(reason=INTERNAL)`.

---

## Notes

- The wire-level amount unit varies. Cashfree wants rupees-as-string (`"500.00"` for 50000 paise). Use `Decimal` inside the connector — never let the conversion bleed into the domain types.
- The PSP's `customer_details` block is built from `request.customer_id` if present; otherwise omit or use a sane default per the PSP's docs.
- If the PSP returns its session-id under a different key (`cf_order_id`, `order_id`, `id`, ...), the wire model decodes that; the domain response uses our `psp_order_id` name regardless.
