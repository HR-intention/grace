# Pattern: cancel_subscription / pause_subscription / resume_subscription

These three flows share the same signature: `(request: ManageMandateRequest) ->
ManageMandateResponse`. All three are **state-changing** operations; all three forward the
`idempotency_key`. This file covers the differences in PSP verb and expected outcome.

## Domain types involved

- Request: `ManageMandateRequest` (from `lens.domain_types`)
- Response: `ManageMandateResponse` (from `lens.domain_types`)

Highlights of `ManageMandateRequest`:

- `psp_mandate_ref: str` — the PSP's subscription/mandate id.
- `idempotency_key: str` — **always present on all three flows**; forward as the PSP's
  idempotency token.
- `reason: str | None` — optional reason/note; pass to the PSP if it accepts a reason field.
- `effective_at: datetime | None` — for `resume_subscription`: the date from which debits
  should restart. Maps to the PSP's **`next_scheduled_time`** (or equivalent). Omit for
  cancel/pause if the PSP has no scheduling concept for those verbs.

`ManageMandateResponse` carries:

- `status: MandateStatus` — the mandate's new status as echoed by the PSP.
- `raw: dict | None` — PSP response verbatim.

## Method signatures (in `subscriptions/connector.py`)

```python
async def cancel_subscription(
    self, request: ManageMandateRequest
) -> ManageMandateResponse: ...

async def pause_subscription(
    self, request: ManageMandateRequest
) -> ManageMandateResponse: ...

async def resume_subscription(
    self, request: ManageMandateRequest
) -> ManageMandateResponse: ...
```

## PSP verb mapping

| Lens method | PSP action verb | `action_details` | Expected new `MandateStatus` |
|---|---|---|---|
| `cancel_subscription` | `CANCEL` (PSP-specific) | none | `MandateStatus.CANCELLED` |
| `pause_subscription` | `PAUSE` (PSP-specific) | none | `MandateStatus.PAUSED` |
| `resume_subscription` | **`ACTIVATE`** | none | `MandateStatus.ACTIVE` |
| `change_plan` | **`CHANGE_PLAN`** | `{"plan_id": <new_plan_id>}` | unchanged (whatever PSP echoes) |

**`resume_subscription` maps to the PSP's ACTIVATE verb.** There is no separate RESUME verb
in the PSP APIs observed. When calling `resume_subscription`, send the ACTIVATE action.

**`change_plan` reuses the same `_manage` helper** with `action="CHANGE_PLAN"` and passes
`action_details={"plan_id": request.new_plan_id}` in the action payload. The `plan_id` key
name is PSP-specific — see `connector_docs/<psp>.md` for the exact field name.

## Implementation skeleton

```python
async def cancel_subscription(
    self, request: ManageMandateRequest
) -> ManageMandateResponse:
    return await self._manage(request, action="CANCEL")


async def pause_subscription(
    self, request: ManageMandateRequest
) -> ManageMandateResponse:
    return await self._manage(request, action="PAUSE")


async def resume_subscription(
    self, request: ManageMandateRequest
) -> ManageMandateResponse:
    # resume = PSP ACTIVATE verb; effective_at → next_scheduled_time
    return await self._manage(request, action="ACTIVATE")


async def change_plan(self, request: ChangePlanRequest) -> ManageMandateResponse:
    # Reuse the _manage helper with CHANGE_PLAN action and action_details carrying the new plan.
    inner = ManageMandateRequest(
        merchant_id=request.merchant_id,
        idempotency_key=request.idempotency_key,
        psp_mandate_ref=request.psp_mandate_ref,
    )
    return await self._manage(
        inner,
        action="CHANGE_PLAN",
        action_details={"plan_id": request.new_plan_id},
    )


async def _manage(
    self,
    request: ManageMandateRequest,
    action: str,
    action_details: dict | None = None,
) -> ManageMandateResponse:
    # Build the action payload; field names are PSP-specific (see connector_docs/<psp>.md).
    action_payload: dict = {"action": action}
    if action_details is not None:
        action_payload["action_details"] = action_details
    if request.reason is not None:
        action_payload["reason"] = request.reason
    # ACTIVATE only: schedule the next debit via next_scheduled_time
    if action == "ACTIVATE" and request.effective_at is not None:
        action_payload["next_scheduled_time"] = request.effective_at.isoformat()

    headers = build_auth_headers(self._config, action_payload)
    headers["<psp-idempotency-header>"] = request.idempotency_key

    try:
        resp = await self._client.post(
            f"/subscriptions/{request.psp_mandate_ref}/manage",   # PSP path from docs
            json=action_payload,
            headers=headers,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ConnectorError(reason=ConnectorErrorReason.ORDER_NOT_FOUND) from e
        raise _map_http_error(e) from e
    except httpx.HTTPError as e:
        raise ConnectorError(reason=ConnectorErrorReason.PSP_UNAVAILABLE) from e

    psp_resp = <Psp>ManageSubscriptionResponse.model_validate(resp.json())
    return ManageMandateResponse(
        status=map_subscription_status(psp_resp.subscription_status),
        raw=psp_resp.model_dump(),
    )
```

