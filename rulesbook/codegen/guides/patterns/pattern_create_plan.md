# Pattern: create_plan

`create_plan` creates a reusable **PERIODIC** plan at the PSP via `POST /plans`, then `change_plan`
can repoint a mandate at a new plan. Inline `create_subscription` does NOT need a pre-created plan;
`create_plan` is for explicit plan lifecycle (upgrade/downgrade).

## Domain types

- Request: `CreatePlanRequest` (from `lens.domain_types`) — `merchant_id, idempotency_key,
  recurring_amount: Amount, max_amount: Amount, interval_type: MandateIntervalType,
  interval_count: int = 1, merchant_plan_id: str | None = None`.
- Response: `CreatePlanResponse` — `plan_id: str, raw: dict`.

## Method signature (in `subscriptions/connector.py`)

```python
async def create_plan(self, request: CreatePlanRequest) -> CreatePlanResponse:
    ...
```

## Implementation skeleton

```python
async def create_plan(self, request: CreatePlanRequest) -> CreatePlanResponse:
    # Deterministic plan id: caller value, else derive from the idempotency key so an
    # idempotent retry sends an identical body. (Charset: alnum/dot/hyphen/underscore, <= 40.)
    plan_id = request.merchant_plan_id or request.idempotency_key
    psp_req = <Psp>CreatePlanRequest(
        plan_id=plan_id,
        plan_name=plan_id,                       # lens has no separate name
        plan_type="PERIODIC",                    # CHANGE_PLAN is PERIODIC-only
        plan_recurring_amount=request.recurring_amount.minor_units / 100,   # major units
        plan_max_amount=request.max_amount.minor_units / 100,
        plan_currency=request.recurring_amount.currency.value,
        plan_intervals=request.interval_count,
        plan_interval_type=request.interval_type.value,
    )
    headers = build_auth_headers(self._config, psp_req)
    headers["<psp-idempotency-header>"] = request.idempotency_key
    try:
        resp = await self._client.post("/plans", json=psp_req.model_dump(exclude_none=True), headers=headers)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise _map_http_error(e) from e          # 400 → INVALID_REQUEST, etc.
    except httpx.HTTPError as e:
        raise ConnectorError(reason=ConnectorErrorReason.PSP_UNAVAILABLE) from e
    try:
        psp_resp = <Psp>PlanEntity.model_validate(resp.json())
    except ValidationError as e:
        raise ConnectorError(reason=ConnectorErrorReason.INTERNAL, psp_message=str(e)) from e
    return CreatePlanResponse(plan_id=str(psp_resp.plan_id or plan_id), raw=psp_resp.model_dump())
```

## Required tests (`tests/test_plan_management.py`)

- Happy path: `POST /plans`; wire body has `plan_type == "PERIODIC"`, `plan_recurring_amount` /
  `plan_max_amount` in **major units**, `plan_interval_type`, `plan_currency`; returns the echoed `plan_id`.
- No `merchant_plan_id` → wire `plan_id == idempotency_key` (deterministic).
- `x-idempotency-key` forwarded.
- 400 → `ConnectorError(INVALID_REQUEST)` + `psp_code`; 5xx → `PSP_UNAVAILABLE`.

## Pitfalls

- Major units: divide `minor_units` by 100 **inside the connector**; never mutate the domain `Amount`.
- The wire model field inventory (`CfCreatePlanRequest`) comes from `connector_docs/<psp>.md` §create_plan
  field map + the PSP's plans-create doc — do not invent fields.
