# Pattern: create_subscription

The `create_subscription` flow creates an **inline** mandate at the PSP — no pre-created plan_id
is passed. The PSP creates the subscription plan and returns a mandate reference plus a customer
approval handle (redirect URL, UPI intent deep-link, etc.).

## Domain types involved

- Request: `CreateSubscriptionRequest` (from `lens.domain_types`)
- Response: `CreateSubscriptionResponse` (from `lens.domain_types`)
- Embedded in response: `ApprovalHandle` (from `lens.domain_types`)

See `../python/domain_types.md` for the locked shapes. Highlights:

- `request.idempotency_key: str` — **always present** for this flow; forward as the PSP's
  idempotency token.
- `request.rail: MandateRail` — maps to the PSP's `payment_methods` / `authorization_details`
  equivalent. The exact wire value is in `connector_docs/<psp>.md` §Subscriptions.
- `request.amount: Amount` — `minor_units: int` + `currency: Currency`.
- `request.max_amount: Amount` — the mandate cap (RBI-required for UPI Autopay and card
  e-mandate).
- `request.interval_type: MandateIntervalType` + `request.interval_count: int` — billing
  cadence.
- `request.first_charge_at: datetime | None` — if present, the date of the first auto-debit;
  the PSP field name and whether it is required in periodic mode is PSP-specific — consult
  `connector_docs/<psp>.md`.
- `request.expires_at: datetime` — mandate expiry.
- `request.max_cycles: int | None` — cap on the number of debits; `None` = unlimited (or
  until `expires_at`).
- `request.customer_contact.email: str` — **required**; passed to the PSP's customer block.
- `request.customer_contact.phone: str` — **required**; passed to the PSP's customer block.
  Both fields are always present (`CustomerContact` forbids extras and both are non-optional).
- `request.return_url: HttpUrl` — where the PSP redirects after the customer completes
  approval.
- `request.description: str` — mandate description / note.
- `request.upi_vpa: Maskable[str] | None` — pre-filled VPA for UPI Autopay collect flows;
  `None` for REDIRECT or CARD rails.
- Response carries `psp_mandate_ref: str`, `status: MandateStatus`,
  `approval: ApprovalHandle`, and `raw: dict`.

## Method signature (in `subscriptions/connector.py`)

```python
async def create_subscription(
    self, request: CreateSubscriptionRequest
) -> CreateSubscriptionResponse:
    ...
```

## Implementation skeleton

```python
from decimal import Decimal

async def create_subscription(
    self, request: CreateSubscriptionRequest
) -> CreateSubscriptionResponse:
    # 1. Build the PSP wire-level request.
    #    Field names and nesting are PSP-specific — read connector_docs/<psp>.md §Subscriptions.
    psp_req = <Psp>CreateSubscriptionRequest(
        # Mandate identification
        subscription_id=str(uuid.uuid4()),       # PSP-driven or Orbit-supplied ref; see PSP docs
        # Customer block — both email and phone are required
        customer_details=<Psp>CustomerDetails(
            customer_email=request.customer_contact.email,
            customer_phone=request.customer_contact.phone,
        ),
        # Plan / schedule block
        plan=<Psp>PlanDetails(
            plan_name=request.description,
            plan_amount=str(Decimal(request.amount.minor_units) / 100),     # if PSP wants major-units
            plan_max_amount=str(Decimal(request.max_amount.minor_units) / 100),
            plan_intervals=request.interval_count,
            plan_interval_type=request.interval_type.value,                 # e.g. "MONTH"
            plan_max_cycles=request.plan_max_cycles,                        # None = omit or PSP default
        ),
        # Authorization / approval
        authorization_details=<Psp>AuthorizationDetails(
            # rail → payment_methods: see connector_docs/<psp>.md §rail-mapping
            payment_methods=_rail_to_payment_methods(request.rail),
            upi_id=str(request.upi_vpa) if request.upi_vpa is not None else None,
        ),
        subscription_meta=<Psp>SubscriptionMeta(
            return_url=str(request.return_url),
            # first_charge_at if present (periodic-only, PSP-specific field name):
            # e.g. subscription_first_charge_time=request.first_charge_at.isoformat()
        ),
        subscription_expiry_time=request.expires_at.isoformat(),
    )

    # 2. Build auth headers + forward idempotency_key.
    headers = build_auth_headers(self._config, psp_req)
    headers["<psp-idempotency-header>"] = request.idempotency_key   # PSP header name from docs

    # 3. Call the PSP. Wrap httpx errors into ConnectorError.
    try:
        resp = await self._client.post(
            "/subscriptions",
            json=psp_req.model_dump(exclude_none=True),
            headers=headers,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise _map_http_error(e) from e
    except httpx.HTTPError as e:
        raise ConnectorError(reason=ConnectorErrorReason.PSP_UNAVAILABLE) from e

    # 4. Parse the wire response and build the domain response.
    psp_resp = <Psp>CreateSubscriptionResponse.model_validate(resp.json())
    return CreateSubscriptionResponse(
        psp_mandate_ref=psp_resp.<psp_subscription_id_field>,
        status=map_subscription_status(psp_resp.subscription_status),   # status_map.py
        approval=_build_approval_handle(psp_resp),
        raw=psp_resp.model_dump(),
    )
```

