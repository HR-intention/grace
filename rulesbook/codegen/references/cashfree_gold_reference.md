# GOLD REFERENCE — Cashfree connector (sandbox-validated)

This is the **canonical, working** Cashfree connector. It is sandbox-validated and passes its full
test suite. When generating or regenerating Cashfree (and as the worked example for any PSP),
**match these patterns exactly**. Each section names the failure mode a prior regeneration hit by
deviating — do not repeat them.

> How to use: read this BEFORE writing any flow. The abstract rules in `python/*.md` and
> `guides/patterns/*.md` say the same things; this file is the concrete proof. When in doubt,
> copy the shape here.

---

## 1. Error wrapping — NEVER let a raw `httpx` or `json` error escape

Every network call and every parse is wrapped. A raw `httpx.HTTPError`, `httpx.ConnectError`, or
`json.JSONDecodeError` reaching the caller is a **bug** — it must become a `ConnectorError`.

Shared helpers (module-level in each domain `connector.py`):

```python
def _extract_psp_error(e: httpx.HTTPStatusError) -> tuple[str | None, str | None]:
    """Pull Cashfree's {code, message} from an error body, if present."""
    try:
        body = e.response.json()
    except (ValueError, TypeError):
        return None, None
    if not isinstance(body, dict):
        return None, None
    code, message = body.get("code"), body.get("message")
    return (code if isinstance(code, str) else None, message if isinstance(message, str) else None)


def _map_http_error(e: httpx.HTTPStatusError) -> ConnectorError:
    status = e.response.status_code
    psp_code, psp_message = _extract_psp_error(e)
    reason_by_status: dict[int, ConnectorErrorReason] = {
        401: ConnectorErrorReason.AUTHENTICATION_FAILED,
        403: ConnectorErrorReason.AUTHORIZATION_FAILED,
        404: ConnectorErrorReason.ORDER_NOT_FOUND,
        409: ConnectorErrorReason.INVALID_ORDER_STATE,
        429: ConnectorErrorReason.RATE_LIMITED,
        400: ConnectorErrorReason.INVALID_REQUEST,
        422: ConnectorErrorReason.INVALID_REQUEST,
    }
    reason = reason_by_status.get(status, ConnectorErrorReason.PSP_UNAVAILABLE)
    return ConnectorError(reason=reason, psp_code=psp_code, psp_message=psp_message)
```

The canonical call + parse shape (every flow uses this exact structure):

```python
try:
    resp = await self._client.post("/orders", json=psp_req.model_dump(exclude_none=True), headers=headers)
    resp.raise_for_status()
except httpx.HTTPStatusError as e:
    raise _map_http_error(e) from e
except httpx.HTTPError as e:                       # network/timeout — NEVER leak
    raise ConnectorError(reason=ConnectorErrorReason.PSP_UNAVAILABLE) from e

try:
    psp_resp = CfOrderResponse.model_validate(resp.json())
except ValidationError as e:
    raise ConnectorError(reason=ConnectorErrorReason.INTERNAL, psp_message=str(e)) from e
```

Webhook parsers wrap the JSON decode too:

```python
try:
    payload = json.loads(raw)
except (json.JSONDecodeError, ValueError) as e:
    raise ConnectorError(reason=ConnectorErrorReason.INVALID_REQUEST, psp_message=str(e)) from e
```

> ❌ **Regen failure:** raw `httpx.ConnectError` and `json.JSONDecodeError` propagated to the caller;
> a `pause` state error mapped to `INVALID_REQUEST` instead of `INVALID_ORDER_STATE` (the 409 arm).
> Keep the `409 → INVALID_ORDER_STATE` mapping for cancel/pause/resume.

---

## 2. Amounts — `Decimal`→**string** at the wire, `int` minor-units in the domain

Cashfree wants amounts as **strings**. Build them with `Decimal`, never a bare float division.

