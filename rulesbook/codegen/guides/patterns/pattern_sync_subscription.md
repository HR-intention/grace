# Pattern: sync_subscription

The `sync_subscription` flow polls the PSP for the current state of a mandate: its status,
the time of the next scheduled debit, and the outcome of the most recent debit attempt (if
any). **Orbit uses this to reconcile mandates after gaps or webhook misses.**

## Domain types involved

- Request: `SyncSubscriptionRequest` (from `lens.domain_types`)
- Response: `SyncSubscriptionResponse` (from `lens.domain_types`)
- Embedded: `MandateDebitOutcome` (from `lens.domain_types`)

Highlights:

- `request.psp_mandate_ref: str` — the PSP's subscription/mandate id from
  `create_subscription`.
- Response carries:
  - `status: MandateStatus` — the mandate's current lifecycle status.
  - `next_charge_at: datetime | None` — when the PSP will attempt the next debit; `None` if
    unknown or if the mandate is terminal.
  - `last_debit: MandateDebitOutcome | None` — the most recent debit attempt; `None` if no
    debit has been attempted yet.
  - `raw: dict | None` — PSP response verbatim for debug.

`MandateDebitOutcome` carries:
- `psp_debit_id: str` — the PSP's payment/transaction id for this debit attempt.
- `psp_mandate_ref: str` — echo of the mandate ref.
- `status: MandateDebitStatus` — `PENDING` / `SUCCESS` / `FAILED`.
- `amount: Amount` — the amount that was (or was attempted to be) debited.
- `failure_code: PaymentFailureCode | None` — `None` for non-FAILED debits; populated from
  `core/status.py`'s failure-substring map.
- `occurred_at: datetime` — when this debit attempt was recorded.
- `psp_attempt: int | None` — the PSP's internal retry counter; `None` if not exposed.

## Method signature (in `subscriptions/connector.py`)

```python
async def sync_subscription(
    self, request: SyncSubscriptionRequest
) -> SyncSubscriptionResponse:
    ...
```

## Implementation skeleton

```python
async def sync_subscription(
    self, request: SyncSubscriptionRequest
) -> SyncSubscriptionResponse:
    headers = build_auth_headers(self._config, None)
    try:
        resp = await self._client.get(
            f"/subscriptions/{request.psp_mandate_ref}",
            headers=headers,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ConnectorError(reason=ConnectorErrorReason.ORDER_NOT_FOUND) from e
        raise _map_http_error(e) from e
    except httpx.HTTPError as e:
        raise ConnectorError(reason=ConnectorErrorReason.PSP_UNAVAILABLE) from e

    psp_resp = <Psp>SyncSubscriptionResponse.model_validate(resp.json())

    last_debit: MandateDebitOutcome | None = None
    if psp_resp.<last_payment_field> is not None:
        last_debit = _to_debit_outcome(psp_resp.<last_payment_field>, request.psp_mandate_ref)

    return SyncSubscriptionResponse(
        status=map_subscription_status(psp_resp.subscription_status),
        next_charge_at=psp_resp.<next_charge_field>,    # datetime or None; parse as needed
        last_debit=last_debit,
        raw=psp_resp.model_dump(),
    )


def _to_debit_outcome(
    psp_payment: <Psp>LastPayment,
    psp_mandate_ref: str,
) -> MandateDebitOutcome:
    status, failure_code = map_debit_status(psp_payment.payment_status)   # status_map.py
    return MandateDebitOutcome(
        psp_debit_id=psp_payment.<psp_payment_id_field>,
        psp_mandate_ref=psp_mandate_ref,
        status=status,
        amount=Amount(
            minor_units=int(Decimal(psp_payment.payment_amount) * 100),
            currency=Currency(psp_payment.payment_currency),
        ),
        failure_code=failure_code,
        occurred_at=psp_payment.<payment_time_field>,
        psp_attempt=psp_payment.<retry_attempts_field>,   # None if PSP doesn't expose
    )
```

## Errors to surface

| Cause | Raise |
|---|---|
| 404 (mandate not found at PSP) | `ConnectorError(ORDER_NOT_FOUND)` |
| Other 4xx | `_map_http_error(e)` |
| 5xx / network | `ConnectorError(PSP_UNAVAILABLE)` |
| Wire shape validation fails | `ConnectorError(INTERNAL, psp_message=str(e))` |
| Unknown subscription status | handled by `map_subscription_status` fallback — logs warning, maps to nearest known status |

## Required tests

`tests/integration/connectors/<psp>/subscriptions/test_sync_subscription.py`:

- **Happy path (ACTIVE, next charge set)** — PSP returns an `ACTIVE` mandate with a next
  debit date; assert `status == MandateStatus.ACTIVE`, `next_charge_at` is a populated
  `datetime`.
- **Happy path (with last debit — SUCCESS)** — PSP response includes a successful last
  payment; assert `last_debit.status == MandateDebitStatus.SUCCESS`, `last_debit.amount`
  matches, `last_debit.failure_code is None`.
- **Happy path (with last debit — FAILED)** — PSP response includes a failed payment; assert
  `last_debit.status == MandateDebitStatus.FAILED` and `last_debit.failure_code` is a
  non-None `PaymentFailureCode`.
- **No debit yet** — new mandate with no payments; assert `last_debit is None`.
- **404 path** — transport returns 404; assert `ConnectorError(reason=ORDER_NOT_FOUND)`.
- **5xx path** — transport returns `503`; assert `ConnectorError(reason=PSP_UNAVAILABLE)`.
- **401 path** — transport returns 401; assert `ConnectorError(reason=AUTHENTICATION_FAILED)`.
- **Unknown subscription-status fallback** — PSP body has an unmapped `subscription_status`
  string; assert does NOT raise and `response.status` is the documented fallback (exercises the
  `map_subscription_status` warning branch).

## Pitfalls

- **Some PSPs embed the last debit inside the subscription body; others require a separate
  `/subscriptions/<ref>/payments` call** — check `connector_docs/<psp>.md` to know which.
- **`next_charge_at` may be absent for PENDING_AUTHORIZATION or terminal mandates**; always
  handle `None`.
- **Amount conversion**: PSP likely returns major-units as a string; convert to `minor_units`
  (integer) with `int(Decimal(x) * 100)` — use `Decimal`, never `float * 100`.
- **`psp_attempt`** is the PSP's internal retry counter, not Orbit's attempt count. Map it
  only if the PSP exposes it explicitly; otherwise pass `None`.
- **No idempotency key here** — `sync_subscription` is a read-only GET; never add a
  state-changing header.