Helper: building the `ApprovalHandle` from the PSP response:

```python
def _build_approval_handle(psp_resp: <Psp>CreateSubscriptionResponse) -> ApprovalHandle:
    # The shape depends on the rail and PSP.
    # REDIRECT: type="REDIRECT", url=<psp's payment_link or auth_link>
    # UPI intent: type="UPI_INTENT", url=<upi://...deep-link>
    # UPI collect: type="UPI_COLLECT", session_id=<token>
    # Consult connector_docs/<psp>.md for the exact discriminator.
    ...
```

## Errors to surface

| Cause | Raise |
|---|---|
| `httpx.HTTPStatusError` 4xx | `_map_http_error(e)` (typically `INVALID_REQUEST`) |
| `httpx.HTTPStatusError` 401/403 | `ConnectorError(AUTHENTICATION_FAILED)` or `AUTHORIZATION_FAILED` |
| `httpx.HTTPStatusError` 409 (duplicate idempotency key / mandate) | `ConnectorError(INVALID_REQUEST)` |
| `httpx.HTTPStatusError` 429 | `ConnectorError(RATE_LIMITED)` |
| `httpx.HTTPStatusError` 5xx | `ConnectorError(PSP_UNAVAILABLE)` |
| `httpx.HTTPError` (network) | `ConnectorError(PSP_UNAVAILABLE)` |
| Response shape validation fails | `ConnectorError(INTERNAL, psp_message=str(e))` |

## Required tests

`tests/integration/connectors/<psp>/subscriptions/test_create_subscription.py`:

- **Happy path (REDIRECT rail)** — `httpx.MockTransport` returns a PSP success body with a
  payment link; assert `CreateSubscriptionResponse` has `psp_mandate_ref` populated,
  `status == MandateStatus.PENDING_AUTHORIZATION`, and `approval.type == "REDIRECT"` with a
  non-empty `url`.
- **Happy path (UPI Autopay collect)** — PSP returns a collect token; assert `approval.type ==
  "UPI_COLLECT"` and `approval.session_id` populated.
- **Idempotency-key forwarding** — assert the PSP's idempotency header is present in the
  outbound request and equals `request.idempotency_key`.
- **PSP 400 (validation error)** — transport returns 400; assert
  `ConnectorError(reason=INVALID_REQUEST)`.
- **PSP 5xx** — transport returns 503; assert `ConnectorError(reason=PSP_UNAVAILABLE)`.

## Pitfalls

- **No pre-created plan_id**: create_subscription is **inline** — the PSP creates the
  subscription plan as part of this call. Do not add a "create plan then subscribe" pre-step
  unless the PSP explicitly requires separate plan creation.
- **Both `customer_contact.email` and `.phone` are required** — never omit either from the
  PSP customer block.
- **`rail` → `payment_methods`**: the mapping lives in `connector_docs/<psp>.md` §rail-mapping.
  Do NOT hardcode the PSP's internal method string here; call `_rail_to_payment_methods`.
- **`idempotency_key` is a `str` (not `str | None`)** on `CreateSubscriptionRequest` — it is
  always present. Forward it unconditionally.
- **Amount in minor units**: `request.amount.minor_units` is an integer (paise / cents).
  Convert to the PSP's unit (e.g. major-units as string) **inside the connector only**; never
  mutate the domain `Amount`.
- **`first_charge_at` is periodic-only**: if the PSP requires a subscription start date only
  in periodic mode, gate the field on `first_charge_at is not None`.
- **`expires_at` vs `max_cycles`**: both constrain the mandate lifetime. If the PSP supports
  only one, prefer `expires_at` and note the limitation in a comment.