```python
order_amount=str(Decimal(request.amount.minor_units) / 100)     # 5000 -> "50"  (NOT 50.0)
refund_amount=str(Decimal(request.amount_to_refund) / 100)      # request body
```

Back to the domain (always `int` minor units):

```python
refunded_amount=int(Decimal(str(psp_resp.refund_amount)) * 100) if psp_resp.refund_amount is not None else None
```

> ❌ **Regen failure:** sent `refund_amount = (amount or 0) / 100.0` → float `50.0`; the PSP/test
> expects the string `"50"`. Floats also lose precision. Always `str(Decimal(...) / 100)`.

---

## 3. ID selection — merchant id out, never the PSP-internal id

The id returned to the caller (`psp_order_id`, `psp_mandate_ref`, `psp_refund_id`) must be the one
the PSP keys its action APIs on. Prefer the **merchant-supplied** id; the PSP's auto-generated
`cf_*` id is for read-side correlation only.

```python
psp_order_id=str(psp_resp.order_id or request.order_id)                  # merchant order id
psp_mandate_ref=str(psp_resp.subscription_id or psp_resp.cf_subscription_id or request.idempotency_key)
psp_refund_id=str(psp_resp.cf_refund_id or psp_resp.refund_id or request.refund_id)
```

`sync_refund` returns `refunded_amount` only on success:

```python
refunded_amount=(int(Decimal(str(psp_resp.refund_amount)) * 100)
                 if psp_resp.refund_amount is not None and status == RefundStatus.SUCCESS else None)
```

> ❌ **Regen failure:** returned `psp_mandate_ref` as `cf_subscription_id` (internal) — action calls
> 404; and `refunded_amount` was populated on a non-success refund (`assert 5000 is None` failed).

---

## 4. Wire models — requests are strict, responses are permissive

PSP **request** models lock down; PSP **response** models tolerate the PSP returning whatever it
likes (numbers where you expect strings, extra keys).

```python
class CfCreateOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)        # requests: strict
    ...

class CfPaymentEntity(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=False)        # responses: permissive
    cf_payment_id: int | str | None = None                       # PSP sends int OR str — accept both
```

> ❌ **Regen failure:** typed `cf_payment_id: str` and `extra="forbid"` on a response entity →
> `ValidationError` on the real payload `cf_payment_id: 12345`. Response entities use
> `extra="allow"` and union types (`int | str | None`) for ids/amounts.

---

## 5. Webhook parsing — event/status maps, refund-by-status, auth-only rail

Map the PSP event name through an explicit table; derive refund event type from the refund **status**,
not the event name; read the realized rail **only on auth-success** (Cashfree echoes `payment_group`
on failed auths too).

```python
_PAYMENT_EVENT_MAP = {
    "PAYMENT_SUCCESS_WEBHOOK": WebhookEventType.PAYMENT_SUCCESS,
    "PAYMENT_FAILED_WEBHOOK": WebhookEventType.PAYMENT_FAILED,
    "REFUND_STATUS_WEBHOOK": WebhookEventType.REFUND_SUCCESS,
    ...
}

# refund event type from STATUS:
event_type = WebhookEventType.REFUND_SUCCESS if refund_status == RefundStatus.SUCCESS else WebhookEventType.REFUND_FAILED

# realized rail ONLY on a successful mandate auth:
if payment_type == "AUTH" and payment_status_str == "SUCCESS":
    realized_rail = map_payment_group_to_rail(auth_details.get("payment_group"))
```

Status maps default to a sensible fallback, not `FAILED`:

```python
# map_subscription_status("UNKNOWN_FUTURE") -> MandateStatus.PENDING_AUTHORIZATION (not FAILED)
# map_debit_status("UNKNOWN")              -> MandateDebitStatus.PENDING (not FAILED)
```

> ❌ **Regen failure:** refund webhook → `PAYMENT_FAILED`; status fallbacks returned `FAILED`;
> `psp_mandate_ref` came back `""`; realized-rail extraction returned `None` on success.