## Errors to surface

| Cause | Raise |
|---|---|
| 404 (mandate not found) | `ConnectorError(ORDER_NOT_FOUND)` |
| 409 / 422 "invalid state" (e.g. cancel an already-cancelled mandate) | `ConnectorError(INVALID_ORDER_STATE)` |
| **400** (e.g. CHANGE_PLAN ceiling / PERIODIC-only violation) | flows through `_map_http_error` → `ConnectorError(INVALID_REQUEST)` |
| 4xx auth | `ConnectorError(AUTHENTICATION_FAILED)` / `AUTHORIZATION_FAILED` |
| 429 | `ConnectorError(RATE_LIMITED)` |
| 5xx / network | `ConnectorError(PSP_UNAVAILABLE)` |
| Wire shape validation fails | `ConnectorError(INTERNAL, psp_message=str(e))` |

**Error-mapping note (CHANGE_PLAN):** a ceiling violation or PERIODIC-only rejection from the
PSP arrives as **400**, which flows through `_map_http_error → INVALID_REQUEST`. This is the
correct path. The `409/422 → INVALID_ORDER_STATE` shortcut in `_manage` is for cancel/pause/
resume state errors **only** — do not describe 400 as a "state" error or route it through the
409/422 shortcut. If a PSP ever returns 409 or 422 for a ceiling, it would be misclassified
as `INVALID_ORDER_STATE`; flag that as a PSP-specific carve-out if needed.

## Required tests

`tests/test_manage_mandate.py` (covers cancel/pause/resume; package-local — Grace relocates
`tests/` after generation), or separate `tests/test_cancel_subscription.py`,
`tests/test_pause_subscription.py`, `tests/test_resume_subscription.py`:

Each file needs:
- **Happy path** — mock returns the expected post-operation `MandateStatus` (CANCELLED/PAUSED/ACTIVE); assert `ManageMandateResponse.status` is that status.
- **Idempotency-key forwarding** — assert the PSP's idempotency header is present in the outbound request.
- **5xx path** — transport returns `503`; assert `ConnectorError(reason=PSP_UNAVAILABLE)`.
- **404 path** — transport returns 404; assert `ConnectorError(reason=ORDER_NOT_FOUND)`.
- **401 path** — transport returns 401; assert `ConnectorError(reason=AUTHENTICATION_FAILED)`.
- **Invalid state** — transport returns 422 (e.g. cancel already cancelled); assert `ConnectorError(reason=INVALID_ORDER_STATE)`.

`test_resume_subscription.py` additionally:
- **`effective_at` forwarding** — action body must contain `ACTIVATE` and `next_scheduled_time` when `effective_at` is set.
- **`effective_at` is None** — omit `next_scheduled_time`; PSP should still accept the ACTIVATE call.

## Pitfalls

- **`resume_subscription` ≠ a "RESUME" PSP verb.** The PSP verb is **ACTIVATE**. Do not
  invent a RESUME action — the PSP will reject it.
- **`effective_at` → `next_scheduled_time`**: the `ManageMandateRequest.effective_at` field
  is the date the mandate should resume. Map it to the PSP's equivalent
  (`next_scheduled_time`, `resume_date`, etc. — see `connector_docs/<psp>.md`).
- **`idempotency_key` is forwarded on all three** — cancel, pause, and resume are all
  state-changing; always add the idempotency header.
- **`supports_pause()` introspection**: the `pause_subscription` method must still be present
  (it is an abstract method on `MandateConnector`), but if `supports_pause()` returns `False`
  for this PSP, the implementation should raise `ConnectorError(NOT_SUPPORTED)` immediately
  rather than calling the PSP.
- **Do NOT call `supports_pause()` inside `resume_subscription`** — a PSP that does not natively
  support pause will not expose ACTIVATE for the same workflow.