---

## 6. Stitching — base owns the client + env-resolved base_url

`_CashfreeBase(Connector)` owns the single `httpx.AsyncClient` (via `build_http_client`) and resolves
`base_url` from `ConnectorConfig.environment`. Domain mixins (`CashfreeOrders`,
`CashfreeSubscriptions`) inherit it; the root `connector.py` composes them; `webhooks.py` composes the
two domain parsers. See `python/connector_abc.md` for the full skeleton.

```python
_BASE_URLS = {Environment.SANDBOX: "https://sandbox.cashfree.com/pg",
              Environment.PRODUCTION: "https://api.cashfree.com/pg"}

class _CashfreeBase(Connector):
    @property
    def base_url(self) -> str:
        return _BASE_URLS[self._config.environment]      # override via config.base_url_override (API base only)

    def __init__(self, config: ConnectorConfig) -> None:
        self._config = config
        self._client = build_http_client(
            base_url=str(config.base_url_override) if config.base_url_override else self.base_url,
            connector_name=self.name, timeout=30.0)
```

Customer-facing links derive from `self.base_url` so they follow the environment:
`f"{self.base_url}/orders/sessions/{session_id}"`.

---

## 7. Rails → `payment_methods` (subscriptions create)

`request.rails: list[MandateRail] | None` → deduped, **order-preserving union** of each rail's method
list (per `connector_docs/cashfree.md` §rail-mapping). `None`/empty ⇒ **omit** the field (offer all);
never send `[]`. A rail ∉ `supported_mandate_rails()` ⇒ `ConnectorError(NOT_SUPPORTED)` before any HTTP.

> ❌ **Regen failure:** produced `payment_methods: []` instead of `["upi","enach","pnach","card"]` —
> the union wasn't computed. `authorization_amount` is **optional**: when `None`, send `null` +
> `authorization_amount_refund=False`; do NOT default to ₹1.

---

## 8. Webhook signature — `verify_signature` must guard the secret

`core/auth.py::verify_signature(config, raw_payload, headers) -> bool`:

```python
if config.webhook_secret is None:
    raise ConnectorError(reason=ConnectorErrorReason.WEBHOOK_SIGNATURE_FAILED,
                         psp_message="webhook_secret is required for signature verification")
secret = config.webhook_secret.expose().encode("utf-8")
timestamp = headers.get("x-webhook-timestamp", "")
signature = headers.get("x-webhook-signature", "")
if not timestamp or not signature:
    return False
expected = base64.b64encode(hmac.new(secret, timestamp.encode() + raw_payload, hashlib.sha256).digest()).decode()
return hmac.compare_digest(expected, signature)     # Base64(HMAC-SHA256(secret, timestamp + body))
```

> ❌ **Regen failure:** did not **raise** on a missing `webhook_secret` (returned False / crashed) —
> `test_webhook_missing_secret_raises`. A missing secret is a config error → `WEBHOOK_SIGNATURE_FAILED`,
> not a silent `False`.

---

## 9. Sync flows — British vs American spelling, status from the maps

`sync_subscription` GETs `/subscriptions/{psp_mandate_ref}` → `CfSubscriptionEntity`. Cashfree's **GET
entity** spells it **`authorisation_details`** (British 's'); the **webhook** uses
`authorization_details` (American 'z'). Read the realized rail from the British field on the sync path,
only when `payment_group` is present. Every sync flow maps status through the `status_map.py` tables
(see the `connector_docs/cashfree.md` mapping tables) — never inline ad-hoc status logic.

> ❌ **Regen failure:** `sync_subscription` read the American spelling (always `None` rail);
> sync status used guessed values because the status tables were unfilled — they are now filled.

---

**Bottom line:** the working connector at `packages/lens/src/lens/connectors/cashfree/` is the
contract. If a generated method's behavior differs from it on any of the seven points above, the
generation is wrong — fix the generation, not the reference.
